#!/usr/bin/env python3
"""eval/trigger_eval.py — skill trigger-rate measurement for coding-kit.

Aims at the "agent does not load the right skill on its own" failure class:
it measures whether a skill's *description* makes an agent load the skill
for the natural user phrasing, with no other mechanisms helping.

Method (ported as ideas from the agentskills.io methodology):
- queries file: JSON array of {"skill": slug, "should": true|false,
  "query": "natural user wording"}. Per skill: several should-trigger
  queries and several should-not near-misses (similar words, different
  task) — not random unrelated questions.
- each query runs N times (default 3); a query passes if the majority of
  runs answer in a way that shows the skill was loaded (the slug appears
  in the answer — the kit souls mandate "mark the skill name").
- per-skill summary: trigger rate (should-queries passed) and false rate
  (should-not queries passed). Thresholds: trigger >= 0.5 and false <= 0.3.
- anti-overfitting: do NOT paste words from failed queries into the
  description; find the real trigger gap and reword (see skills/learn).

The model backend plugs in exactly like eval/runner.py: `--executor CMD`
reads the prompt from stdin, prints the answer to stdout (e.g.
`gemini -p -`, `claude -p`). Without `--executor` the queries file is only
validated (dry-run). The executor spec is developer-owned config, never
user input; parsed with shlex, run WITHOUT shell=True.

Usage:
    python eval/trigger_eval.py --queries eval/trigger_queries.json        # validate
    python eval/trigger_eval.py --queries eval/trigger_queries.json        \\
        --executor "gemini -p -" --runs 3 --parallel 4 --out trig.jsonl
    python eval/trigger_eval.py --queries q.json --only yagni              # one skill
"""
import argparse
import json
import re
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent          # eval/
ROOT = HERE.parent                              # kit root
sys.path.insert(0, str(HERE))
from runner import resolve_cmd, run_prompt      # same executor contract

TRIGGER_RATE_MIN = 0.5
FALSE_RATE_MAX = 0.3
RUNS_DEFAULT = 3
TIMEOUT_DEFAULT = 300


def detect(slug: str, answer: str) -> bool:
    """True if the slug appears as a standalone token in the answer."""
    slug = re.escape(slug)
    return re.search(rf"(?<![a-z0-9_-]){slug}(?![a-z0-9_-])",
                     answer, re.IGNORECASE) is not None


def validate(queries: list[dict]) -> list[str]:
    """Schema + balance checks. Returns a list of problems (empty = ok)."""
    problems = []
    if not queries:
        problems.append("queries file is empty")
        return problems
    by_skill: dict[str, dict[str, int]] = {}
    for i, q in enumerate(queries):
        where = f"queries[{i}]"
        if not isinstance(q, dict):
            problems.append(f"{where}: not an object"); continue
        for key in ("skill", "should", "query"):
            if key not in q:
                problems.append(f"{where}: missing '{key}'")
        if not isinstance(q.get("query"), str) or not q["query"].strip():
            problems.append(f"{where}: query is not a non-empty string")
        if not isinstance(q.get("should"), bool):
            problems.append(f"{where}: 'should' must be true/false")
        if q.get("skill"):
            s = by_skill.setdefault(q["skill"], {"should": 0, "not": 0})
            if q.get("should"):
                s["should"] += 1
            else:
                s["not"] += 1
    for skill, counts in by_skill.items():
        if counts["should"] == 0:
            problems.append(f"skill '{skill}': no should-trigger queries")
        if counts["not"] == 0:
            problems.append(f"skill '{skill}': no should-not (near-miss) queries")
    pairs = [(q["skill"], q["query"]) for q in queries
             if q.get("skill") and q.get("query")]
    if len(set(pairs)) != len(pairs):
        problems.append("duplicate (skill, query) entries")
    for i, q in enumerate(queries):
        if q.get("should") is False and q.get("skill") \
                and q["skill"].lower() in q["query"].lower():
            problems.append(f"queries[{i}]: should-not query names its own "
                            f"skill ('{q['skill']}') — near-miss must not")
    return problems


# --- prompt construction ---

PRELUDE = (
    "You are an engineer agent with a skills directory available "
    "(Hermes-format SKILL.md skills). Load any skill that fits the user "
    "request. End your answer with a line: SKILLS LOADED: <comma-separated "
    "skill names you actually loaded, or 'none'>.\n\n"
)


def prompt_for(query: str) -> str:
    return PRELUDE + "User request: " + query + "\n"


def run_query(cmd: list[str], q: dict, runs: int,
              timeout: int = TIMEOUT_DEFAULT) -> tuple[str, bool]:
    """Runs one query `runs` times; majority vote decides triggered."""
    hits = 0
    for _ in range(runs):
        answer = run_prompt(cmd, prompt_for(q["query"]), timeout=timeout)
        if detect(q["skill"], answer):
            hits += 1
    return q["query"], hits * 2 > runs


