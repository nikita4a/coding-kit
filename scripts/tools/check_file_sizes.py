#!/usr/bin/env python3

"""Единый гейт размера файлов coding-kit (god-файлы запрещены).

ОДИН источник правды лимитов. Потребители:
- doctor.py — проверка file-sizes (import collect);
- CI (.github/workflows/setup-test.yml) — `--ci` (exit 1 при нарушениях);
- правило в OPS.md — КОНСТАНТЫ-ЗЕРКАЛО
  (хук автономен, запускается из ~/.claude/hooks/ и т.п. — не импортирует
  scripts/); при правке лимитов менять ОБА места.

Лимиты (индустрия, research.db id=543):
- code: soft 500 / hard 1000 (SonarQube python:S104 = 1000, ESLint = 300 —
  мы между: context-бюджет агента);
- docs: soft 300 / hard 500 (канон-MD/SKILL.md читаются агентом целиком).

Grandfather (baseline, паттерн SonarQube new-code quality gate):
файлы, уже выше hard на момент ввода правила, фиксируются в
scripts/file_size_baseline.json с ТЕКУЩИМ числом строк (как меряет этот
скрипт). Им можно только УМЕНЬШАТЬСЯ (резка); рост = error. Новые файлы
выше hard — error всегда. После резки файла — удалить из baseline.

Запуск:
    python3 scripts/tools/check_file_sizes.py            # отчёт (exit 0)
    python3 scripts/tools/check_file_sizes.py --ci       # гейт: exit 1 при error
"""
import argparse
import json
import os
import subprocess
import sys

from pathlib import Path

# stdlib-only: no scripts/_compat.py dependency (memory/ moved out of the kit)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110 — optional, lives without it
    pass

ROOT = Path(__file__).resolve().parents[2]

# Лимиты: (soft, hard). soft = nudge/предупреждение, hard = блок/гейт.
LIMITS = {
    "code": {"soft": 500, "hard": 1000, "ext": (
        ".py", ".js", ".ts", ".sh", ".go", ".rs", ".java", ".c", ".cpp",
        ".css", ".html", ".toml")},
    "docs": {"soft": 300, "hard": 500, "ext": (".md",)},
}

# Каталоги вне дерева (по имени, любой уровень).
EXCLUDE_DIRS = {".git", "db", "node_modules", "__pycache__", ".cache",
                "dist", "build", "vendor"}

# Имена, которые не считаются (append-only журналы, генерируемое, бэкапы).
EXCLUDE_NAMES = {"CHANGELOG.md", "index.md"}

BASELINE_PATH = Path(__file__).resolve().parent.parent / "file_size_baseline.json"


def _tier_for(rel_path: str):
    ext = os.path.splitext(rel_path)[1].lower()
    for tier, conf in LIMITS.items():
        if ext in conf["ext"]:
            return tier
    return None


def _count_lines(path: Path) -> int:
    """Строки как wc -l: число \n (бинарно, быстро). Файл без хвостового
    перевода строки теряет последнюю строку на единицу — как wc -l и база
    (db/files.lines), с которой сверяемся."""
    with open(path, "rb") as fh:
        return sum(1 for _ in fh)


def _load_baseline():
    if not BASELINE_PATH.is_file():
        return {}
    with open(BASELINE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _level(rel: str, lines: int, tier: str, baseline: dict):
    """(level, cap) для одного файла: level (hard/baseline-grown/soft/
    baseline-done/baseline-ok) или None (в лимитах); cap — фиксатор baseline."""
    conf = LIMITS[tier]
    if rel in baseline:
        cap = baseline[rel].get("lines", conf["hard"])
        if lines > cap:
            return "baseline-grown", cap
        if lines <= conf["hard"]:
            return "baseline-done", cap
        return "baseline-ok", cap
    if lines > conf["hard"]:
        return "hard", None
    if lines > conf["soft"]:
        return "soft", None
    return None, None


def collect(root: Path) -> list:
    """Все файлы дерева с числом строк и вердиктом. Только нарушения
    (soft/hard/baseline-grown) + baseline-done — чистые не возвращаем."""
    baseline = _load_baseline()
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS
                             and not d.startswith("venv"))
        for name in sorted(filenames):
            if name in EXCLUDE_NAMES or name.endswith((".bak", ".orig")):
                continue
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            tier = _tier_for(rel)
            if tier is None:
                continue
            try:
                lines = _count_lines(full)
            except OSError:
                continue
            level, cap = _level(rel, lines, tier, baseline)
            if level in (None, "baseline-ok"):
                continue
            rows.append({"rel_path": rel, "lines": lines, "tier": tier,
                         "level": level, "cap": cap})
    return rows


