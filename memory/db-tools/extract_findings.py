#!/usr/bin/env python3

"""Авто-разбор истории сессий → кандидаты в research.db (пункт #1 обшивки).

Проблема: знания из разговоров (транскрипты sherpa-voice, истории чатов)
умирают в логах — findings добавляются только вручную. Скрипт пробегает по
истории, находит строки с маркерами идей/решений/проблем и показывает их
кандидатами. Полу-авто: по умолчанию только показывает (--dry-run), добавка
в базу — по номерам (--add 1,3,5).

Поддерживаемые форматы:
  - sherpa-voice history.md:  "## 2026-08-08" + "- `2026-08-08 13:05:15` текст"
  - sherpa-voice history.txt: "[2026-08-08 13:05:15] текст"
  - произвольный текст: строки как есть (--file)

Примеры:
    python3 extract_findings.py                          # кандидаты из history.md
    python3 extract_findings.py --file any.txt           # свой файл
    python3 extract_findings.py --add 1,3,7              # добавить выбранные в базу
    python3 extract_findings.py --min-len 80             # длиннее строки
    python3 extract_findings.py --tags session ideas     # свои теги при добавке
"""
import argparse
import datetime
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import _compat

ROOT = _compat.chulan_root()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален
    pass


DEFAULT_HISTORY = os.path.expanduser("~/.cache/sherpa-voice/history.md")
DB = os.path.join(ROOT, "db", "research.db")

# Маркеры «здесь есть знание»: предложение, решение, проблема, урок.
# Слова раздельно, чтобы не ловить «добавить» в «добавление» шумно,
# но по-русски без стемминга — ловим по подстроке с учётом контекста.
MARKERS = (
    "предлагаю", "нужно добавить", "надо добавить", "добавить", "давай добавим",
    "проблема", "не работает", "ошибка", "баг", "грабля", "урок", "вывод",
    "решение", "прикол в том", "понял, в чём", "важно", "правило", "надо",
    "стоит", "сделать", "сделаем", "реализовать", "стоило бы", "хорошо бы",
    "нужно", "заметил", "обнаружил", "выяснил", "получилось", "сломалось",
    "а что если", "давай попробуем", "проверить",
)

# Сильные маркеры: знание, даже если строка — вопрос или жалоба.
STRONG = ("предлагаю", "нужно добавить", "надо добавить", "давай добавим",
          "проблема", "не работает", "ошибка", "баг", "грабля", "урок",
          "вывод", "решение", "прикол в том", "сломалось", "обнаружил",
          "выяснил", "получилось")

# Короткие/служебные строки, которые не знание: приветствия, проверки связи.
NOISE = (
    "привет", "тест", "алло", "ха-ха", "проверка", "ау", "ок", "окей",
    "спасибо", "понятно", "ага", "угу", "да", "нет", "ну", "как дела",
    "как твои дела", "кто ты", "что делаешь", "занят", "пока", "до связи",
)

# Вопросительные без маркеров — не кандидаты (вопрос ≠ вывод), но с
# маркером «почему/а что если» — кандидаты (это ход мысли).
QUESTION_WORDS = ("как сделать", "как работает", "как устроен", "расскажи",
                  "объясни", "что такое", "что думаешь")


def parse_history(path):
    """Строки из файла: [(дата_или_None, текст)]. Форматы выше."""
    lines = []
    cur_date = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n").strip()
            if not line:
                continue
            m = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})", line)
            if m:
                cur_date = m.group(1)
                continue
            if line.startswith("## "):
                continue  # заголовок-не-дата (вставленные промты/правила) — не знание
            m = re.match(r"^-\s*`([^`]+)`\s*(.*)$", line)       # history.md
            if m:
                lines.append((cur_date or m.group(1)[:10], m.group(2)))
                continue
            m = re.match(r"^\[([^\]]+)\]\s*(.*)$", line)        # history.txt
            if m:
                lines.append((cur_date or m.group(1)[:10], m.group(2)))
                continue
            if line.startswith("- "):
                continue  # markdown-список (вставленные правила/промты) — не речь
            lines.append((cur_date, line))
    return lines


