#!/usr/bin/env python3

"""Repo-map: карта файла/проекта из базы для промпта агента.

Паттерн индустрии (aider repomap / goldfish / repomap-mcp / CodeGraphX):
агент тратит 40-60% токенов на ориентацию в коде (греп, чтение файлов);
карта — PageRank по символьному/импорт-графу из базы + рендер в
токен-бюджет. Сырьё уже в базе: symbols (имя/kind/строка/сигнатура),
imports (rel_path → module), calls (rel_path → callee). PageRank —
чистый python (power iteration), без numpy (паттерн repomap-mcp).

Использование:
    python3 db-tools/repomap.py project --db db/wiki.db --tokens 1500
    python3 db-tools/repomap.py project --focus db-tools/search.py
    python3 db-tools/repomap.py file db-tools/search.py --db db/wiki.db
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

from _compat import chulan_root, fix_encoding  # noqa: E402 — единый хелпер канона

fix_encoding()

DEFAULT_DB = chulan_root() / "db" / "wiki.db"
CHAR_PER_TOKEN = 3  # грубая оценка: код ~3-4 симв/токен, русский ~2.5


def _connect(db):
    return sqlite3.connect(db)


def _module_index(conn) -> dict:
    """module → [rel_path, ...] по всем файлам базы."""
    idx = {}
    for (rel_path,) in conn.execute("SELECT rel_path FROM files"):
        stem = rel_path.replace("\\", "/").rsplit("/", 1)[-1]
        stem = stem.removesuffix(".py")
        idx.setdefault(stem, []).append(rel_path)
    return idx


def file_graph(conn) -> tuple[dict, dict]:
    """Граф импортов между файлами: {file: {target: w}} + reverse."""
    midx = _module_index(conn)
    graph, reverse = {}, {}
    for rel_path, module in conn.execute(
            "SELECT DISTINCT rel_path, module FROM imports"):
        targets = midx.get(module, [])
        for t in targets:
            if t == rel_path:
                continue
            graph.setdefault(rel_path, {}).setdefault(t, 0)
            graph[rel_path][t] += 1
            reverse.setdefault(t, {}).setdefault(rel_path, 0)
            reverse[t][rel_path] += 1
    return graph, reverse


def page_rank(graph: dict, focus: list | None = None,
              iters: int = 20) -> dict:
    """PageRank по взвешенному графу; focus — список путей для буста."""
    nodes = set(graph)
    for edges in graph.values():
        nodes |= set(edges)
    if not nodes:
        return {}
    n = len(nodes)
    score = {node: 1.0 / n for node in nodes}
    boost = 2.0
    for _ in range(iters):
        nxt = {node: (1.0 - 0.85) / n for node in nodes}
        for src, edges in graph.items():
            total = sum(edges.values())
            if not total:
                continue
            for dst, w in edges.items():
                nxt[dst] = nxt.get(dst, 0.0) + 0.85 * score[src] * w / total
        score = nxt
    if focus:
        for f in focus:
            if f in score:
                score[f] *= boost
    return score


def _symbols_of(conn, rel_path: str) -> list:
    rows = conn.execute(
        "SELECT name, kind, line FROM symbols WHERE rel_path=? "
        "ORDER BY line", (rel_path,)).fetchall()
    return rows


def _callers_of(conn, callees: set, limit: int = 12) -> list:
    if not callees:
        return []
    q = "SELECT DISTINCT rel_path, callee FROM calls WHERE callee IN (%s)" % (
        ",".join("?" * len(callees)))
    # параметризованный sqlite3 (?-плейсхолдеры, значения — через params);
    # semgrep-правило рассчитано на SQLAlchemy — см. search.py:237
    rows = conn.execute(q, list(callees)).fetchall()  # nosemgrep: sqlalchemy-execute-raw-query
    seen, out = set(), []
    for rel_path, callee in rows:
        key = (rel_path, callee)
        if key in seen:
            continue
        seen.add(key)
        out.append((rel_path, callee))
        if len(out) >= limit:
            break
    return out


def map_file(conn, rel_path: str, tokens: int = 800) -> str:
    """Карта одного файла: символы + кто зовёт его функции + кого зовёт."""
    rel_path = rel_path.replace("\\", "/")
    candidates = {rel_path, rel_path.replace("/", "\\")}
    row = conn.execute(
        "SELECT rel_path FROM files WHERE rel_path IN (?,?) LIMIT 1",
        tuple(candidates)).fetchone()
    if row:
        rel_path = row[0]  # канонический вид из базы
    syms = _symbols_of(conn, rel_path)
    if not syms:
        return f"файл не найден или без символов: {rel_path}"
    budget = tokens * CHAR_PER_TOKEN
    out = [f"# {rel_path} ({len(syms)} символов)"]
    used = len(out[0])
    shown = []
    for name, kind, line in syms:
        s = f"{line:>5} {kind[:9]:9} {name}"
        if used + len(s) > budget * 0.7:
            shown.append("…")
            break
        shown.append(s)
        used += len(s)
    out.append("\n".join(shown))
    names = {n for n, _, _ in syms}
    callers = _callers_of(conn, names)
    if callers:
        cset = sorted({f"{c} → {n}" for c, n in callers})
        out.append("// зовут его: " + ", ".join(cset[:10]))
    out_edges = conn.execute(
        "SELECT DISTINCT callee FROM calls WHERE rel_path=? LIMIT 20",
        (rel_path,)).fetchall()
    if out_edges:
        out.append("// он зовёт: " + ", ".join(
            c[0] for c in out_edges))
    return "\n".join(out)[:budget]


def map_project(conn, tokens: int = 2000, focus: list | None = None) -> str:
    """Карта проекта: PageRank по импорт-графу → топ-файлы с символами."""
    graph, reverse = file_graph(conn)
    ranks = page_rank(graph, focus=focus)
    budget = tokens * CHAR_PER_TOKEN
    order = sorted(ranks, key=ranks.get, reverse=True)
    total_files = len(order)
    out = [f"# Карта проекта ({total_files} файлов, бюджет ~{tokens} ток)"]
    used = len(out[0])
    shown = 0
    for rel_path in order:
        syms = _symbols_of(conn, rel_path)
        if not syms:
            continue
        names = ", ".join(n for n, _, _ in syms[:12])
        head = f"\n{rel_path} · {len(syms)} симв · входящих {len(reverse.get(rel_path, {}))}"
        line = f"{head}\n  {names}"
        if used + len(line) > budget:
            out.append(f"\n… (показано {shown} из {total_files})")
            break
        out.append(line)
        used += len(line)
        shown += 1
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="what", required=True)
    p = sub.add_parser("project", help="карта всего проекта (PageRank)")
    f = sub.add_parser("file", help="карта одного файла")
    for sp in (p, f):
        sp.add_argument("--db", default=str(DEFAULT_DB))
        sp.add_argument("--tokens", type=int, default=2000 if sp is p else 800)
    p.add_argument("--focus", nargs="*", default=None,
                   help="буст файлов в ранжировании")
    f.add_argument("path", help="rel_path файла")
    args = ap.parse_args()
    conn = _connect(args.db)
    try:
        if args.what == "project":
            print(map_project(conn, tokens=args.tokens, focus=args.focus))
        else:
            print(map_file(conn, args.path, tokens=args.tokens))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())