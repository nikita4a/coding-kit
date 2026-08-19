#!/usr/bin/env python3
"""memory-warmup.py — cross-chat memory warmup (global + per-project hierarchy).

Schema v2.7 (files + files_fts), search across ALL databases in the db/
directory (global wiki.db + project *.db), findings from research.db.

Usage:
    python scripts/memory-warmup.py              # full warmup
    python scripts/memory-warmup.py --query "X"  # search all databases
    python scripts/memory-warmup.py --stats      # stats only
    python scripts/memory-warmup.py --json       # JSON for the agent
"""
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROFILE_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROFILE_ROOT / "db"
WIKI_ROOT = PROFILE_ROOT / "Wiki"
WIKI_DB = DB_DIR / "wiki.db"
RESEARCH_DB = DB_DIR / "research.db"


def list_dbs() -> list:
    """Databases in db/ with the files_fts table (wiki.db + project ones)."""
    out = []
    if not DB_DIR.exists():
        return out
    for p in sorted(DB_DIR.glob("*.db")):
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            has = con.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name='files_fts'"
            ).fetchone()[0] > 0
            con.close()
        except sqlite3.Error:
            continue
        if has:
            out.append(p)
    return out


def _sanitize(query: str) -> str:
    """Quote tokens with FTS5 specials (hyphen = column filter:
    'agent-lsp' dies as 'no such column: lsp' without this). Mirrors
    search.py sanitize_query; duplicated because warmup ships to
    ~/.memory/scripts without db-tools. Prefix wildcards stay unquoted
    (a quoted '*' is a literal and kills the prefix search)."""
    out = []
    for tok in query.split():
        up = tok.upper()
        if up in ("AND", "OR", "NOT") or up.startswith("NEAR(") or \
                (tok.startswith('"') and tok.endswith('"')):
            out.append(tok)
        elif tok.endswith("*") and any(c in tok[:-1] for c in '"-():^'):
            # prefix on a special-char body: quote the body, keep the
            # star outside (quoted '*' is a literal in FTS5)
            out.append('"' + tok[:-1].replace('"', '""') + '"*')
        elif any(c in tok for c in '"-()*:^'):
            out.append('"' + tok.replace('"', '""') + '"')
        else:
            out.append(tok)
    return " ".join(out)


def search_all_dbs(query: str, limit: int = 5) -> list:
    """FTS search across all databases: [{db, path, snippet}]."""
    results = []
    for p in list_dbs():
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            rows = con.execute(
                "SELECT rel_path, snippet(files_fts, 1, '<mark>', '</mark>', '...', 40) "
                "FROM files_fts WHERE files_fts MATCH ? LIMIT ?",
                (_sanitize(query), limit),
            ).fetchall()
            con.close()
        except sqlite3.OperationalError:
            continue
        for path, snip in rows:
            results.append({"db": p.stem, "path": path, "snippet": snip})
    return results


def _wiki_where() -> str:
    """WHERE for global Wiki files (separator-independent: GLOB)."""
    return "(rel_path GLOB 'Wiki*') AND ext IN ('md','.md') AND rel_path NOT GLOB '*_templates*'"


def stats() -> dict:
    """Stats: global Wiki + project databases + findings."""
    out = {"wiki_entries": 0, "recent_7d": 0, "project_dbs": [], "findings": 0}
    if WIKI_DB.exists():
        con = sqlite3.connect(f"file:{WIKI_DB}?mode=ro", uri=True)
        try:
            out["wiki_entries"] = con.execute(
                f"SELECT COUNT(*) FROM files WHERE {_wiki_where()}"
            ).fetchone()[0]
            out["recent_7d"] = con.execute(
                f"SELECT COUNT(*) FROM files WHERE {_wiki_where()} "
                "AND mtime >= strftime('%s','now','-7 days')"
            ).fetchone()[0]
        except sqlite3.Error:
            pass
        con.close()
    for p in list_dbs():
        if p == WIKI_DB:
            continue
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            n = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            con.close()
            out["project_dbs"].append({"name": p.stem, "files": n})
        except sqlite3.Error:
            continue
    if RESEARCH_DB.exists():
        try:
            con = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True)
            out["findings"] = con.execute(
                "SELECT COUNT(*) FROM findings").fetchone()[0]
            con.close()
        except sqlite3.Error:
            pass
    return out


