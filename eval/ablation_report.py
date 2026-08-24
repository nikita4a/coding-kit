#!/usr/bin/env python3
"""eval/ablation_report.py — experimental inlined-prompt ablation rendering.

Renders 'ablate' kind runs from the shared JSON store into a raw
"Experimental inlined-prompt contribution" table. Pure rendering concern:
it receives the newest-per-model ablation runs plus duration/cost formatter
callables so it stays a thin, dependency-free helper (no results-store
access, no baseline logic).

Usage (via eval/trend.py):
    from ablation_report import render_ablation_section
    lines += render_ablation_section(ablate_runs, _duration_str, _reported_cost_str)
"""
import math


def _finite_ablation_number(value: object) -> bool:
    """True when `value` is a finite int/float and not a bool."""
    return (isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value))


def _delta_sort_key(value: object) -> tuple:
    """Type-safe sort key for an ablation delta.

    Valid numeric deltas order ascending (matching the original behaviour);
    malformed ones (string/bool/NaN/Inf/missing) sort after them so a mixed
    per_skill list never raises a cross-type comparison error.
    """
    if _finite_ablation_number(value):
        return (0, float(value))
    return (1, 0.0)


def _ablation_rate(value: object) -> str:
    """Render a pass-rate column, `-` when the value is not a finite number."""
    if not _finite_ablation_number(value):
        return "-"
    return str(value)


def _ablation_delta(value: object) -> str:
    """Render a delta column, `-` when the value is not a finite number."""
    if not _finite_ablation_number(value):
        return "-"
    return f"{value:+.3f}"


def render_ablation_section(ablate_runs: list[dict], duration_str: object,
                            reported_cost_str: object) -> list[str]:
    """Newest inlined-prompt contribution per model, rendered raw.

    `duration_str` and `reported_cost_str` are callables taking a run dict
    and returning the formatted duration / reported-cost column strings.
    """
    if not ablate_runs:
        return []
    newest: dict[str, dict] = {}
    for r in ablate_runs:
        if not isinstance(r, dict):
            continue
        model = str(r.get("model") or "unspecified")
        existing = newest.get(model)
        if existing is None or str(r.get("utc", "")) >= str(existing.get("utc", "")):
            newest[model] = r

    rows = []
    for model in sorted(newest):
        r = newest[model]
        repeat = r.get("repeat", 1)
        dur = duration_str(r)
        cost = reported_cost_str(r)
        raw_entries = r.get("per_skill", [])
        entries = [e for e in raw_entries if isinstance(e, dict)] \
            if isinstance(raw_entries, list) else []
        entries.sort(key=lambda e: _delta_sort_key(e.get("delta")))
        for e in entries:
            rows.append(
                f"| {model} | {e.get('skill', '?')} | "
                f"{_ablation_rate(e.get('pass_rate_with'))} | "
                f"{_ablation_rate(e.get('pass_rate_without'))} | "
                f"{_ablation_delta(e.get('delta'))} | "
                f"{e.get('scenarios_affected', 0)} | {repeat} | "
                f"{dur} | {cost} |")

    if not rows:
        return []
    return [
        "",
        "## Experimental inlined-prompt contribution",
        "",
        "Caveat: ambient global skills are uncontrolled and small samples are "
        "non-conclusive. Raw figures only.",
        "",
        "| model | skill | with | without | delta | n | repeat | duration | reported cost |",
        "|---|---|---|---|---|---|---|---|---|",
        *rows,
        "",
    ]
