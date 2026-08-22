#!/usr/bin/env python3
"""eval/runner.py — trap-suite scenario runner for coding-kit.

Scenario eval/scenarios/*.md: frontmatter (name, skill, trap, expect) + body.
The body is fed to a model as a task; the model's answer plus the `expect`
line is fed to a judge (a second model call), which returns PASS/FAIL with
reasoning.

The model backend plugs in via `--executor CMD` (reads prompt from stdin,
prints answer to stdout — e.g. `gemini -p -`). Without `--executor`, scenarios
are only validated (dry-run). The executor spec is developer-owned config,
never user input; it is parsed with shlex and run WITHOUT shell=True
(.cmd/.bat targets are wrapped in `cmd /c` so Windows batch launchers work).

Usage:
    python eval/runner.py                        # dry-run: validate scenarios
    python eval/runner.py --executor "gemini -p -"        # run via Gemini CLI
    python eval/runner.py --executor "…" --repeat 3       # flake gate: all N must PASS
"""
import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ROOT / "eval" / "scenarios"


def resolve_cmd(spec: str) -> list[str]:
    """CLI string -> argv list. No shell; .cmd/.bat run through cmd /c."""
    parts = shlex.split(spec)
    if not parts:
        return []
    exe = shutil.which(parts[0])
    if exe and os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe, *parts[1:]]
    return [exe or parts[0], *parts[1:]]


def run_prompt(cmd: list[str], prompt: str, timeout: int = 600) -> str:
    r = subprocess.run(
        cmd, input=prompt, capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace",
    )
    return (r.stdout or r.stderr).strip()


def parse(text: str) -> dict:
    meta, _, body = text.partition("\n\n")
    out = {"body": body.strip()}
    for line in meta.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def judge_one(judge_cmd: list[str], expect: str, answer: str) -> str:
    prompt = (
        f"The scenario expects the following behavior:\nEXPECT: {expect}\n\n"
        f"Agent's answer:\n{answer}\n\n"
        f"Does the agent's answer match the expectation? One line: "
        f"PASS or FAIL, then one line of reasoning."
    )
    return run_prompt(judge_cmd, prompt)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--executor", help="model CLI (prompt on stdin)")
    ap.add_argument("--judge", default=None,
                    help="judge CLI (default = --executor)")
    ap.add_argument("--scenario", help="single scenario name (no .md)")
    ap.add_argument("--repeat", type=int, default=1,
                    help="flake gate: scenario must PASS N times in a row")
    args = ap.parse_args()

    executor = resolve_cmd(args.executor) if args.executor else None
    judge = resolve_cmd(args.judge) if args.judge else executor

    files = sorted(SCENARIOS.glob("*.md"))
    if args.scenario:
        files = [SCENARIOS / f"{args.scenario}.md"]
    if not files:
        print("no scenarios found")
        return 1

    fails = 0
    for f in files:
        sc = parse(f.read_text(encoding="utf-8"))
        ok = all(k in sc for k in ("name", "skill", "trap", "expect", "body"))
        print(f"{'OK ' if ok else 'BAD'} {f.name} [{sc.get('skill','?')}] "
              f"trap: {sc.get('trap','?')[:60]}")
        if not ok:
            fails += 1
            continue
        if not executor:
            print(f"     (dry-run: body {len(sc['body'])} chars, "
                  f"expect {sc['expect'][:50]}...)")
            continue
        outcomes = []
        for i in range(args.repeat):
            try:
                answer = run_prompt(executor, sc["body"])
            except Exception as e:
                print(f"     EXECUTOR FAIL: {e}")
                fails += 1
                break
            try:
                verdict = judge_one(judge, sc["expect"], answer)
            except Exception as e:
                verdict = f"JUDGE FAIL: {e}"
            passed = verdict.strip().lower().startswith("pass")
            if not passed:
                fails += 1
            outcomes.append(f"attempt {i+1}: {verdict[:160]}")
        print("\n     " + "\n     ".join(outcomes)
              if outcomes else f"     (no runs)")
    print(f"\noverall: {'ALL GREEN' if not fails else f'{fails} non-PASS'}"
          f" ({len(files)} scenarios x {args.repeat})")
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())