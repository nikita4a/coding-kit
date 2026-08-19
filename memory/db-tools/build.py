#!/usr/bin/env python3


"""Build a file database from a project folder.

By default — INCREMENTAL: compares file mtime/size against the database
and updates only changed/added/deleted. The FTS index is synchronized
by triggers itself. Full rebuild — only on a schema change or with the
--full flag.

Run:
    python3 build.py                                    # memory -> wiki.db
    python3 build.py -r ../projects/myproject -o ../db/myproject.db
    python3 build.py --full                             # full rebuild
"""
import argparse
import fnmatch
import hashlib
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import _compat

ROOT = _compat.chulan_root()

# Windows console defaults to cp1251 — Russian output crashes with
# UnicodeEncodeError. Switching to UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure is optional, fine without it
    pass

# Never indexed, on any machine: build output, VCS, virtualenvs.
DEFAULT_SKIP_DIRS = {"db", ".venv", "venv", ".git", "__pycache__"}
DEFAULT_SKIP_FILES = {".env", "wiki.db", "skip.local"}


def load_local_skip(root):
    """Per-machine extras: <root>/skip.local — one name per line (# =
    comment). Personal project layout stays OUT of the shipped kit."""
    dirs, files = set(), set()
    try:
        # utf-8-sig: Notepad saves BOM by default; a BOM would silently
        # disable the first entry
        text = open(os.path.join(root, "skip.local"), encoding="utf-8-sig").read()
    except OSError:
        return dirs, files
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        (files if line.endswith((".py", ".md", ".db", ".txt"))
         else dirs).add(line)
    return dirs, files

# --- JS/TS via tree-sitter (parsers.py; optional dependency). ---
import os
import sys

import _compat
from parsers import (  # noqa: F401 — the contract (tests: build.extract_*)
    extract_calls,
    extract_errors,
    extract_imports,
    extract_inherits,
    extract_symbols,
)


def read_hashed(full):
    """Read a file: (sha256, content). Hash is the change authority."""
    with open(full, "rb") as f:
        data = f.read()
    return hashlib.sha256(data).hexdigest(), data.decode("utf-8",
                                                         errors="replace")

_BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp",
                ".exe", ".dll", ".so", ".bin", ".pdf", ".zip", ".tar", ".gz",
                ".7z", ".rar", ".jar", ".docx", ".xlsx", ".pptx"}


def is_artifact(fn):
    """Service sqlite files, backups and images — not put into the text
    database. .bak/.orig — backup copies (gen_index writes index.md.bak
    before overwriting): they duplicate content and pollute search
    (case 14.08.2026: phantom index.md.bak in wiki.db, research.db id=489)."""
    return fn.endswith((".db", ".db-shm", ".db-wal", ".db-journal",
                        ".bak", ".orig")) or \
        os.path.splitext(fn)[1].lower() in _BINARY_EXTS


def load_gitignore(root):
    """Minimal .gitignore parser: folder names (like skip_dirs) and
    fnmatch patterns for files. '!' (un-ignore) rules are not handled."""
    ignore_dirs, ignore_files = set(), []
    p = os.path.join(root, ".gitignore")
    if not os.path.isfile(p):
        return ignore_dirs, ignore_files
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("#", "!")):
                    continue
                pat = line.rstrip("/")
                if "*" not in pat and "?" not in pat and "[" not in pat:
                    ignore_dirs.add(pat.lstrip("/"))
                else:
                    ignore_files.append(pat)
    except OSError:
        pass
    return ignore_dirs, ignore_files


def scan_files(root, skip_dirs, skip_files, use_gitignore=False):
    """Fast pass without reading content: rel -> (mtime, size)."""
    out = {}
    gi_dirs, gi_files = load_gitignore(root) if use_gitignore else (set(), [])
    skip = set(skip_dirs) | gi_dirs
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in sorted(filenames):
            if fn in skip_files or is_artifact(fn):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if gi_files and any(
                    fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel, p.lstrip("/"))
                    for p in gi_files):
                continue
            out[rel] = (os.path.getmtime(full), os.path.getsize(full))
    return out

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path TEXT NOT NULL UNIQUE,
    ext TEXT,
    size_bytes INTEGER,
    mtime REAL,
    lines INTEGER,
    symbols_count INTEGER,
    content_hash TEXT,
    content TEXT
);

CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    line INTEGER,
    signature TEXT
);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_path ON symbols(rel_path);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path TEXT NOT NULL,
    module TEXT NOT NULL,
    line INTEGER
);
CREATE INDEX IF NOT EXISTS idx_imports_module ON imports(module);
CREATE INDEX IF NOT EXISTS idx_imports_path ON imports(rel_path);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path TEXT NOT NULL,
    callee TEXT NOT NULL,
    line INTEGER
);
CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee);
CREATE INDEX IF NOT EXISTS idx_calls_path ON calls(rel_path);

CREATE TABLE IF NOT EXISTS inherits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path TEXT NOT NULL,
    child TEXT NOT NULL,
    base TEXT NOT NULL,
    line INTEGER
);
CREATE INDEX IF NOT EXISTS idx_inherits_base ON inherits(base);
CREATE INDEX IF NOT EXISTS idx_inherits_child ON inherits(child);
CREATE INDEX IF NOT EXISTS idx_inherits_path ON inherits(rel_path);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path TEXT NOT NULL,
    line INTEGER,
    message TEXT
);
CREATE INDEX IF NOT EXISTS idx_errors_path ON errors(rel_path);

CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    rel_path, content,
    content='files', content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS files_fts_trigram USING fts5(
    rel_path, content,
    content='files', content_rowid='id', tokenize='trigram'
);

-- WHEN: triggers don't fire on touch-updates (mtime/size) when content
-- has not changed — otherwise every reindexing would rewrite the FTS.

CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
    INSERT INTO files_fts(rowid, rel_path, content)
    VALUES (new.id, new.rel_path, new.content);
END;

CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
    INSERT INTO files_fts(files_fts, rowid, rel_path, content)
    VALUES ('delete', old.id, old.rel_path, old.content);
END;

CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files
WHEN old.content IS NOT new.content BEGIN
    INSERT INTO files_fts(files_fts, rowid, rel_path, content)
    VALUES ('delete', old.id, old.rel_path, old.content);
    INSERT INTO files_fts(rowid, rel_path, content)
    VALUES (new.id, new.rel_path, new.content);
END;

CREATE TRIGGER IF NOT EXISTS files_ai_t AFTER INSERT ON files BEGIN
    INSERT INTO files_fts_trigram(rowid, rel_path, content)
    VALUES (new.id, new.rel_path, new.content);
END;

CREATE TRIGGER IF NOT EXISTS files_ad_t AFTER DELETE ON files BEGIN
    INSERT INTO files_fts_trigram(files_fts_trigram, rowid, rel_path, content)
    VALUES ('delete', old.id, old.rel_path, old.content);
END;

CREATE TRIGGER IF NOT EXISTS files_au_t AFTER UPDATE ON files
WHEN old.content IS NOT new.content BEGIN
    INSERT INTO files_fts_trigram(files_fts_trigram, rowid, rel_path, content)
    VALUES ('delete', old.id, old.rel_path, old.content);
    INSERT INTO files_fts_trigram(rowid, rel_path, content)
    VALUES (new.id, new.rel_path, new.content);
