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
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ROOT / "eval" / "scenarios"

_EXECUTOR_ENV_KEYS = (
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA",
    "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
    "PROGRAMW6432", "TEMP", "TMP", "TMPDIR", "USER", "USERNAME",
    "SHELL", "LANG", "LC_ALL", "PYTHONIOENCODING", "PYTHONUTF8",
    "TERM", "COLORTERM", "NO_COLOR",
)


def executor_env() -> dict[str, str]:
    """Minimal runtime environment; model subprocesses never inherit secrets."""
    return {key: os.environ[key] for key in _EXECUTOR_ENV_KEYS
            if key in os.environ}

sys.path.insert(0, str(ROOT / "eval"))
try:
    from results_io import save_result
except ImportError:
    from eval.results_io import save_result


def _unquote(s: str) -> str:
    if len(s) >= 2 and ((s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'"))):
        return s[1:-1]
    return s


def resolve_cmd(spec: str) -> list[str]:
    """CLI string -> argv list. No shell; .cmd/.bat run through cmd /c."""
    if not spec or not spec.strip():
        return []
    is_win = sys.platform == "win32"
    parts = shlex.split(spec, posix=not is_win)
    if not parts:
        return []
    if is_win:
        parts = [_unquote(p) for p in parts]
    exe = shutil.which(parts[0]) or parts[0]
    if is_win and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe, *parts[1:]]
    return [exe, *parts[1:]]


def run_prompt(cmd: list[str], prompt: str, timeout: int = 600) -> str:
    r = subprocess.run(
        cmd, input=prompt, capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace", env=executor_env(),
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


def judge_one(judge_cmd: list[str], expect: str, answer: str, timeout: int = 600) -> str:
    prompt = (
        f"The scenario expects the following behavior:\nEXPECT: {expect}\n\n"
        f"Agent's answer:\n{answer}\n\n"
        f"Does the agent's answer match the expectation? One line: "
        f"PASS or FAIL, then one line of reasoning."
    )
    return run_prompt(judge_cmd, prompt, timeout=timeout)


def run_scenarios(
    executor: list[str] | None,
    judge: list[str] | None,
    scenario_files: list[Path],
    repeat: int = 1,
    json_out: str | Path | None = None,
    model: str | None = None,
    executor_spec: str | None = None,
    timeout: int = 600,
) -> int:
    fails = 0
    rows = []
    repeat = max(1, repeat)

    for f in scenario_files:
        sc = parse(f.read_text(encoding="utf-8"))
        ok = all(k in sc for k in ("name", "skill", "trap", "expect", "body"))
        name = sc.get("name", f.stem)
        skill = sc.get("skill", "?")
        print(f"{'OK ' if ok else 'BAD'} {f.name} [{skill}] "
              f"trap: {sc.get('trap', '?')[:60]}")
        if not ok:
            fails += 1
            rows.append({
                "name": name,
                "skill": skill,
                "verdict": "FAIL",
                "attempts": [],
            })
            continue

        if not executor:
            print(f"     (dry-run: body {len(sc['body'])} chars, "
                  f"expect {sc['expect'][:50]}...)")
            rows.append({
                "name": name,
                "skill": skill,
                "verdict": "PASS",
                "attempts": [],
            })
            continue

        attempts = []
        outcomes = []
        judge_cmd = judge if judge is not None else executor

        for i in range(repeat):
            t0 = time.perf_counter()
            answer = None
            try:
                answer = run_prompt(executor, sc["body"], timeout=timeout)
            except Exception as e:
                duration_s = round(time.perf_counter() - t0, 4)
                print(f"     EXECUTOR FAIL: {e}")
                att = {
                    "verdict": "FAIL",
                    "duration_s": duration_s,
                    "error": f"executor {type(e).__name__}: {e}",
                }
                out = getattr(e, "stderr", None) or getattr(e, "stdout", None)
                if out:
                    if isinstance(out, bytes):
                        out = out.decode("utf-8", errors="replace")
                    att["trace_tail"] = str(out).strip()[-500:]
                attempts.append(att)
                outcomes.append(f"attempt {i+1}: EXECUTOR FAIL: {e}")
                continue

            try:
                verdict_text = judge_one(judge_cmd, sc["expect"], answer, timeout=timeout)
            except Exception as e:
                duration_s = round(time.perf_counter() - t0, 4)
                print(f"     JUDGE FAIL: {e}")
                att = {
                    "verdict": "FAIL",
                    "duration_s": duration_s,
                    "error": f"judge {type(e).__name__}: {e}",
                }
                if answer:
                    att["trace_tail"] = answer[-500:]
                attempts.append(att)
                outcomes.append(f"attempt {i+1}: JUDGE FAIL: {e}")
                continue

            duration_s = round(time.perf_counter() - t0, 4)
            passed = verdict_text.strip().upper().startswith("PASS")
            if passed:
                attempts.append({
                    "verdict": "PASS",
                    "duration_s": duration_s,
                })
            else:
                err_line = verdict_text.strip().splitlines()[0] if verdict_text.strip() else "judge returned empty verdict"
                att = {
                    "verdict": "FAIL",
                    "duration_s": duration_s,
                    "error": err_line,
                }
                if answer:
                    att["trace_tail"] = answer[-500:]
                attempts.append(att)
            outcomes.append(f"attempt {i+1}: {verdict_text[:160]}")

        print("\n     " + "\n     ".join(outcomes)
              if outcomes else "     (no runs)")

        scenario_passed = (
            len(attempts) == repeat
            and all(a.get("verdict") == "PASS" for a in attempts)
        )
        if not scenario_passed:
            fails += 1
            final_verdict = "FAIL"
        else:
            final_verdict = "PASS"

        rows.append({
            "name": name,
            "skill": skill,
            "verdict": final_verdict,
            "attempts": attempts,
        })

    print(f"\noverall: {'ALL GREEN' if not fails else f'{fails} non-PASS'}"
          f" ({len(scenario_files)} scenarios x {repeat})")

    if json_out:
        override = None if str(json_out) == "auto" else Path(json_out)
        payload = {
            "scenarios": rows,
            "passed": sum(1 for r in rows if r["verdict"] == "PASS"),
            "total": len(rows),
        }
        if not executor:
            payload["mode"] = "dry-run"
        save_result(
            "trap",
            model or "unspecified",
            payload,
            path=override,
            executor_spec=executor_spec,
        )
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--executor", help="model CLI (prompt on stdin)")
    ap.add_argument("--model", default=None,
                    help="model identifier (e.g. gpt-4o, claude-3-5-sonnet); "
                         "defaults to 'unspecified' if omitted")
    ap.add_argument("--judge", default=None,
                    help="judge CLI (default = --executor)")
    ap.add_argument("--scenario", help="single scenario name (no .md)")
    ap.add_argument("--repeat", type=int, default=1,
                    help="flake gate: scenario must PASS N times in a row")
    ap.add_argument("--timeout", type=int, default=600,
                    help="per-attempt timeout in seconds (default 600)")
    ap.add_argument("--json", default=None, metavar="PATH|auto",
                    help="write a JSON result doc: explicit path or 'auto' "
                         "for the shared timestamped store (eval/results/)")
    args = ap.parse_args()

    executor = resolve_cmd(args.executor) if args.executor else None
    judge = resolve_cmd(args.judge) if args.judge else executor

    files = sorted(SCENARIOS.glob("*.md"))
    if args.scenario:
        files = [SCENARIOS / f"{args.scenario}.md"]
    if not files:
        print("no scenarios found")
        return 1

    return run_scenarios(
        executor=executor,
        judge=judge,
        scenario_files=files,
        repeat=args.repeat,
        json_out=args.json,
        model=args.model,
        executor_spec=args.executor,
        timeout=args.timeout,
    )
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())