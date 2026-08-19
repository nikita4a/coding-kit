#!/usr/bin/env python3

"""Лог поисков в research.db — метрики использования баз (пункт #4 обшивки).

Каждый поиск по базе (search.py, MCP db-tools) пишет строку в search_log:
когда, чем, в какой базе, какой запрос, сколько нашлось. Это позволяет
отвечать на «что мы реально ищем, что находим, где пусто» — а не гадать.

Использование:
    from log import log_search, search_stats
    log_search("search.py", "memory", "канон", 3)
    print(search_stats(20))

Таблица создаётся лениво при первом логировании — отдельная миграция не
нужна (research.db хранит и findings, и метрики).
"""
import datetime

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import _compat

ROOT = _compat.chulan_root()

DB = os.path.join(ROOT, "db", "research.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS search_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    tool TEXT NOT NULL,
    db_name TEXT NOT NULL DEFAULT '',
    query TEXT NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_search_log_ts ON search_log(ts);
CREATE INDEX IF NOT EXISTS idx_search_log_db ON search_log(db_name);
"""


def _connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def log_search(tool, db_name, query, hits):
    """Записать один поиск. Ошибки не роняют поиск — метрика вторична."""
    try:
        con = _connect()
        con.execute(
            "INSERT INTO search_log (ts, tool, db_name, query, hits) "
            "VALUES (?,?,?,?,?)",
            (datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
             tool, db_name, query[:200], hits))
        con.commit()
        con.close()
    except sqlite3.Error:
        pass


def search_stats(limit=20):
    """Сводка использования: всего, пустых, топ запросов, последние."""
    con = _connect()
    cur = con.cursor()
    total = cur.execute("SELECT COUNT(*) FROM search_log").fetchone()[0]
    empty = cur.execute(
        "SELECT COUNT(*) FROM search_log WHERE hits = 0").fetchone()[0]
    top = cur.execute(
        "SELECT query, COUNT(*) n, SUM(hits) found, "
        "SUM(CASE WHEN hits=0 THEN 1 ELSE 0 END) miss "
        "FROM search_log GROUP BY query ORDER BY n DESC LIMIT ?",
        (limit,)).fetchall()
    last = cur.execute(
        "SELECT ts, tool, db_name, query, hits FROM search_log "
        "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    by_db = cur.execute(
        "SELECT db_name, COUNT(*) n FROM search_log "
        "GROUP BY db_name ORDER BY n DESC").fetchall()
    con.close()
    return {"total": total, "empty": empty, "top": [dict(r) for r in top],
            "by_db": [dict(r) for r in by_db],
            "last": [dict(r) for r in last]}


def empty_queries(limit=30):
    """Майнинг пустых запросов: какие темы ищут и НЕ находят (все прогоны
    пустые) — кандидаты в доки/wiki (аудит 14.08, research.db id=489).
    Исключаем обрубки (одно слово без смысла) и служебный мусор."""
    con = _connect()
    rows = con.execute(
        "SELECT query, COUNT(*) n, MAX(ts) last_ts, db_name "
        "FROM search_log WHERE hits = 0 "
        "GROUP BY query HAVING n >= 2 ORDER BY n DESC LIMIT ?",
        (limit,)).fetchall()
    con.close()
    junk = {"test", "foo", "удал", "настройк", "подмешка"}
    out = []
    for r in rows:
        q = r["query"]
        if q.strip().lower() in junk or len(q) < 4:
            continue
        out.append(dict(r))
    return out
