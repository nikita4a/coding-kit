"""memory/db-tools/findings_db.py — database connection and schema for findings."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import _compat

ROOT = _compat.chulan_root()

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
        con.execute("ALTER TABLE findings ADD COLUMN verify_cmd TEXT DEFAULT ''")
    if "verified_at" not in cols:
        con.execute("ALTER TABLE findings ADD COLUMN verified_at TEXT DEFAULT ''")
    con.commit()
    return con
