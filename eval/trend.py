#!/usr/bin/env python3
"""eval/trend.py — pass-rate history + failure-driven harness proposals.

Reads the shared JSON store (eval/results_io.load_runs) and prints:
  1. a markdown table of the last runs per kind/model with scores;
  2. a Proposals section: every non-PASS in the NEWEST run of each kind,
     grouped by owning component — the semi-automatic half of the harness
     evolution loop (machine proposes, human merges, evals re-verify).

Usage:
    python eval/trend.py                 # report to stdout
    python eval/trend.py > TREND.md      # or redirect
"""
from results_io import load_runs

KIND_ORDER = {"trap": 0, "tasks": 1, "trigger": 2}


def _score(r: dict) -> str:
    if "passed" in r and "total" in r:
        return f"{r['passed']}/{r['total']}"
    if "fired" in r and "total" in r:
        return f"fired {r['fired']}/{r['total']}"
    return "?"


def _proposals(newest: dict[str, dict]) -> list[str]:
    out = []
    for kind in sorted(newest, key=lambda k: KIND_ORDER.get(k, 9)):
        r = newest[kind]
        for row in r.get("scenarios", []):
            if row.get("verdict") != "PASS":
                out.append(f"- [{row.get('skill', '?')}] trap `{row['name']}` "
                           f"FAILED on {r['model']} ({r['utc'][:16]}): tighten "
                           f"skill wording; re-verify: "
                           f"python eval/runner.py --scenario {row['name']} "
                           f"--executor ... --repeat 2")
        if "fired" in r and r["fired"] < r.get("total", 0):
            out.append(f"- [routing] trigger misses on {r['model']} "
                       f"({r['utc'][:16]}): {'; '.join(r.get('misses', []))}; "
                       f"re-verify: python eval/trigger_eval.py "
                       f"--queries eval/trigger_queries.json --executor ...")
        for row in r.get("rows", []):
            if row.get("verdict") != "PASS":
                out.append(f"- [{row['name']}] task FAILED on {r['model']} "
                           f"({r['utc'][:16]}): inspect sandbox behavior; "
                           f"re-verify: python eval/task_runner.py "
                           f"--executor ...")
    return out


def render() -> str:
    runs = load_runs()
    if not runs:
        return ("# Eval trends\n\nno results yet — run any eval with "
                "`--json auto`\n")
    lines = ["# Eval trends\n",
             "| kind | model | utc | score |",
             "|---|---|---|---|"]
    for r in runs[-20:]:
        lines.append(f"| {r['kind']} | {r['model']} | {r['utc'][:16]} "
                     f"| {_score(r)} |")
    newest: dict[str, dict] = {}
    for r in runs:
        newest[r["kind"]] = r          # last write wins = newest per kind
    lines += ["", "## Proposals", ""]
    props = _proposals(newest)
    lines += props or ["all-green: no open failures", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render())
