#!/usr/bin/env python3

"""Журнал задач (research.db, таблица tasks) — event-sourced история работ.

Зачем: находки отвечают на «что мы знаем», журнал — на «что мы делали,
когда и чем кончилось». Переживает перезапуск сессии и смену харнеса
(паттерн индустрии: file-based/event-sourced memory, understandingdata.com).

Правила:
- записи append-only: не удаляются (это журнал, time-travel);
- задача в работе — status=active; по итогу — close (done) или
  abort/block (aborted/blocked);
- «чем кончилось» — в --result одной-двумя строками (не пересказ).

Примеры:
    python3 tasks.py add "Переписать прошивку под 7 харнесов" --tags proshivka
    python3 tasks.py list
    python3 tasks.py list --status active
    python3 tasks.py close 3 --result "сторож PreToolUse в 6/7 харнесов"
    python3 tasks.py block 3 --reason "нужен доступ владельца"
    python3 tasks.py search прошивка
    python3 tasks.py stats
"""
import argparse
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import _compat

ROOT = _compat.chulan_root()

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass


DB = os.path.join(ROOT, "db", "research.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    result TEXT DEFAULT '',
    closed TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    source TEXT DEFAULT ''
);
CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
    task, result, content='tasks', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS tasks_ai AFTER INSERT ON tasks BEGIN
    INSERT INTO tasks_fts(rowid, task, result)
    VALUES (new.id, new.task, new.result);
END;
CREATE TRIGGER IF NOT EXISTS tasks_au AFTER UPDATE ON tasks BEGIN
    INSERT INTO tasks_fts(tasks_fts, rowid, task, result)
    VALUES ('delete', old.id, old.task, old.result);
    INSERT INTO tasks_fts(rowid, task, result)
    VALUES (new.id, new.task, new.result);
