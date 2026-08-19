#!/usr/bin/env python3

"""Поиск по ВСЕМ базам воркспейса сразу (паттерн srclight multi-repo:
ATTACH + UNION). «Где это лежит» одним запросом — по всем базам,
agent, wiki, проектным базам db/*.db (базы без files_fts пропускаются,
например research.db — у неё своя схема findings/tasks).

Использование:
    python3 db-tools/search_all.py "прошивка"
    python3 db-tools/search_all.py "load_mix" --limit 15
    python3 db-tools/search_all.py "настройк" --substring
"""
import argparse
import sqlite3
import sys
from pathlib import Path

from _compat import chulan_root, fix_encoding  # noqa: E402

fix_encoding()

DB_DIR = chulan_root() / "db"


def list_searchable_dbs(db_dir=None) -> list:
    """Базы каталога db/ с таблицей files_fts (или files_fts_trigram)."""
    ddir = Path(db_dir) if db_dir else DB_DIR
    out = []
    for p in sorted(ddir.glob("*.db")):
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            has = con.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE name IN ('files_fts','files_fts_trigram')"
            ).fetchone()[0] > 0
            con.close()
        except sqlite3.Error:
            continue
        if has:
            out.append(p)
    return out


def search_all(query: str, limit: int = 5, substring: bool = False,
               db_dir=None) -> list:
    """[(база, rel_path, сниппет), ...] по всем базам."""
    results = []
    idx = "files_fts_trigram" if substring else "files_fts"
    for p in list_searchable_dbs(db_dir):
        name = p.stem
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            rows = con.execute(
                f"SELECT rel_path, snippet({idx}, 1, '<b>', '</b>', "
                f"'…', 12) FROM {idx} WHERE {idx} MATCH ? LIMIT ?",
                (query, limit)).fetchall()
            con.close()
        except sqlite3.OperationalError:
            continue
        for rel_path, snip in rows:
            results.append((name, rel_path, snip))
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", help="запрос (>= 3 символа)")
    ap.add_argument("--limit", type=int, default=5,
                    help="результатов на базу")
    ap.add_argument("--substring", action="store_true",
                    help="триграм-подстрока вместо слов (склонения)")
    args = ap.parse_args()
    results = search_all(args.query, limit=args.limit,
                         substring=args.substring)
    if not results:
        print("ничего не найдено ни в одной базе")
        return 1
    for name, rel_path, snip in results:
        print(f"[{name}] {rel_path}")
        print(f"  {snip}")
    print(f"\nитого: {len(results)} в {len({n for n, _, _ in results})} базах")
    return 0


if __name__ == "__main__":
    sys.exit(main())