def recent_entries(limit: int = 5) -> list:
    """Most recent global Wiki entries (by mtime)."""
    if not WIKI_DB.exists():
        return []
    try:
        con = sqlite3.connect(f"file:{WIKI_DB}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT rel_path, date(mtime, 'unixepoch') AS d FROM files "
            f"WHERE {_wiki_where()} "
            "ORDER BY mtime DESC LIMIT ?", (limit,),
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return []
    return [{"path": r[0], "date": r[1]} for r in rows]


def recent_findings(limit: int = 3) -> list:
    """Most recent research.db findings."""
    if not RESEARCH_DB.exists():
        return []
    try:
        con = sqlite3.connect(f"file:{RESEARCH_DB}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT id, created, topic FROM findings ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return []
    return [{"id": r[0], "date": r[1], "topic": r[2]} for r in rows]


def integrity_check() -> dict:
    """Quick integrity check of the global Wiki."""
    errors = []
    if not WIKI_ROOT.exists():
        return {"ok": False, "errors": ["Wiki/ directory missing"]}
    for name in ("index.md", "log.md"):
        if not (WIKI_ROOT / name).exists():
            errors.append(f"Wiki/{name} missing")
    for md in WIKI_ROOT.rglob("*.md"):
        if md.name in ("index.md", "log.md", "README.md"):
            continue
        try:
            if not md.read_text(encoding="utf-8").startswith("---"):
                errors.append(f"{md.relative_to(WIKI_ROOT)}: missing frontmatter")
        except Exception:
            errors.append(f"{md.relative_to(WIKI_ROOT)}: unreadable")
    return {"ok": len(errors) == 0, "errors": errors}


def main():
    import argparse

    p = argparse.ArgumentParser(description="Cross-chat memory warmup")
    p.add_argument("--query", "-q", help="Search query (all dbs)")
    p.add_argument("--stats", "-s", action="store_true", help="Stats only")
    p.add_argument("--json", "-j", action="store_true", help="JSON output")
    args = p.parse_args()

    output = {}
    if args.query:
        output["search"] = {"query": args.query,
                            "results": search_all_dbs(args.query)}
    elif args.stats:
        output["stats"] = stats()
    else:
        output["stats"] = stats()
        output["recent"] = recent_entries()
        output["findings"] = recent_findings()
        output["integrity"] = integrity_check()

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    if "stats" in output:
        s = output["stats"]
        print(f"Wiki: {s['wiki_entries']} entries ({s['recent_7d']} this week)")
        for pd in s["project_dbs"]:
            print(f"  project [{pd['name']}]: {pd['files']} files")
        print(f"  findings: {s['findings']}")
    if "recent" in output:
        print("\nRecent:")
        for r in output["recent"]:
            print(f"  {r['path']} ({r['date']})")
    if "findings" in output and output["findings"]:
        print("\nFindings:")
        for f in output["findings"]:
            print(f"  [#{f['id']}] {f['topic']} ({f['date']})")
    if "integrity" in output:
        ic = output["integrity"]
        print(f"\nIntegrity: {'OK' if ic['ok'] else str(len(ic['errors'])) + ' issue(s)'}")
        for e in ic["errors"][:10]:
            print(f"  ! {e}")
    if "search" in output:
        q = output["search"]
        print(f"\nSearch: '{q['query']}' → {len(q['results'])} results")
        for r in q["results"][:10]:
            print(f"  [{r['db']}] {r['path']}")
            print(f"    {r['snippet']}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main()