#!/usr/bin/env python3
"""Полнотекстовый поиск по базе Wiki (база из build.py).

Примеры:
    python3 search.py страховка
    python3 search.py -b /путь/wiki.db рецепт
    python3 search.py "умный AND дом"
    python3 search.py --substring "гнцо"            # подстрока (trigram, >= 3)
    python3 search.py -p reference "врач"           # только в reference/
    python3 search.py --json "идея"                 # машинный вывод (JSON)
    python3 search.py --limit 5 отпуск
"""
import argparse
import json
import os
import sqlite3
import sys

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass

DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "wiki.db")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from log import log_search, search_stats

OPS = {"AND", "OR", "NOT", "NEAR"}


def sanitize_query(query):
    """Экранирует FTS5-запрос: токены со спецсимволами (кавычки, скобки,
    дефис — известная грабля «agent-lsp», звёздочки) оборачиваются в двойные
    кавычки. Операторы AND/OR/NOT/NEAR и готовые фразы в кавычках не
    трогаем, чтобы булева логика работала."""
    out = []
    for tok in query.split():
        upper = tok.upper()
        if upper in OPS or upper.startswith("NEAR(") or \
                (tok.startswith('"') and tok.endswith('"')):
            out.append(tok)
        elif any(c in tok for c in '\"-()*:^'):
            # Префиксный поиск (подмешк*) не оборачиваем: в кавычках
            # звёздочка становится литералом и префикс не работает.
            if tok.endswith("*") and not any(c in tok[:-1] for c in '\"-():^'):
                out.append(tok)
            else:
                out.append('"' + tok.replace('"', '""') + '"')
        else:
            out.append(tok)
    return " ".join(out)


def main():
    ap = argparse.ArgumentParser(description="Поиск по базе Wiki")
    ap.add_argument("query", nargs="?", help="FTS5-запрос, например: страховка или 'умный AND дом'")
    ap.add_argument("-b", "--db", default=DEFAULT_DB, help="путь к базе (по умолчанию db/wiki.db)")
    ap.add_argument("--limit", type=int, default=10, help="сколько результатов (по умолчанию 10)")
    ap.add_argument("--no-snippet", action="store_true", help="не показывать сниппеты")
    ap.add_argument("--substring", action="store_true",
                    help="поиск подстроки через trigram-индекс (запрос >= 3 символа)")
    ap.add_argument("-p", "--path", metavar="ПОДСТРОКА",
                    help="искать только в файлах, чей путь содержит подстроку")
    ap.add_argument("--json", action="store_true", help="вывод в JSON (машиночитаемо)")
    ap.add_argument("--stats", action="store_true",
                    help="метрики использования поиска (research.db search_log): "
                         "топ запросов, пустые, последние")
    ap.add_argument("--no-log", action="store_true",
                    help="не писать этот поиск в search_log (по умолчанию пишется)")
    ap.add_argument("--refresh", action="store_true",
                    help="пересобрать базу (инкрементально) перед поиском; "
                         "-r/--root и --extra-files берутся из аргументов")
    ap.add_argument("-r", "--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help="корень набора для --refresh (по умолчанию корень assistant-kit)")
    ap.add_argument("--extra-files", nargs="*", default=[],
                    help="внешние файлы вне root для --refresh")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if args.stats:
        s = search_stats()
        print(f"поисков всего: {s['total']}  (пустых: {s['empty']}, "
              f"{round(100 * s['empty'] / s['total'], 1) if s['total'] else 0}%)")
        if s["by_db"]:
            print("по базам: " + ", ".join(
                f"{r['db_name']} — {r['n']}" for r in s["by_db"]))
        print("\nтоп запросов (запрос | раз | найдено | пусто):")
        for r in s["top"]:
            print(f"  {r['query'][:60]:60} | {r['n']:3} | {r['found']:4} | {r['miss']}")
        print("\nпоследние:")
        for r in s["last"][:10]:
            print(f"  {r['ts']} [{r['tool']}] {r['db_name']}: "
                  f"{r['query'][:60]} -> {r['hits']}")
        return
    if args.refresh:
        import subprocess
        build_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build.py")
        cmd = [sys.executable, build_py, "-r", os.path.abspath(args.root),
               "-o", db_path]
        if args.extra_files:
            cmd += ["--extra-files"] + args.extra_files
        subprocess.run(cmd, check=True)
    if not os.path.exists(db_path):
        print(f"базы нет: {db_path}\nСначала запусти: python3 build.py -o {db_path}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    def out(data):
        """Единый вывод: JSON по флагу, иначе текст."""
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))

    if not args.query:
        print("задайте запрос (или --substring для поиска подстроки)",
              file=sys.stderr)
        sys.exit(1)

    if args.substring and len(args.query) < 3:
        print("--substring требует запрос не короче 3 символов",
              file=sys.stderr)
        sys.exit(1)

    idx = "files_fts_trigram" if args.substring else "files_fts"
    query = sanitize_query(args.query)
    path_cond = "AND f.rel_path LIKE ?" if args.path else ""
    params = [query]
    if args.path:
        params.append(f"%{args.path}%")
    if not args.no_snippet:
        sql = f"""
        SELECT f.rel_path, f.size_bytes,
               snippet({idx}, 1, '[', ']', '…', 12) AS snip
        FROM {idx}
        JOIN files f ON f.id = {idx}.rowid
        WHERE {idx} MATCH ? {path_cond}
        ORDER BY bm25({idx}, 10.0, 1.0)
        LIMIT ?
        """
    else:
        sql = f"""
        SELECT f.rel_path, f.size_bytes
        FROM {idx}
        JOIN files f ON f.id = {idx}.rowid
        WHERE {idx} MATCH ? {path_cond}
        ORDER BY bm25({idx}, 10.0, 1.0)
        LIMIT ?
        """
    params.append(args.limit)

    try:
        rows = cur.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        print(f"неверный запрос: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.no_log:
        log_search("search.py", os.path.basename(db_path).replace(".db", ""),
                   args.query, len(rows))

    if args.json:
        data = [dict(r) for r in rows]
        out(data)
        return

    if not rows:
        print("ничего не найдено")
        return

    print(f"найдено: {len(rows)}\n")
    for r in rows:
        print(f"{r['rel_path']}  ({r['size_bytes']} б)")
        if not args.no_snippet:
            print(f"  …{r['snip']}")
        print()


if __name__ == "__main__":
    main()