def staged_rows(root: Path) -> list:
    """Вердикты по файлам в git-индексе (staged): считаем строки их
    ЗАКОММИЧИВАЕМОГО содержимого (git show :путь), а не рабочего дерева.
    Пропускаем удалённые/бинарные/вне-тиров. Пустой результат — не гейт."""
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "-z"],
            cwd=str(root), capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    baseline = _load_baseline()
    rows = []
    for rel in r.stdout.decode("utf-8", "replace").split("\0"):
        rel = rel.strip()
        if not rel:
            continue
        tier = _tier_for(rel)
        if tier is None or os.path.basename(rel) in EXCLUDE_NAMES:
            continue
        try:
            g = subprocess.run(["git", "show", f":{rel}"],
                               cwd=str(root), capture_output=True,
                               timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if g.returncode != 0:
            continue  # удалённый из индекса/не staged-контент
        lines = g.stdout.count(b"\n")
        level, cap = _level(rel, lines, tier, baseline)
        if level in (None, "baseline-ok"):
            continue
        rows.append({"rel_path": rel, "lines": lines, "tier": tier,
                     "level": level, "cap": cap})
    return rows


def gate(rows: list) -> tuple:
    """(errors, warnings, info). error = hard/baseline-grown; warning = soft;
    info = baseline-done (уже под hard — фиксатор можно снять)."""
    errors = [r for r in rows if r["level"] in ("hard", "baseline-grown")]
    warnings = [r for r in rows if r["level"] == "soft"]
    info = [r for r in rows if r["level"] == "baseline-done"]
    return errors, warnings, info


def _fmt(r: dict) -> str:
    lim = LIMITS[r["tier"]]
    if r["level"] == "baseline-grown":
        return (f"{r['rel_path']}: {r['lines']} строк (> baseline "
                f"{r.get('cap')}) — РОСТ ЗАПРЕЩЁН, только резка")
    if r["level"] == "baseline-done":
        return (f"{r['rel_path']}: {r['lines']} строк (уже <= hard "
                f"{lim['hard']}) — удали файл из baseline: начнёт действовать "
                f"hard-лимит")
    if r["level"] == "hard":
        return (f"{r['rel_path']}: {r['lines']} строк (> hard {lim['hard']}) "
                f"— god-файл: режь или впиши в baseline с причиной")
    return (f"{r['rel_path']}: {r['lines']} строк (> soft {lim['soft']}, "
            f"hard {lim['hard']})")


def main():
    ap = argparse.ArgumentParser(description="Гейт размера файлов (god-файлы)")
    ap.add_argument("--ci", action="store_true",
                    help="гейт CI: exit 1 при error-нарушениях")
    ap.add_argument("--quiet", action="store_true",
                    help="только ошибки, без предупреждений")
    ap.add_argument("--root", default=None,
                    help="корень для сканирования (по умолчанию — корень "
                         "coding-kit; для pre-commit хука — git rev-parse "
                         "--show-toplevel)")
    ap.add_argument("--staged", action="store_true",
                    help="гейт staged-файлов (git diff --cached): считает "
                         "строки ИХ индексированного содержимого, exit 1 при "
                         "error. Для git pre-commit хука")
    ap.add_argument("--reviewdog", action="store_true",
                    help="вывод hard-нарушений в формате reviewdog "
                         "errorformat: путь:1:1: сообщение")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else ROOT

    if args.staged:
        rows = staged_rows(root)
        errors, warnings, info = gate(rows)
        for r in errors:
            print(f"[✗] {_fmt(r)}")
        for r in info:
            print(f"[i] {_fmt(r)}")
        if errors:
            print(f"итого: staged-нарушений {len(errors)} — коммит заблокирован")
            sys.exit(1)
        print(f"[✓] staged-файлы в лимитах ({len(rows)} предупреждений)" if warnings
              else "[✓] staged-файлы в лимитах")
        sys.exit(0)

    rows = collect(root)
    errors, warnings, info = gate(rows)

    if args.reviewdog:
        # Формат errorformat %f:%l:%c: %m — reviewdog постит в PR/check.
        for r in errors:
            print(f"{r['rel_path']}:1:1: god-файл: {_fmt(r)}")
        sys.exit(0)

    if errors:
        print(f"[✗] hard-нарушения ({len(errors)}):")
        for r in errors:
            print(f"  {_fmt(r)}")
    if warnings and not args.quiet:
        print(f"[!] выше soft-лимита ({len(warnings)}):")
        for r in warnings:
            print(f"  {_fmt(r)}")
    if info and not args.quiet:
        print(f"[i] baseline-фиксаторы можно снять ({len(info)}):")
        for r in info:
            print(f"  {_fmt(r)}")
    if not errors and not warnings and not info:
        print("[✓] все файлы в лимитах (soft/hard)")
    elif not errors:
        print(f"итого: hard 0, soft {len(warnings)} — гейт зелёный")
    sys.exit(1 if (args.ci and errors) else 0)


if __name__ == "__main__":
    main()