def summarize(results: dict[str, list[tuple[str, bool, bool]]]) -> tuple[list[str], dict]:
    """Return (problem lines, per-skill stats)."""
    problems, stats = [], {}
    for skill, rows in results.items():
        should = [p for (_, s, p) in rows if s]
        nots = [p for (_, s, p) in rows if not s]
        tr = sum(should) / len(should)
        fr = sum(nots) / len(nots)
        stats[skill] = {"trigger": tr, "false": fr,
                        "should": len(should), "not": len(nots)}
        if tr < TRIGGER_RATE_MIN:
            problems.append(f"{skill}: trigger rate {tr:.2f} < {TRIGGER_RATE_MIN} "
                            f"(failed: {[q for (q, s, p) in rows if s and not p]})")
        if fr > FALSE_RATE_MAX:
            problems.append(f"{skill}: false rate {fr:.2f} > {FALSE_RATE_MAX} "
                            f"(false-triggered: {[q for (q, s, p) in rows if not s and p]})")
    return problems, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queries", required=True, help="JSON file with {skill, should, query}")
    ap.add_argument("--executor", help='CLI reading prompt from stdin, '
                     'printing answer to stdout (e.g. "gemini -p -")')
    ap.add_argument("--runs", type=int, default=RUNS_DEFAULT,
                    help=f"runs per query (default {RUNS_DEFAULT})")
    ap.add_argument("--parallel", type=int, default=1, help="parallel workers")
    ap.add_argument("--only", help="run a single skill (slug)")
    ap.add_argument("--timeout", type=int, default=TIMEOUT_DEFAULT,
                    help="per-call timeout seconds")
    ap.add_argument("--out", help="append results as JSONL")
    ap.add_argument("--json", default=None, metavar="PATH|auto",
                    help="write a JSON result doc: explicit path or 'auto' "
                         "for the shared timestamped store (eval/results/)")
    args = ap.parse_args()

    try:
        queries = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"queries file not found: {args.queries}"); return 2
    except json.JSONDecodeError as e:
        print(f"queries file is not valid JSON: {e}"); return 2
    problems = validate(queries)
    if problems:
        print("queries validation FAILED:")
        print("\n".join(f"  - {p}" for p in problems)); return 1
    print(f"queries OK: {len(queries)} queries "
          f"({len({q['skill'] for q in queries})} skills)")

    if not args.executor:
        print("dry-run: no --executor, queries validated only")
        if args.json:
            _emit_json(args, mode="dry-run", total=len(queries),
                       fired=0, misses=[])
        return 0
    cmd = resolve_cmd(args.executor)
    selected = [q for q in queries
                if not args.only or q["skill"] == args.only]
    if args.only and not selected:
        print(f"--only {args.only}: no such skill in queries"); return 2

    results: dict[str, list[tuple[str, bool, bool]]] = {}
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futs = {pool.submit(run_query, cmd, q, args.runs,
                            args.timeout): q for q in selected}
        for fut in as_completed(futs):
            q = futs[fut]
            query_text, passed = fut.result()
            tag = "PASS" if passed == q["should"] else "FAIL"
            print(f"[{tag}] {q['skill']:30s} should={str(q['should']):5s} "
                  f"'{query_text[:60]}'")
            results.setdefault(q["skill"], []).append((query_text, q["should"], passed))
            if args.out:
                with open(args.out, "a", encoding="utf-8") as f:
                    f.write(json.dumps(
                        {"skill": q["skill"], "should": q["should"],
                         "query": query_text, "result": tag}, ensure_ascii=False) + "\n")

    problems, stats = summarize(results)
    print("\nper-skill summary (trigger = should-passed rate, false = should-not-passed):")
    for skill, s in sorted(stats.items()):
        print(f"  {skill:30s} trigger {s['trigger']:.2f}  false {s['false']:.2f}  "
              f"({s['should']}+{s['not']} queries)")
    if problems:
        print("\nBELOW THRESHOLD:")
        print("\n".join(f"  - {p}" for p in problems))
        _emit_json(args, mode="live", total=len(selected),
                   fired=sum(1 for rows in results.values()
                             for (_, s, p) in rows if p == s),
                   misses=[p for p in problems])
        return 1
    print("\nall measured skills above threshold")
    _emit_json(args, mode="live", total=len(selected),
               fired=sum(1 for rows in results.values()
                         for (_, s, p) in rows if p == s),
               misses=[])
    return 0


def _emit_json(args, mode: str, total: int, fired: int,
               misses: list[str]) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from results_io import save_result
    override = None if str(args.json) == "auto" else Path(args.json)
    save_result("trigger", args.executor or "dry-run",
                {"mode": mode, "fired": fired, "total": total,
                 "misses": misses}, path=override)


if __name__ == "__main__":
    sys.exit(main())