END;
"""

STATUSES = {"active", "done", "aborted", "blocked"}


def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    con.commit()
    return con


def _now():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")


def _warn_active(con, cur):
    act = cur.execute("SELECT COUNT(*) FROM tasks WHERE status='active'") \
        .fetchone()[0]
    if act:
        print(f"[~] открытых задач: {act} — не забудь закрыть по итогу",
              file=sys.stderr)


def cmd_add(args):
    con = connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO tasks (created, task, status, tags, source) "
        "VALUES (?,?, 'active', ?, ?)",
        (_now(), args.task, args.tags, args.source or ""))
    new_id = cur.lastrowid
    con.commit()
    print(f"[✓] задача: {args.task} (id={new_id})")
    _warn_active(con, cur)
    con.close()


def cmd_close(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT * FROM tasks WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"задачи с id={args.id} нет")
        return
    if not args.result:
        print("укажи --result «чем кончилось» (одна-две строки)")
        return
    cur.execute(
        "UPDATE tasks SET status='done', result=?, closed=? WHERE id=?",
        (args.result, _now(), args.id))
    con.commit()
    print(f"[✓] закрыто: [{args.id}] {row['task']}")
    print(f"    итог: {args.result}")
    con.close()


def cmd_abort(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT * FROM tasks WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"задачи с id={args.id} нет")
        return
    cur.execute(
        "UPDATE tasks SET status='aborted', result=?, closed=? WHERE id=?",
        (args.reason or "отменена", _now(), args.id))
    con.commit()
    print(f"[✗] отменена: [{args.id}] {row['task']} ({args.reason or 'без причины'})")
    con.close()


def cmd_block(args):
    con = connect()
    cur = con.cursor()
    row = cur.execute("SELECT * FROM tasks WHERE id = ?",
                      (args.id,)).fetchone()
    if not row:
        print(f"задачи с id={args.id} нет")
        return
    cur.execute(
        "UPDATE tasks SET status='blocked', result=?, closed=? WHERE id=?",
        (args.reason or "заблокирована", _now(), args.id))
    con.commit()
    print(f"[■] заблокирована: [{args.id}] {row['task']} ({args.reason or 'без причины'})")
    con.close()


def cmd_list(args):
    con = connect()
    cur = con.cursor()
    if args.status == "all":
        rows = cur.execute(
            "SELECT * FROM tasks ORDER BY id DESC LIMIT ?",
            (args.limit,)).fetchall()
    else:
        rows = cur.execute(
            "SELECT * FROM tasks WHERE status=? ORDER BY id DESC LIMIT ?",
            (args.status, args.limit)).fetchall()
    if not rows:
        print(f"задач со статусом {args.status} нет")
        return
    print(f"задач: {len(rows)} (статус: {args.status})\n")
    marks = {"active": "▸", "done": "✓", "aborted": "✗", "blocked": "■"}
    for r in rows:
        tail = ""
        if r["status"] == "done":
            tail = f" — {r['result'][:60]}"
        elif r["result"]:
            tail = f" ({r['result'][:60]})"
        print(f"{marks.get(r['status'], '?')} [{r['id']}] {r['created']}  "
              f"{r['task']}{tail}")
    con.close()


def cmd_search(args):
    con = connect()
    cur = con.cursor()
    from findings import sanitize_query
    try:
        rows = cur.execute(
            "SELECT t.id, t.created, t.status, t.task, t.result, "
            "snippet(tasks_fts, 1, '[', ']', '…', 12) AS snip "
            "FROM tasks_fts JOIN tasks t ON t.id = tasks_fts.rowid "
            "WHERE tasks_fts MATCH ? ORDER BY t.id DESC LIMIT ?",
            (sanitize_query(args.query), args.limit)).fetchall()
    except sqlite3.OperationalError as e:
        print(f"неверный запрос: {e}", file=sys.stderr)
        sys.exit(1)
    if not rows:
        print(f"ничего не найдено по «{args.query}»")
        return
    print(f"найдено: {len(rows)}\n")
    for r in rows:
        print(f"[{r['id']}] {r['status']:8} {r['created']}  {r['task']}")
        print(f"  …{r['snip']}")
        print()
    con.close()


def cmd_stats(args):
    con = connect()
    cur = con.cursor()
    total = cur.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    by_status = {r["status"]: r["n"] for r in cur.execute(
        "SELECT status, COUNT(*) n FROM tasks GROUP BY status").fetchall()}
    print(f"задач в журнале: {total}")
    for s in ("active", "blocked", "done", "aborted"):
        n = by_status.get(s, 0)
        if n or s in ("active", "done"):
            print(f"  {s:8} | {n}")
    con.close()


def main():
    ap = argparse.ArgumentParser(description="Журнал задач (append-only)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="завести задачу")
    p_add.add_argument("task", help="что делаем, одной строкой")
    p_add.add_argument("--tags", default="", help="теги через пробел")
    p_add.add_argument("--source", default="", help="откуда задача (путь/URL)")
    p_add.set_defaults(fn=cmd_add)

    p_list = sub.add_parser("list", help="список задач")
    p_list.add_argument("--status", default="active",
                        choices=["active", "done", "aborted", "blocked", "all"],
                        help="фильтр по статусу (по умолчанию active)")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.set_defaults(fn=cmd_list)

    p_close = sub.add_parser("close", help="закрыть задачу по итогу")
    p_close.add_argument("id", type=int)
    p_close.add_argument("--result", required=True,
                         help="чем кончилось (одна-две строки)")
    p_close.set_defaults(fn=cmd_close)

    p_abort = sub.add_parser("abort", help="отменить задачу")
    p_abort.add_argument("id", type=int)
    p_abort.add_argument("--reason", default="", help="почему отменили")
    p_abort.set_defaults(fn=cmd_abort)

    p_block = sub.add_parser("block", help="заблокировать задачу")
    p_block.add_argument("id", type=int)
    p_block.add_argument("--reason", default="", help="что мешает")
    p_block.set_defaults(fn=cmd_block)

    p_search = sub.add_parser("search", help="поиск по журналу (FTS5)")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.set_defaults(fn=cmd_search)

    p_stats = sub.add_parser("stats", help="метрики журнала")
    p_stats.set_defaults(fn=cmd_stats)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()


