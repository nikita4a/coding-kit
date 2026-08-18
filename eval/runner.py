#!/usr/bin/env python3
"""eval/runner.py — trap-suite прогон сценариев coding-kit.

Сценарий eval/scenarios/*.md: frontmatter (name, skill, trap, expect) + тело.
Тело подаётся модели как задание. Ответ модели + expect подаются судье
(вторая модель), который ставит PASS/FAIL с обоснованием.

Бэкенд модели подключается через `--executor CMD`: команда, читающая промпт
со stdin и печатающая ответ в stdout (например: `gemini -p -` для Gemini CLI).
Без --executor сценарии только валидируются (dry-run).

Использование:
    python eval/runner.py                     # dry-run: валидация сценариев
    python eval/runner.py --executor "gemini -p -"   # прогон через Gemini CLI
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ROOT / "eval" / "scenarios"


def parse(text: str) -> dict:
    meta, _, body = text.partition("\n\n")
    out = {"body": body.strip()}
    for line in meta.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--executor", help="команда вызова модели (промпт на stdin)")
    ap.add_argument("--judge", default=None, help="команда судьи (по умолчанию = --executor)")
    ap.add_argument("--scenario", help="имя одного сценария (без .md)")
    args = ap.parse_args()

    files = sorted(SCENARIOS.glob("*.md"))
    if args.scenario:
        files = [SCENARIOS / f"{args.scenario}.md"]
    if not files:
        print("сценариев нет")
        return 1

    for f in files:
        sc = parse(f.read_text(encoding="utf-8"))
        ok = all(k in sc for k in ("name", "skill", "trap", "expect", "body"))
        print(f"{'OK ' if ok else 'BAD'} {f.name} [{sc.get('skill','?')}] trap: {sc.get('trap','?')[:60]}")
        if not ok:
            continue
        if not args.executor:
            print(f"     (dry-run: body {len(sc['body'])} chars, expect {sc['expect'][:50]}...)")
            continue
        try:
            run = subprocess.run(
                args.executor, shell=True, input=sc["body"],
                capture_output=True, text=True, timeout=600,
                encoding="utf-8", errors="replace",
            )
            answer = (run.stdout or run.stderr).strip()
        except Exception as e:
            print(f"     EXECUTOR FAIL: {e}")
            continue
        judge_prompt = (
            f"Сценарий оценивает следующее поведение:\nОЖИДАНИЕ: {sc['expect']}\n\n"
            f"Ответ агента:\n{answer}\n\n"
            f"Совпадает ли ответ агента с ожиданием? Ответь одной строкой: "
            f"PASS или FAIL, затем обоснование в одну строку."
        )
        judge_cmd = args.judge or args.executor
        try:
            jr = subprocess.run(
                judge_cmd, shell=True, input=judge_prompt,
                capture_output=True, text=True, timeout=600,
                encoding="utf-8", errors="replace",
            )
            verdict = (jr.stdout or jr.stderr).strip()
        except Exception as e:
            verdict = f"JUDGE FAIL: {e}"
        print(f"     → {verdict[:200]}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())