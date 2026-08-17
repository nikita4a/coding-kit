#!/usr/bin/env python3
"""memory-warmup.py — Cross-chat memory warmup for Business Agent.

Run before any non-trivial task. Searches the Wiki for recent entries,
checks integrity, and returns a JSON context snapshot for the agent.

Usage:
    python scripts/memory-warmup.py              # full warmup
    python scripts/memory-warmup.py --query "X"  # targeted search
    python scripts/memory-warmup.py --stats      # stats only
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROFILE_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROFILE_ROOT / "db" / "wiki.db"
WIKI_ROOT = PROFILE_ROOT / "Wiki"


def get_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def stats(db: sqlite3.Connection) -> dict:
    """Return basic Wiki statistics."""
    try:
        total = db.execute("SELECT COUNT(*) as n FROM wiki").fetchone()["n"]
    except Exception:
        total = 0
    try:
        recent = db.execute(
            "SELECT COUNT(*) as n FROM wiki WHERE date >= ?",
            ((datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),),
        ).fetchone()["n"]
    except Exception:
        recent = 0
    try:
        types = {}
        for row in db.execute("SELECT type, COUNT(*) as n FROM wiki GROUP BY type"):
            types[row["type"]] = row["n"]
    except Exception:
        types = {}

    try:
        categories = {}
        for row in db.execute("SELECT tags FROM wiki"):
            if row["tags"]:
                first_tag = row["tags"].split(",")[0].strip().strip("[]").strip("'\"")
                categories[first_tag] = categories.get(first_tag, 0) + 1
    except Exception:
        categories = {}

    return {
        "total_entries": total,
        "recent_7d": recent,
        "by_type": types,
        "by_category": dict(sorted(categories.items(), key=lambda x: -x[1])[:10]),
    }


def search(db: sqlite3.Connection, query: str, limit: int = 5) -> list:
    """Full-text search (schema v2.7: files + files_fts)."""
    try:
        rows = db.execute(
            "SELECT f.rel_path AS path, f.rel_path AS title, f.ext AS type, "
            "date(f.mtime, 'unixepoch') AS date, "
            "snippet(files_fts, 1, '<mark>', '</mark>', '...', 40) AS sn "
            "FROM files_fts ft JOIN files f ON f.id = ft.rowid "
            "WHERE files_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
    except Exception:
        # Fallback: LIKE search
        try:
            rows = db.execute(
                "SELECT rel_path AS path, rel_path AS title, ext AS type, "
                "date(mtime, 'unixepoch') AS date, substr(content, 1, 200) AS sn "
                "FROM files WHERE content LIKE ? ORDER BY mtime DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        except Exception:
            return []

    return [
        {
            "path": r["path"],
            "title": r["title"],
            "type": r["type"],
            "date": r["date"],
            "snippet": r["sn"],
        }
        for r in rows
    ]


def recent_entries(db: sqlite3.Connection, limit: int = 5) -> list:
    """Return most recent entries."""
    try:
        rows = db.execute(
            "SELECT path, title, type, date FROM wiki ORDER BY date DESC LIMIT ?",
            (limit,),
        ).fetchall()
    except Exception:
        return []
    return [
        {"path": r["path"], "title": r["title"], "type": r["type"], "date": r["date"]}
        for r in rows
    ]


def integrity_check() -> dict:
    """Quick integrity check."""
    errors = []
    if not WIKI_ROOT.exists():
        return {"ok": False, "errors": ["Wiki/ directory missing"]}

    # Check index.md exists
    if not (WIKI_ROOT / "index.md").exists():
        errors.append("Wiki/index.md missing")

    # Check log.md exists
    if not (WIKI_ROOT / "log.md").exists():
        errors.append("Wiki/log.md missing")

    # Check for .md files with broken frontmatter
    for md_file in WIKI_ROOT.rglob("*.md"):
        if md_file.name in ("index.md", "log.md", "README.md"):
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
            if not content.startswith("---"):
                errors.append(f"{md_file.relative_to(WIKI_ROOT)}: missing frontmatter")
        except Exception:
            errors.append(f"{md_file.relative_to(WIKI_ROOT)}: unreadable")

    return {"ok": len(errors) == 0, "errors": errors}


def main():
    import argparse

    p = argparse.ArgumentParser(description="Cross-chat memory warmup")
    p.add_argument("--query", "-q", help="Search query")
    p.add_argument("--stats", "-s", action="store_true", help="Stats only")
    p.add_argument("--json", "-j", action="store_true", help="JSON output")
    args = p.parse_args()

    db = get_db()
    if db is None:
        result = {"error": "Database not found. Run: python db-tools/build.py"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    output = {}

    if args.query:
        output["search"] = {"query": args.query, "results": search(db, args.query)}
    elif args.stats:
        output["stats"] = stats(db)
    else:
        # Full warmup
        output["stats"] = stats(db)
        output["recent"] = recent_entries(db)
        output["integrity"] = integrity_check()
        # Suggest: recent errors
        error_hits = search(db, "error bug incident", limit=3)
        if error_hits:
            output["recent_errors"] = error_hits

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # Human-readable
        if "stats" in output:
            s = output["stats"]
            print(f"Wiki: {s['total_entries']} entries ({s['recent_7d']} this week)")
            if s["by_type"]:
                print(f"  Types: {s['by_type']}")
        if "recent" in output:
            print("\nRecent:")
            for r in output["recent"]:
                print(f"  [{r['type']}] {r['title']} ({r['date']})")
        if "integrity" in output:
            ic = output["integrity"]
            if ic["ok"]:
                print("\nIntegrity: OK")
            else:
                print(f"\nIntegrity: {len(ic['errors'])} issue(s)")
                for e in ic["errors"]:
                    print(f"  ! {e}")
        if "recent_errors" in output:
            print("\nRecent errors/incidents:")
            for r in output["recent_errors"]:
                print(f"  [{r['type']}] {r['title']} ({r['date']})")
        if "search" in output:
            print(f"\nSearch: '{output['search']['query']}' → {len(output['search']['results'])} results")
            for r in output["search"]["results"]:
                print(f"  [{r['type']}] {r['title']} ({r['date']})")


if __name__ == "__main__":
    main()