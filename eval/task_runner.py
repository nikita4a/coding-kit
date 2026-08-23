#!/usr/bin/env python3
"""eval/task_runner.py — quantitative agent benchmark on real coding tasks.

Each eval/tasks/<name>/ holds TASK.md (the brief) + verify.py (binary oracle).
The executor gets the brief on stdin with cwd=sandbox (a fresh copy of
repo-fixture); afterwards verify.py <sandbox> decides pass/fail. No LLM
judge — scoring is reproducible and model-agnostic.

Usage:
    python eval/task_runner.py --dry-run                     # validate layout
    python eval/task_runner.py --executor "claude -p"        # score all tasks
    python eval/task_runner.py --executor "..." --json auto  # + result doc

Exit 1 if any task fails (flake-gate compatible: rerun to confirm).
"""
import argparse
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "eval" / "tasks"
FIXTURE = TASKS / "repo-fixture"


def resolve_cmd(spec: str) -> list[str]:
    """CLI string -> argv list. No shell; .cmd/.bat run through cmd /c."""
    parts = shlex.split(spec, posix=(sys.platform != "win32"))
    exe = shutil.which(parts[0]) or parts[0]
    if sys.platform == "win32" and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe, *parts[1:]]
    return [exe or parts[0], *parts[1:]]


def discover() -> list[str]:
    return sorted(d.name for d in TASKS.iterdir()
                  if d.is_dir()
                  and (d / "TASK.md").is_file()
                  and (d / "verify.py").is_file())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--executor", help="model CLI reading the brief on stdin")
    ap.add_argument("--timeout", type=int, default=900,
                    help="per-task executor timeout seconds (default 900)")
    ap.add_argument("--json", default=None, metavar="PATH|auto",
                    help="write a JSON result doc: explicit path or 'auto' "
                         "for the shared timestamped store (eval/results/)")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate task layout only")
    args = ap.parse_args()

    names = discover()
    print(f"{len(names)} tasks discovered: {', '.join(names)}")
    if args.dry_run:
        broken = [n for n in names
                  if not (TASKS / n / "verify.py").is_file()]
        if broken:
            print(f"BROKEN: {broken}")
            return 1
        print("OK (dry-run)")
        return 0
    if not args.executor:
        ap.error("--executor required without --dry-run")

    cmd = resolve_cmd(args.executor)
    rows, failed = [], 0
    for name in names:
        with tempfile.TemporaryDirectory(prefix=f"kit-task-{name}-") as td:
            sandbox = Path(td) / "repo"
            shutil.copytree(FIXTURE, sandbox)
            brief = (TASKS / name / "TASK.md").read_text(encoding="utf-8")
            try:
                subprocess.run(cmd, input=brief, cwd=sandbox,
                               timeout=args.timeout, capture_output=True)
                ok = subprocess.run(
                    [sys.executable, str(TASKS / name / "verify.py"),
                     str(sandbox)], capture_output=True).returncode == 0
            except subprocess.TimeoutExpired:
                ok = False
        rows.append({"name": name, "verdict": "PASS" if ok else "FAIL"})
        failed += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'} {name}")

    print(f"\noverall: {len(rows) - failed}/{len(rows)} tasks PASS")
    if args.json:
        sys.path.insert(0, str(ROOT / "eval"))
        from results_io import save_result
        override = None if str(args.json) == "auto" else Path(args.json)
        save_result("tasks", args.executor,
                    {"rows": rows, "passed": len(rows) - failed,
                     "total": len(rows),
                     "pass_rate": round((len(rows) - failed) / len(rows), 3)},
                    path=override)
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
