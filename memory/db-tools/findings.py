#!/usr/bin/env python3

"""Findings and conclusions database (research.db) — knowledge already arrived at.

Why: research (web, Camoufox, experiments, teardowns) produces conclusions
that get lost after the conversation. Here they live apart from project files
and are found by search, like everything else.

Examples:
    python3 findings.py add "MCP for LSP" --text "agent-lsp — the most mature bridge..." --tags mcp lsp
    python3 findings.py search mcp
    python3 findings.py list
    python3 findings.py list --tags lsp
    python3 findings.py del 12
    python3 findings.py edit 12 --tags "lsp mcp"
"""
import argparse
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import _compat
from ftsquery import sanitize_query

ROOT = _compat.chulan_root()

# Windows console defaults to cp1251 — non-ASCII output crashes with
# UnicodeEncodeError. Switch to UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure is optional, we live without it
    pass


# The DB can be overridden for tests/sandbox (isolation from the prod store):
# MEMORY_ROOT_RESEARCH_DB=/tmp/test.db python3 db-tools/findings.py ...
DB = os.environ.get("MEMORY_ROOT_RESEARCH_DB", os.path.join(ROOT, "db", "research.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL,
    topic TEXT NOT NULL,
    text TEXT NOT NULL,
    tags TEXT DEFAULT '',
    source TEXT DEFAULT '',
    file TEXT DEFAULT '',
    symbol TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    kind TEXT NOT NULL DEFAULT 'related',
    note TEXT DEFAULT '',
    created TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_id);
CREATE INDEX IF NOT EXISTS idx_links_to ON links(to_id);
CREATE VIRTUAL TABLE IF NOT EXISTS findings_fts USING fts5(
    topic, text, content='findings', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS findings_ai AFTER INSERT ON findings BEGIN
    INSERT INTO findings_fts(rowid, topic, text)
    VALUES (new.id, new.topic, new.text);
END;
CREATE TRIGGER IF NOT EXISTS findings_ad AFTER DELETE ON findings BEGIN
    INSERT INTO findings_fts(findings_fts, rowid, topic, text)
    VALUES ('delete', old.id, old.topic, old.text);
END;
CREATE TRIGGER IF NOT EXISTS findings_au AFTER UPDATE ON findings BEGIN
    INSERT INTO findings_fts(findings_fts, rowid, topic, text)
    VALUES ('delete', old.id, old.topic, old.text);
    INSERT INTO findings_fts(rowid, topic, text)
    VALUES (new.id, new.topic, new.text);
END;
"""

OPS = {"AND", "OR", "NOT", "NEAR"}  # noqa: F401 — re-exported for old imports


def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    # Soft migration of old databases: columns that did not exist before
    cols = [r[1] for r in con.execute("PRAGMA table_info(findings)")]
    if "source" not in cols:
        con.execute("ALTER TABLE findings ADD COLUMN source TEXT DEFAULT ''")
    if "file" not in cols:
        con.execute("ALTER TABLE findings ADD COLUMN file TEXT DEFAULT ''")
    if "symbol" not in cols:
        con.execute("ALTER TABLE findings ADD COLUMN symbol TEXT DEFAULT ''")
    if "verify_cmd" not in cols:
        con.execute(
            "ALTER TABLE findings ADD COLUMN verify_cmd TEXT DEFAULT ''")
    if "verified_at" not in cols:
        con.execute(
            "ALTER TABLE findings ADD COLUMN verified_at TEXT DEFAULT ''")
    con.commit()
    return con


def cmd_add(args):
    con = connect()
    cur = con.cursor()
    if not args.source:
        print("[~] hint: --source not set; for web facts give a "
              "URL/path (verification, research.db id=367)", file=sys.stderr)
    dup = cur.execute(
        "SELECT id, topic FROM findings WHERE topic = ? LIMIT 1",
        (args.topic,)).fetchone()
    if dup:
        print(f"[!] a finding with this topic already exists: id={dup['id']} "
              f"\"{dup['topic']}\" — adding a duplicate", file=sys.stderr)
    cur.execute(
        "INSERT INTO findings (created, topic, text, tags, source, file, "
        "symbol, verify_cmd) VALUES (?,?,?,?,?,?,?,?)",
        (datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
         args.topic, args.text, args.tags, args.source or "",
         args.file or "", args.symbol or "", getattr(args, "verify_cmd", "") or ""))
    new_id = cur.lastrowid
    for rel in _parse_ids(args.related):
        if rel != new_id:
            cur.execute(
                "INSERT INTO links (from_id, to_id, kind, note, created) "
                "VALUES (?,?,?,?,?)",
                (new_id, rel, "related", "",
                 datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")))
    con.commit()
    print(f"[✓] added: {args.topic} (id={new_id})")
    if args.file:
        loc = args.file + (f":{args.symbol}" if args.symbol else "")
        print(f"    attached to: {loc}")
    if args.related:
        print(f"    linked to: {args.related}")
    con.close()


def _parse_ids(s):
    """'1,2, 3' -> [1, 2, 3]; skip junk."""
    out = []
    for part in (s or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out




def cmd_del(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT topic FROM findings WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"no finding with id={args.id}")
        return
    cur.execute("DELETE FROM findings WHERE id = ?", (args.id,))
    n_links = cur.execute(
        "DELETE FROM links WHERE from_id = ? OR to_id = ?",
        (args.id, args.id)).rowcount
    con.commit()
    print(f"[✓] deleted: id={args.id} \"{row['topic']}\""
          + (f" (links deleted: {n_links})" if n_links else ""))
    con.close()


def cmd_edit(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT * FROM findings WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"no finding with id={args.id}")
        return
    sets, params = [], []
    for col, val in (("topic", args.topic), ("text", args.text),
                     ("tags", args.tags), ("source", args.source)):
        if val is not None:
            sets.append(f"{col} = ?")
            params.append(val)
    if not sets:
        print("nothing to change: pass --topic/--text/--tags")
        return
    params.append(args.id)
    # Columns are the fixed list above (topic/text/tags/source),
    # values are only parameters: no injection.
    cur.execute(f"UPDATE findings SET {', '.join(sets)} WHERE id = ?", params)  # noqa: S608 — columns whitelist, values params; nosemgrep
    con.commit()
    print(f"[✓] updated: id={args.id} \"{row['topic']}\"")
    con.close()


def cmd_verify(args):
    """Re-run a finding's verify-cmd: memory that proves itself fresh.
    VERIFIED (exit 0, verified_at stamped) or FAILED (exit 1)."""
    import shlex
    con = connect()
    cur = con.cursor()
    r = cur.execute("SELECT topic, verify_cmd, verified_at FROM findings "
                    "WHERE id = ?", (args.id,)).fetchone()
    if not r:
        print(f"no finding with id={args.id}")
        con.close()
        sys.exit(1)
    if not r["verify_cmd"]:
        print(f"finding [{args.id}] has no verify-cmd "
              "(add one: findings.py edit ... / add --verify-cmd)")
        con.close()
        sys.exit(1)
    cmd = shlex.split(r["verify_cmd"])
    print(f"[~] running: {r['verify_cmd']}")
    out = _compat.run(cmd, timeout=getattr(args, "timeout", None) or 300)
    tail = "\n".join(((out.stdout or "") + (out.stderr or "")).splitlines()[-5:])
    if out.returncode == 0:
        now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
        cur.execute("UPDATE findings SET verified_at = ? WHERE id = ?",
                    (now, args.id))
        con.commit()
        print(f"[✓] VERIFIED: \"{r['topic']}\" at {now}")
        con.close()
        return
    print(f"[✗] FAILED (rc={out.returncode}): \"{r['topic']}\" — "
          f"last verified: {r['verified_at'] or 'never'}")
    if tail:
        print(tail)
    con.close()
    sys.exit(1)


def cmd_search(args):
    con = connect()
    cur = con.cursor()
    sql = ("SELECT f.id, f.created, f.topic, f.tags, "
           "snippet(findings_fts, 1, '[', ']', '…', 12) AS snip "
           "FROM findings_fts JOIN findings f ON f.id = findings_fts.rowid "
           "WHERE findings_fts MATCH ?")
    params = [sanitize_query(args.query)]
    source = getattr(args, "source", "")
    tag = getattr(args, "tag", "")
    if source:
        sql += " AND f.source LIKE ?"
        params.append(f"%{source}%")
    if tag:
        sql += " AND ' '||f.tags||' ' LIKE ?"
        params.append(f"% {tag} %")
    sql += " ORDER BY f.id DESC LIMIT ?"
    params.append(args.limit)
    try:
        rows = cur.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        print(f"invalid query: {e}", file=sys.stderr)
        sys.exit(1)
    if not rows:
        print(f"not found for \"{args.query}\""
              + (f" (source ~ \"{source}\")" if source else "")
              + (f" (tag \"{tag}\")" if tag else ""))
        return
    print(f"found: {len(rows)}\n")
    for r in rows:
        print(f"[{r['id']}] {r['created']}  {r['topic']}  ({r['tags']})")
        print(f"  …{r['snip']}")
        print()
    con.close()


def cmd_list(args):
    con = connect()
    cur = con.cursor()
    if args.tags:
        rows = cur.execute(
            "SELECT id, created, topic, tags, file, symbol FROM findings "
            "WHERE ' '||tags||' ' LIKE ? ORDER BY id DESC",
            (f"% {args.tags} %",)).fetchall()
    else:
        rows = cur.execute(
            "SELECT id, created, topic, tags, file, symbol FROM findings "
            "ORDER BY id DESC LIMIT ?", (args.limit,)).fetchall()
    if not rows:
        print("empty so far — add the first finding: findings.py add \"topic\"")
        return
    print(f"total: {len(rows)}\n")
    for r in rows:
        loc = f" [{r['file']}:{r['symbol']}]" if r["file"] else ""
        print(f"[{r['id']}] {r['created']}  {r['topic']}  ({r['tags']}){loc}")
    con.close()


def _row_links(cur, fid):
    """Finding links in both directions: [(direction, linked_id, kind, note)]."""
    out = []
    for r in cur.execute(
            "SELECT l.id link_id, l.from_id, l.to_id, l.kind, l.note, "
            "f.topic FROM links l JOIN findings f ON f.id = "
            "CASE WHEN l.from_id = ? THEN l.to_id ELSE l.from_id END "
            "WHERE l.from_id = ? OR l.to_id = ? ORDER BY l.id",
            (fid, fid, fid)).fetchall():
        direction = "->" if r["from_id"] == fid else "<-"
        out.append((r["link_id"], direction, r["kind"], r["topic"],
                    r["note"]))
    return out


def cmd_link_add(args):
    con = connect()
    cur = con.cursor()
    for fid in (args.from_id, args.to_id):
        if not cur.execute("SELECT 1 FROM findings WHERE id = ?",
                           (fid,)).fetchone():
            print(f"no finding with id={fid}", file=sys.stderr)
            con.close()
            sys.exit(1)
    cur.execute(
        "INSERT INTO links (from_id, to_id, kind, note, created) "
        "VALUES (?,?,?,?,?)",
        (args.from_id, args.to_id, args.kind, args.note or "",
         datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")))
    con.commit()
    print(f"[✓] link: {args.from_id} --{args.kind}--> {args.to_id} (id={cur.lastrowid})")
    con.close()


def cmd_link_list(args):
    con = connect()
    cur = con.cursor()
    if not cur.execute("SELECT 1 FROM findings WHERE id = ?",
                       (args.id,)).fetchone():
        print(f"no finding with id={args.id}")
        con.close()
        return
    links = _row_links(cur, args.id)
    if not links:
        print(f"finding [{args.id}] has no links")
        con.close()
        return
    print(f"links of finding [{args.id}]:\n")
    for _link_id, direction, kind, topic, note in links:
        note_s = f"  ({note})" if note else ""
        print(f"  {direction} {kind:12} [{_link_id}] {topic}{note_s}")
    con.close()


def cmd_link_rm(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT id, from_id, to_id, kind FROM links WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"no link with id={args.id}")
        return
    cur.execute("DELETE FROM links WHERE id = ?", (args.id,))
    con.commit()
    print(f"[✓] link deleted: {row['from_id']} --{row['kind']}--> {row['to_id']}")
    con.close()


def cmd_related(args):
    """Quick answer to "what is linked to this finding": id + topics.
    --depth N — transitive links (graph over links, KG pattern from
    mcp-memory entities/relations: knowledge chains, not just neighbors)."""
    con = connect()
    cur = con.cursor()
    if getattr(args, "depth", 0) > 0:
        _print_chain(cur, args.id, args.depth)
        con.close()
        return
    links = _row_links(cur, args.id)
    if not links:
        print(f"finding [{args.id}] has no links")
        con.close()
        return
    print(f"linked to [{args.id}]:\n")
    for _link_id, direction, kind, topic, note in links:
        note_s = f"  ({note})" if note else ""
        print(f"  {direction} {kind:12} {topic}{note_s}")
    con.close()


def _print_chain(cur, fid, depth):
    """Link graph down to the given depth: recursive CTE over links."""
    rows = cur.execute(
        "WITH RECURSIVE chain(id, d, path) AS ("
        "  SELECT ?, 0, '' "
        "  UNION "
        "  SELECT CASE WHEN l.from_id = chain.id THEN l.to_id "
        "              ELSE l.from_id END,"
        "         chain.d + 1,"
        "         chain.path || ' >' || l.kind || '> '"
        "  FROM links l JOIN chain "
        "  ON (l.from_id = chain.id OR l.to_id = chain.id) "
        "  AND chain.d < ?"
        ") SELECT DISTINCT c.id, MIN(c.d) AS d, "
        "  (SELECT path FROM chain c2 WHERE c2.id = c.id "
        "   ORDER BY c2.d LIMIT 1) AS path, "
        "  (SELECT topic FROM findings f WHERE f.id = c.id) AS topic "
        "FROM chain c WHERE c.id != ? GROUP BY c.id ORDER BY d",
        (fid, depth, fid)).fetchall()
    if not rows:
        print(f"finding [{fid}] has no links")
        return
    print(f"link graph [{fid}] (depth {depth}):\n")
    for r in rows:
        print(f"  [{r['id']}] d={r['d']}  {r['topic']}")
        if r["path"]:
            print(f"       path: {r['path'].strip()}")


def cmd_show(args):
    con = connect()
    cur = con.cursor()
    r = cur.execute("SELECT * FROM findings WHERE id = ?",
                    (args.id,)).fetchone()
    if not r:
        print(f"no finding with id={args.id}")
        con.close()
        return
    print(f"[{r['id']}] {r['created']}  {r['topic']}")
    if r["tags"]:
        print(f"tags: {r['tags']}")
    if r["source"]:
        print(f"source: {r['source']}")
    if r["verify_cmd"]:
        print(f"verify-cmd: {r['verify_cmd']} "
              f"(last: {r['verified_at'] or 'never'})")
    print()
    print(r["text"])
    links = _row_links(cur, args.id)
    if links:
        print("\nlinks:")
        for _link_id, direction, kind, topic, note in links:
            note_s = f"  ({note})" if note else ""
            print(f"  {direction} {kind:12} {topic}{note_s}")
    con.close()


def cmd_stats(args):
    con = connect()
    cur = con.cursor()
    total = cur.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
    week_ago = (datetime.datetime.now().astimezone() -
                datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
    last7 = cur.execute("SELECT COUNT(*) FROM findings WHERE created >= ?",
                        (week_ago,)).fetchone()[0]
    nlinks = cur.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    print(f"findings: {total}  (last 7 days: {last7})  links: {nlinks}")
    tags = cur.execute(
        "SELECT tags, COUNT(*) n FROM findings GROUP BY tags "
        "ORDER BY n DESC LIMIT 10").fetchall()
    if tags and any(r["tags"] for r in tags):
        print("\ntop tags (set | count):")
        for r in tags:
            if r["tags"]:
                print(f"  {r['tags']:40} | {r['n']}")
    con.close()


def main():
    ap = argparse.ArgumentParser(description="Findings and conclusions database")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add", help="add a finding")
    p_add.add_argument("topic", help="topic in one line")
    p_add.add_argument("--text", required=True, help="conclusion/fact")
    p_add.add_argument("--tags", default="", help="space-separated tags")
    p_add.add_argument("--source", default="", help="where it came from (path/URL)")
    p_add.add_argument("--file", default="",
                       help="project file where the problem lives (rel_path)")
    p_add.add_argument("--symbol", default="",
                       help="symbol (fn/class) where the problem lives")
    p_add.add_argument("--related", default="",
                       help="ids of linked findings, comma-separated")
    p_add.add_argument("--verify-cmd", default="",
                       help="command that re-verifies this conclusion "
                            "(findings.py verify <id> runs it)")
    p_add.set_defaults(fn=cmd_add)

    p_verify = sub.add_parser("verify", help="re-run a finding's verify-cmd")
    p_verify.add_argument("id", type=int)
    p_verify.add_argument("--timeout", type=int, default=300,
                          help="verify-cmd timeout seconds (default 300)")
    p_verify.set_defaults(fn=cmd_verify)

    p_search = sub.add_parser("search", help="search findings")
    p_search.add_argument("query", help="FTS5 query")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--source", default="",
                          help="filter: source (path/URL) contains substring")
    p_search.add_argument("--tag", default="",
                          help="filter: exact finding tag")
    p_search.set_defaults(fn=cmd_search)

    p_list = sub.add_parser("list", help="list findings")
    p_list.add_argument("--tags", default="", help="filter by tag (exact word)")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.set_defaults(fn=cmd_list)

    p_del = sub.add_parser("del", help="delete finding by id")
    p_del.add_argument("id", type=int)
    p_del.set_defaults(fn=cmd_del)

    p_edit = sub.add_parser("edit", help="edit finding by id")
    p_edit.add_argument("id", type=int)
    p_edit.add_argument("--topic")
    p_edit.add_argument("--text")
    p_edit.add_argument("--tags")
    p_edit.add_argument("--source")
    p_edit.set_defaults(fn=cmd_edit)

    p_show = sub.add_parser("show", help="full finding record + links")
    p_show.add_argument("id", type=int)
    p_show.set_defaults(fn=cmd_show)

    p_related = sub.add_parser("related", help="what is linked to a finding")
    p_related.add_argument("id", type=int)
    p_related.add_argument("--depth", type=int, default=0,
                           help="link graph depth (0 — neighbors only)")
    p_related.set_defaults(fn=cmd_related)

    p_link = sub.add_parser("link", help="finding links (link add/list/rm)")
    link_sub = p_link.add_subparsers(dest="link_cmd", required=True)
    p_la = link_sub.add_parser("add", help="add a link")
    p_la.add_argument("from_id", type=int)
    p_la.add_argument("to_id", type=int)
    p_la.add_argument("--kind", default="related",
                      help="type: related/extends/contradicts/source (default related)")
    p_la.add_argument("--note", default="", help="note for the link")
    p_la.set_defaults(fn=cmd_link_add)
    p_ll = link_sub.add_parser("list", help="finding links (both directions)")
    p_ll.add_argument("id", type=int)
    p_ll.set_defaults(fn=cmd_link_list)
    p_lr = link_sub.add_parser("rm", help="delete link by id")
    p_lr.add_argument("id", type=int)
    p_lr.set_defaults(fn=cmd_link_rm)

    p_stats = sub.add_parser("stats", help="metrics: total findings, last 7 days, links, top tags")
    p_stats.set_defaults(fn=cmd_stats)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()