END;
"""


def collect_extra(extra_files):
    """External files outside root (e.g. transcript history): the full path
    is used both as the identifier and as the read point."""
    out = {}
    for p in (extra_files or []):
        full = os.path.abspath(os.path.expanduser(p))
        if os.path.isfile(full):
            out[full] = (os.path.getmtime(full), os.path.getsize(full))
    return out


def upsert_file(cur, rel, full, mtime, size, stats, action, content_hash=None,
                content=None):
    """Read the file and insert/update it (content + symbols + edges).
    Hash and content can be passed in advance (already read during
    comparison) to avoid reading the file twice."""
    if content is None:
        content_hash, content = read_hashed(full)
    if "\x00" in content:
        # binary (no extension match): drop any stale row left by a
        # text->binary flip, never index — a 50MB .exe of U+FFFD made
        # snippet()/bm25() crawl for minutes
        cur.execute("DELETE FROM files WHERE rel_path = ?", (rel,))
        stats["del"] += 1
        return
    lines = content.count("\n") + 1
    syms = extract_symbols(rel, content)
    imports = extract_imports(rel, content)
    calls = extract_calls(rel, content)
    inherits = extract_inherits(rel, content)
    errors = extract_errors(rel, content)
    ext = os.path.splitext(rel)[1].lower() or "none"
    cur.execute("DELETE FROM symbols WHERE rel_path = ?", (rel,))
    cur.execute("DELETE FROM imports WHERE rel_path = ?", (rel,))
    cur.execute("DELETE FROM calls WHERE rel_path = ?", (rel,))
    cur.execute("DELETE FROM inherits WHERE rel_path = ?", (rel,))
    cur.execute("DELETE FROM errors WHERE rel_path = ?", (rel,))
    if action == "new":
        cur.execute(
            "INSERT INTO files (rel_path, ext, size_bytes, mtime, lines, "
            "symbols_count, content_hash, content) VALUES (?,?,?,?,?,?,?,?)",
            (rel, ext, size, mtime, lines, len(syms), content_hash, content),
        )
    else:
        cur.execute(
            "UPDATE files SET ext=?, size_bytes=?, mtime=?, lines=?, "
            "symbols_count=?, content_hash=?, content=? WHERE rel_path=?",
            (ext, size, mtime, lines, len(syms), content_hash, content, rel),
        )
    cur.executemany(
        "INSERT INTO symbols (rel_path, name, kind, line, signature) "
        "VALUES (?,?,?,?,?)",
        [(rel, s[0], s[1], s[2], s[3]) for s in syms],
    )
    cur.executemany(
        "INSERT INTO imports (rel_path, module, line) VALUES (?,?,?)",
        [(rel, m, ln) for m, ln in imports],
    )
    cur.executemany(
        "INSERT INTO calls (rel_path, callee, line) VALUES (?,?,?)",
        [(rel, c, ln) for c, ln in calls],
    )
    cur.executemany(
        "INSERT INTO inherits (rel_path, child, base, line) VALUES (?,?,?,?)",
        [(rel, c, b, ln) for c, b, ln in inherits],
    )
    cur.executemany(
        "INSERT INTO errors (rel_path, line, message) VALUES (?,?,?)",
        [(rel, ln, msg) for ln, msg in errors],
    )
    stats[action] += 1


def full_build(con, root, skip_dirs, skip_files, extra=None,
               use_gitignore=False):
    """Full rebuild: DROP + CREATE + all files."""
    cur = con.cursor()
    cur.executescript(
        "DROP TABLE IF EXISTS files_fts_trigram; "
        "DROP TABLE IF EXISTS files_fts; DROP TABLE IF EXISTS errors; "
        "DROP TABLE IF EXISTS inherits; DROP TABLE IF EXISTS calls; "
        "DROP TABLE IF EXISTS imports; DROP TABLE IF EXISTS symbols; "
        "DROP TABLE IF EXISTS files;")
    cur.executescript(SCHEMA)
    stats = {"new": 0, "changed": 0, "del": 0, "same": 0}
    for rel, (mtime, size) in scan_files(root, skip_dirs, skip_files,
                                         use_gitignore).items():
        upsert_file(cur, rel, os.path.join(root, rel), mtime, size, stats, "new")
    for full, (mtime, size) in (extra or {}).items():
        upsert_file(cur, full, full, mtime, size, stats, "new")
    return stats


def incremental_build(con, root, skip_dirs, skip_files, extra=None,
                      use_gitignore=False):
    """mtime-then-hash: mtime/size — cheap gate, sha256 — authority.

    mtime matches -> leave the file alone (fast path, no reading).
    mtime/size differ -> read and hash; hash matches the stored one
    (cp -p, restore, LiveSync rewrote bytes identically) -> update only
    mtime/size, content and FTS untouched. Hash differs -> full upsert.
    Triggers keep both FTS indexes in sync."""
    cur = con.cursor()
    cur.execute("SELECT rel_path, mtime, size_bytes, content_hash FROM files")
    db_files = {r[0]: (r[1], r[2], r[3]) for r in cur.fetchall()}
    disk = scan_files(root, skip_dirs, skip_files, use_gitignore)
    stats = {"new": 0, "changed": 0, "del": 0, "same": 0, "touch": 0}

    for rel, (mtime, size) in disk.items():
        rec = db_files.get(rel)
        if rec is None:
            upsert_file(cur, rel, os.path.join(root, rel), mtime, size,
                        stats, "new")
        elif rec[0] == mtime and rec[1] == size:
            stats["same"] += 1
        else:
            full = os.path.join(root, rel)
            content_hash, content = read_hashed(full)
            if rec[2] == content_hash:
                cur.execute(
                    "UPDATE files SET mtime=?, size_bytes=? WHERE rel_path=?",
                    (mtime, size, rel))
                stats["touch"] += 1
            else:
                upsert_file(cur, rel, full, mtime, size, stats, "changed",
                            content_hash, content)

    for full, (mtime, size) in (extra or {}).items():
        rec = db_files.get(full)
        if rec is None:
            upsert_file(cur, full, full, mtime, size, stats, "new")
        elif rec[0] == mtime and rec[1] == size:
            stats["same"] += 1
        else:
            content_hash, content = read_hashed(full)
            if rec[2] == content_hash:
                cur.execute(
                    "UPDATE files SET mtime=?, size_bytes=? WHERE rel_path=?",
                    (mtime, size, full))
                stats["touch"] += 1
            else:
                upsert_file(cur, full, full, mtime, size, stats, "changed",
                            content_hash, content)

    for rel in set(db_files) - set(disk) - set(extra or {}):
        cur.execute("DELETE FROM files WHERE rel_path = ?", (rel,))
        cur.execute("DELETE FROM symbols WHERE rel_path = ?", (rel,))
        cur.execute("DELETE FROM imports WHERE rel_path = ?", (rel,))
        cur.execute("DELETE FROM calls WHERE rel_path = ?", (rel,))
        cur.execute("DELETE FROM inherits WHERE rel_path = ?", (rel,))
        cur.execute("DELETE FROM errors WHERE rel_path = ?", (rel,))
        stats["del"] += 1
    if stats["del"]:
        # DELETE triggers leave FTS tombstones; merge them so the index
        # does not bloat (372MB agent.db incident, 2026-08-19)
        cur.execute("INSERT INTO files_fts(files_fts) VALUES('optimize')")
        cur.execute(
            "INSERT INTO files_fts_trigram(files_fts_trigram) VALUES('optimize')")
    return stats


def schema_ok(con):
    """Database is suitable for incremental updates (current schema)."""
    try:
        cur = con.cursor()
        for t in ("files", "symbols", "imports", "calls", "inherits",
                  "errors"):
            # t — only from the fixed tuple above, not user input
            cur.execute(f"SELECT 1 FROM {t} LIMIT 1")  # noqa: S608 — t from the fixed tuple above; nosemgrep
        file_cols = [r[1] for r in cur.execute("PRAGMA table_info(files)")]
        sym_cols = [r[1] for r in cur.execute("PRAGMA table_info(symbols)")]
        return "lines" in file_cols and "content_hash" in file_cols and \
            "signature" in sym_cols
    except sqlite3.Error:
        return False


def main():
    ap = argparse.ArgumentParser(description="Build a file database in sqlite")
    ap.add_argument("-r", "--root", default=str(ROOT))
    ap.add_argument("-o", "--out", help="path to the database (default <root>/<folder-name>.db)")
    ap.add_argument("--full", action="store_true", help="full rebuild instead of incremental")
    ap.add_argument("--skip-dirs", nargs="*", default=[], help="additional folders to exclude")
    ap.add_argument("--skip-files", nargs="*", default=[], help="additional files to exclude")
    ap.add_argument("--gitignore", action="store_true",
                    help="respect the root .gitignore (default off: the database indexes everything, "
                         "including nested projects)")
    ap.add_argument("--extra-files", nargs="*", default=[],
                    help="external files outside root (e.g. ~/.cache/session/history.md)")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"no such folder: {root}", file=sys.stderr)
        sys.exit(1)
    if args.out:
        db_path = os.path.abspath(args.out)
    elif os.path.abspath(root) == os.path.abspath(str(ROOT)):
        db_path = os.path.join(ROOT, "db", "wiki.db")
    else:
        # project build: its own db, never the wiki (a documented
        # invocation used to destroy wiki.db: '-r X' without '-o')
        db_path = os.path.join(ROOT, "db", os.path.basename(root) + ".db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    local_dirs, local_files = load_local_skip(root)
    skip_dirs = DEFAULT_SKIP_DIRS | set(args.skip_dirs) | local_dirs
    skip_files = DEFAULT_SKIP_FILES | set(args.skip_files) | local_files
    extra = collect_extra(args.extra_files)

    existed = os.path.exists(db_path)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL")
    if args.full or not existed or not schema_ok(con):
        stats = full_build(con, root, skip_dirs, skip_files, extra,
                           args.gitignore)
        mode = "full"
    else:
        stats = incremental_build(con, root, skip_dirs, skip_files, extra,
                                  args.gitignore)
        mode = "incremental"

    con.commit()
    cur = con.cursor()
    n = cur.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    total = cur.execute("SELECT SUM(LENGTH(content)) FROM files").fetchone()[0]
    nsym = cur.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
    print(f"ok [{mode}]: {n} files, {nsym} symbols, {total} chars of text "
          f"-> {db_path}")
    print(f"    processed: +{stats['new']} / ~{stats['changed']} / "
          f"-{stats['del']}, unchanged: {stats['same']}, "
          f"touch (mtime, content identical): {stats.get('touch', 0)}")
    con.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 — CLI wrapper: surface any error with exit code 1
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