def is_candidate(text, min_len):
    if len(text) < min_len:
        return False
    low = text.lower()
    if any(n in low for n in NOISE) and len(text) < 60:
        return False
    if not any(m in low for m in MARKERS):
        return False
    # Вопрос («как сделать X») без сильного маркера — не знание, а запрос.
    if any(q in low for q in QUESTION_WORDS) and \
            not any(m in low for m in STRONG):
        return False
    if len(text) > 300:  # длинные рассуждения — кандидат только с сильным маркером
        return any(m in low for m in STRONG)
    return True


def candidates(path, min_len):
    out = []
    seen = set()
    for date, text in parse_history(path):
        if not is_candidate(text, min_len):
            continue
        # Нормализация для дедупа: буквы/цифры в нижнем регистре, первые 80.
        norm = "".join(c for c in " ".join(text.split()).lower()
                       if c.isalnum())[:80]
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append((date, text))
    return out


def topic_of(text):
    """Тема из текста: первые слова до ~60 символов, без хвоста."""
    t = " ".join(text.split())
    return t[:60] + ("…" if len(t) > 60 else "")


def already_exists(con, topic):
    """Проверка дубликата: та же тема (обрезанная) или точное совпадение."""
    r = con.execute(
        "SELECT 1 FROM findings WHERE topic = ? OR topic = ? LIMIT 1",
        (topic, topic.rstrip("…"))).fetchone()
    return r is not None


def cmd_main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", default=DEFAULT_HISTORY,
                    help="файл истории (по умолчанию history.md sherpa-voice)")
    ap.add_argument("--min-len", type=int, default=40,
                    help="минимальная длина строки-кандидата (по умолчанию 40)")
    ap.add_argument("--add", default="",
                    help="добавить кандидатов по номерам: 1,3,7 (по умолчанию "
                         "только показ, dry-run)")
    ap.add_argument("--tags", default="session",
                    help="теги для добавляемых находок (по умолчанию 'session')")
    ap.add_argument("--limit", type=int, default=30,
                    help="сколько кандидатов показать (по умолчанию 30)")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        print(f"нет файла истории: {args.file}", file=sys.stderr)
        sys.exit(1)

    cands = candidates(args.file, args.min_len)
    if not cands:
        print(f"кандидатов не найдено в {args.file} (min_len={args.min_len})")
        return

    print(f"кандидатов: {len(cands)} (из {args.file})\n")
    for i, (date, text) in enumerate(cands[:args.limit], 1):
        one = " ".join(text.split())
        print(f"[{i}] {date or '????-??-??'}  {one[:110]}")
        if len(one) > 110:
            print(f"      …{one[110:220]}")
    if len(cands) > args.limit:
        print(f"\n…и ещё {len(cands) - args.limit} (поднимите --limit)")

    if not args.add:
        print("\nдобавка в базу — по номерам: --add 1,3,7 (см. --help)")
        return

    wanted = set()
    for part in args.add.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(cands):
            wanted.add(int(part))
    if not wanted:
        print("неверные номера для --add", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    added = skipped = 0
    for i, (date, text) in enumerate(cands, 1):
        if i not in wanted:
            continue
        topic = topic_of(text)
        if already_exists(con, topic):
            print(f"[!] пропуск дубликата [{i}]: {topic}")
            skipped += 1
            continue
        con.execute(
            "INSERT INTO findings (created, topic, text, tags, source) "
            "VALUES (?,?,?,?,?)",
            (now, topic, f"{text}\n\n[из истории {args.file} от {date}]",
             args.tags, args.file))
        print(f"[✓] добавлено [{i}] id={con.execute('SELECT last_insert_rowid()').fetchone()[0]}: {topic}")
        added += 1
    con.commit()
    con.close()
    print(f"\nитог: добавлено {added}, пропущено дубликатов {skipped}")


if __name__ == "__main__":
    cmd_main()
