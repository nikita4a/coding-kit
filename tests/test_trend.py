import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

import results_io
import trend
import ablation_report


def test_render_empty_store(tmp_path):
    res_dir = tmp_path / "results"
    res_dir.mkdir(parents=True)
    out = trend.render(results_dir=res_dir)
    assert "# Eval trends" in out
    assert "no results yet" in out


def test_trend_groups_by_kind_and_model_without_hiding(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    # Older run for m1
    results_io.save_result("trap", "gpt-4o", {"passed": 16, "total": 18, "scenarios": []}, results_dir=res_dir)
    # Newer run for m1
    results_io.save_result("trap", "gpt-4o", {"passed": 18, "total": 18, "scenarios": []}, results_dir=res_dir)
    # Run for m2
    results_io.save_result("trap", "claude-3-7", {"passed": 17, "total": 18, "scenarios": []}, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| kind | model | utc | score | baseline | delta | status | duration | reported cost |" in out
    assert "| trap | gpt-4o |" in out
    assert "18/18" in out
    # Stale run 16/18 should not appear in the table
    assert "16/18" not in out
    assert "| trap | claude-3-7 |" in out
    assert "17/18" in out


def test_baseline_bands_and_boundaries(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    # Baseline is 90.0% (0.90) for all models
    (base_dir / "trap.json").write_text(
        json.dumps({
            "m_ok_plus": 0.90,
            "m_ok_zero": 0.90,
            "m_ok_exact_minus3": 0.90,
            "m_warn_minus301": 0.90,
            "m_warn_minus5": 0.90,
            "m_warn_minus799": 0.90,
            "m_crit_exact_minus8": 0.90,
            "m_crit_minus10": 0.90,
        }),
        encoding="utf-8"
    )

    # delta = +5.0pp -> OK
    results_io.save_result("trap", "m_ok_plus", {"passed": 95, "total": 100, "scenarios": []}, results_dir=res_dir)
    # delta = +0.0pp -> OK
    results_io.save_result("trap", "m_ok_zero", {"passed": 90, "total": 100, "scenarios": []}, results_dir=res_dir)
    # delta = -3.0pp -> OK (exact -3 boundary)
    results_io.save_result("trap", "m_ok_exact_minus3", {"passed": 87, "total": 100, "scenarios": []}, results_dir=res_dir)
    # delta = -3.01pp -> WARN
    results_io.save_result("trap", "m_warn_minus301", {"passed": 8699, "total": 10000, "scenarios": []}, results_dir=res_dir)
    # delta = -5.0pp -> WARN
    results_io.save_result("trap", "m_warn_minus5", {"passed": 85, "total": 100, "scenarios": []}, results_dir=res_dir)
    # delta = -7.99pp -> WARN
    results_io.save_result("trap", "m_warn_minus799", {"passed": 8201, "total": 10000, "scenarios": []}, results_dir=res_dir)
    # delta = -8.0pp -> CRITICAL (exact -8 boundary)
    results_io.save_result("trap", "m_crit_exact_minus8", {"passed": 82, "total": 100, "scenarios": []}, results_dir=res_dir)
    # delta = -10.0pp -> CRITICAL
    results_io.save_result("trap", "m_crit_minus10", {"passed": 80, "total": 100, "scenarios": []}, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)

    for line in out.splitlines():
        if "| trap | m_ok_plus |" in line:
            assert "+5.0pp | OK |" in line
        elif "| trap | m_ok_zero |" in line:
            assert "+0.0pp | OK |" in line
        elif "| trap | m_ok_exact_minus3 |" in line:
            assert "-3.0pp | OK |" in line
        elif "| trap | m_warn_minus301 |" in line:
            assert "-3.0pp | WARN |" in line or "-3.01" in line
        elif "| trap | m_warn_minus5 |" in line:
            assert "-5.0pp | WARN |" in line
        elif "| trap | m_warn_minus799 |" in line:
            assert "-8.0pp | WARN |" in line or "-7.99" in line
        elif "| trap | m_crit_exact_minus8 |" in line:
            assert "-8.0pp | CRITICAL |" in line
        elif "| trap | m_crit_minus10 |" in line:
            assert "-10.0pp | CRITICAL |" in line


def test_missing_and_malformed_baseline_tolerance(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    results_io.save_result("trap", "m1", {"passed": 18, "total": 18, "scenarios": []}, results_dir=res_dir)

    # 1. Missing baseline directory / file
    out1 = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| trap | m1 |" in out1
    assert "| - | - | - |" in out1

    # 2. Malformed JSON syntax in baseline file
    (base_dir / "trap.json").write_text("{ corrupt json syntax", encoding="utf-8")
    out2 = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| trap | m1 |" in out2
    assert "| - | - | - |" in out2

    # 3. Non-dict JSON in baseline file
    (base_dir / "trap.json").write_text("[1, 2, 3]", encoding="utf-8")
    out3 = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| trap | m1 |" in out3
    assert "| - | - | - |" in out3

    # 4. Non-numeric entry for model
    (base_dir / "trap.json").write_text(json.dumps({"m1": "invalid"}), encoding="utf-8")
    out4 = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| trap | m1 |" in out4
    assert "| - | - | - |" in out4


def test_evidence_packets_all_three_kinds(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"

    # Trap failure
    results_io.save_result("trap", "m1", {
        "passed": 17, "total": 18,
        "scenarios": [{
            "name": "scope-creep",
            "skill": "yagni",
            "verdict": "FAIL",
            "error": "judge mismatch: extra files created",
            "trace_tail": "trace: wrote foo.py and bar.py",
        }]
    }, results_dir=res_dir)

    # Tasks failure
    results_io.save_result("tasks", "m1", {
        "passed": 2, "total": 3,
        "rows": [{
            "name": "002-add-validation",
            "verdict": "FAIL",
            "error_class": "test_timeout",
            "trace_tail": "subprocess timed out after 900s",
        }]
    }, results_dir=res_dir)

    # Trigger failure
    results_io.save_result("trigger", "m1", {
        "fired": 79, "total": 80,
        "rows": [{
            "query": "how do I add validation",
            "skill": "yagni",
            "expected": True,
            "fired": False,
            "verdict": "FAIL",
            "error": "skill did not fire",
            "trace_tail": "loaded skills: none",
        }]
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "## Failure Evidence Packets" in out

    # Trap packet
    assert "- [trap] target: `scope-creep (skill: yagni)` | model: `m1`" in out
    assert "error: judge mismatch: extra files created" in out
    assert "trace_tail: trace: wrote foo.py and bar.py" in out
    assert "re-verify: python eval/runner.py --scenario scope-creep --executor ... --repeat 2" in out

    # Tasks packet
    assert "- [tasks] target: `002-add-validation` | model: `m1`" in out
    assert "error: test_timeout" in out
    assert "trace_tail: subprocess timed out after 900s" in out
    assert "re-verify: python eval/task_runner.py --executor ..." in out

    # Trigger packet
    assert "- [trigger] target: `how do I add validation (skill: yagni)` | model: `m1`" in out
    assert "error: skill did not fire" in out
    assert "trace_tail: loaded skills: none" in out
    assert "re-verify: python eval/trigger_eval.py --queries eval/trigger_queries.json --executor ..." in out


def test_evidence_packets_exclude_fixed_failures(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"

    # Run 1 fails scope-creep
    results_io.save_result("trap", "m1", {
        "passed": 17, "total": 18,
        "scenarios": [{
            "name": "scope-creep",
            "skill": "yagni",
            "verdict": "FAIL",
            "error": "judge mismatch",
        }]
    }, results_dir=res_dir)

    # Run 2 passes all
    results_io.save_result("trap", "m1", {
        "passed": 18, "total": 18,
        "scenarios": [{
            "name": "scope-creep",
            "skill": "yagni",
            "verdict": "PASS",
        }]
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "scope-creep" not in out.split("## Failure Evidence Packets")[1]
    assert "all-green: no open failures" in out


def test_no_proposal_or_edit_wording(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"

    results_io.save_result("trap", "m1", {
        "passed": 17, "total": 18,
        "scenarios": [{"name": "scope-creep", "skill": "yagni", "verdict": "FAIL", "error": "err"}]
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)

    # Old proposal keywords must NOT be present
    assert "## Proposals" not in out
    assert "tighten skill wording" not in out
    assert "inspect sandbox behavior" not in out
    assert "Proposals" not in out


def test_update_baselines_last_n_averaging(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"

    # 5 runs: 1.0, 0.8, 0.6, 0.9, 0.7
    rates = [(10, 10), (8, 10), (6, 10), (9, 10), (7, 10)]
    for passed, total in rates:
        results_io.save_result("trap", "m1", {"passed": passed, "total": total}, results_dir=res_dir)

    # Update baselines with n=3 (averages 0.6, 0.9, 0.7 -> 2.2 / 3 = 0.7333)
    trend.update_baselines(results_dir=res_dir, baselines_dir=base_dir, n=3)

    trap_baseline_file = base_dir / "trap.json"
    assert trap_baseline_file.is_file()
    data = json.loads(trap_baseline_file.read_text(encoding="utf-8"))
    assert data["m1"] == 0.7333

    # Check deterministic trailing LF
    raw = trap_baseline_file.read_bytes()
    assert raw.endswith(b"\n")


def test_cli_always_exits_zero(tmp_path, monkeypatch):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    # Baseline 1.0 (100%)
    (base_dir / "trap.json").write_text(json.dumps({"m1": 1.0}), encoding="utf-8")
    # Result 0.8 (80%) -> delta -20.0pp -> CRITICAL
    results_io.save_result("trap", "m1", {"passed": 8, "total": 10}, results_dir=res_dir)

    # Normal render with CRITICAL status must exit 0 (warn-only)
    rc1 = trend.main(["--results-dir", str(res_dir), "--baselines-dir", str(base_dir)])
    assert rc1 == 0

    # With update baselines
    rc2 = trend.main(["--update-baselines", "--results-dir", str(res_dir), "--baselines-dir", str(base_dir)])
    assert rc2 == 0


def test_rate_and_score_definitions_all_kinds(tmp_path):
    # 1. Trap with top-level and scenario fallback
    doc_trap_top = {"kind": "trap", "passed": 15, "total": 20}
    assert trend._rate(doc_trap_top) == 0.75
    assert trend._score(doc_trap_top) == "15/20"

    doc_trap_scenarios = {"kind": "trap", "scenarios": [{"verdict": "PASS"}, {"verdict": "FAIL"}]}
    assert trend._rate(doc_trap_scenarios) == 0.5
    assert trend._score(doc_trap_scenarios) == "1/2"

    # 2. Tasks with top-level and row fallback
    doc_tasks_top = {"kind": "tasks", "passed": 2, "total": 3}
    assert trend._rate(doc_tasks_top) == pytest.approx(2 / 3)
    assert trend._score(doc_tasks_top) == "2/3"

    doc_tasks_rows = {"kind": "tasks", "rows": [{"verdict": "PASS"}, {"verdict": "PASS"}, {"verdict": "FAIL"}]}
    assert trend._rate(doc_tasks_rows) == pytest.approx(2 / 3)
    assert trend._score(doc_tasks_rows) == "2/3"

    # 3. Trigger with top-level passed, legacy top-level fired, and legacy row fallback
    doc_trig_top = {"kind": "trigger", "passed": 75, "fired": 50, "total": 100}
    assert trend._rate(doc_trig_top) == 0.75
    assert trend._score(doc_trig_top) == "75/100"

    doc_trig_legacy_top = {"kind": "trigger", "fired": 75, "total": 100}
    assert trend._rate(doc_trig_legacy_top) == 0.75
    assert trend._score(doc_trig_legacy_top) == "fired 75/100"

    doc_trig_rows = {"kind": "trigger", "rows": [{"fired": True}, {"fired": False}, {"verdict": "PASS"}]}
    assert trend._rate(doc_trig_rows) == pytest.approx(1 / 3)
    assert trend._score(doc_trig_rows) == "fired 1/3"


def test_evidence_packets_from_attempts(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"

    # Error and trace_tail only inside attempts array
    results_io.save_result("trap", "m1", {
        "passed": 0, "total": 1,
        "scenarios": [{
            "name": "scenario-from-att",
            "skill": "yagni",
            "verdict": "FAIL",
            "attempts": [
                {"verdict": "FAIL", "error": "attempt_1_error", "trace_tail": "tail_attempt_1"}
            ]
        }]
    }, results_dir=res_dir)

    results_io.save_result("tasks", "m1", {
        "passed": 0, "total": 1,
        "rows": [{
            "name": "task-from-att",
            "verdict": "FAIL",
            "attempts": [
                {"verdict": "FAIL", "error_class": "syntax_error", "trace_tail": "trace_task_att"}
            ]
        }]
    }, results_dir=res_dir)

    results_io.save_result("trigger", "m1", {
        "fired": 0, "total": 1,
        "rows": [{
            "query": "trigger-from-att",
            "skill": "superpowers",
            "verdict": "FAIL",
            "attempts": [
                {"verdict": "FAIL", "error": "trigger_att_error", "trace_tail": "trace_trigger_att"}
            ]
        }]
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "error: attempt_1_error" in out
    assert "trace_tail: tail_attempt_1" in out
    assert "error: syntax_error" in out
    assert "trace_tail: trace_task_att" in out
    assert "error: trigger_att_error" in out
    assert "trace_tail: trace_trigger_att" in out


def test_evidence_packets_trigger_summary_misses(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"

    # Trigger with misses list instead of row objects
    results_io.save_result("trigger", "m1", {
        "fired": 2, "total": 3,
        "misses": ["yagni should-query missed"]
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "- [trigger] target: `yagni should-query missed` | model: `m1`" in out
    assert "error: trigger miss" in out
    assert "re-verify: python eval/trigger_eval.py --queries eval/trigger_queries.json --executor ..." in out


def test_malformed_substructures_tolerance(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"

    # Scenarios/rows contain non-dict or weird items
    results_io.save_result("trap", "m1", {
        "scenarios": [None, "invalid_str", 123, {"name": "ok_s", "verdict": "PASS"}]
    }, results_dir=res_dir)
    results_io.save_result("tasks", "m1", {
        "rows": [None, 456, {"name": "ok_t", "verdict": "PASS"}]
    }, results_dir=res_dir)
    results_io.save_result("trigger", "m1", {
        "rows": [None, {"verdict": "PASS"}]
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "all-green: no open failures" in out
    assert "| trap | m1 |" in out
    assert "| tasks | m1 |" in out
    assert "| trigger | m1 |" in out


def test_dry_run_records_excluded_from_render_and_baselines(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    # 1. Pure dry-run records
    results_io.save_result("trigger", "m1", {
        "mode": "dry-run",
        "passed": 0,
        "fired": 0,
        "total": 80,
        "misses": [],
        "rows": [],
    }, results_dir=res_dir)

    results_io.save_result("tasks", "m1", {
        "passed": 0,
        "total": 3,
        "rows": [{"name": "task-1", "verdict": "DRY_RUN", "attempts": []}],
    }, results_dir=res_dir)

    # Render with only dry-runs should report no results yet
    out_empty = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "no results yet" in out_empty

    # Update baselines with only dry-runs should produce no baseline files
    trend.update_baselines(results_dir=res_dir, baselines_dir=base_dir, n=5)
    assert not (base_dir / "trigger.json").exists()
    assert not (base_dir / "tasks.json").exists()

    # 2. Add a live record alongside dry-run records
    results_io.save_result("trigger", "m1", {
        "mode": "live",
        "passed": 80,
        "fired": 40,
        "total": 80,
        "misses": [],
        "rows": [],
    }, results_dir=res_dir)

    out_live = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| trigger | m1 |" in out_live
    assert "80/80" in out_live
    # Tasks dry-run must still be excluded
    assert "| tasks |" not in out_live

    # Update baselines should only use the live trigger run (rate = 1.0)
    trend.update_baselines(results_dir=res_dir, baselines_dir=base_dir, n=5)
    assert (base_dir / "trigger.json").exists()
    data = json.loads((base_dir / "trigger.json").read_text(encoding="utf-8"))
    assert data["m1"] == 1.0
    assert not (base_dir / "tasks.json").exists()


def test_explicit_mode_and_legacy_zero_result_dry_run_filtering(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    # 1. Explicit mode="dry-run" with non-DRY_RUN row verdict
    results_io.save_result("tasks", "m_dry_explicit", {
        "mode": "dry-run",
        "passed": 3,
        "total": 3,
        "rows": [{"name": "task-1", "verdict": "PASS", "attempts": []}],
    }, results_dir=res_dir)

    # 2. Legacy run without mode and renamed/non-DRY_RUN row verdict with empty attempts
    results_io.save_result("tasks", "m_legacy_renamed_dry", {
        "passed": 0,
        "total": 1,
        "rows": [{"name": "task-renamed", "verdict": "SKIPPED", "attempts": []}],
    }, results_dir=res_dir)

    # 3. Legacy zero-result artifact without mode
    results_io.save_result("tasks", "m_legacy_zero", {
        "passed": 0,
        "total": 0,
        "rows": [],
    }, results_dir=res_dir)

    # 4. Explicit mode="live" with DRY_RUN text in row (explicit mode discriminator takes precedence)
    results_io.save_result("tasks", "m_live_explicit", {
        "mode": "live",
        "passed": 1,
        "total": 1,
        "rows": [{"name": "task-1", "verdict": "PASS", "attempts": [{"verdict": "PASS", "phase": "verifier"}]}],
    }, results_dir=res_dir)

    # 5. Legacy live run without mode but with real attempts
    results_io.save_result("trap", "m_legacy_live", {
        "passed": 18,
        "total": 18,
        "scenarios": [{"name": "sc1", "verdict": "PASS", "attempts": [{"verdict": "PASS", "phase": "verdict"}]}],
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "m_dry_explicit" not in out
    assert "m_legacy_renamed_dry" not in out
    assert "m_legacy_zero" not in out
    assert "m_live_explicit" in out
    assert "m_legacy_live" in out

    trend.update_baselines(results_dir=res_dir, baselines_dir=base_dir, n=5)
    tasks_data = json.loads((base_dir / "tasks.json").read_text(encoding="utf-8"))
    assert "m_dry_explicit" not in tasks_data
    assert "m_legacy_renamed_dry" not in tasks_data
    assert "m_legacy_zero" not in tasks_data
    assert tasks_data["m_live_explicit"] == 1.0

    trap_data = json.loads((base_dir / "trap.json").read_text(encoding="utf-8"))
    assert trap_data["m_legacy_live"] == 1.0


def test_trigger_perfect_mixed_corpus_all_green(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    # 4 queries: 2 should-trigger (fired=True), 2 should-not (fired=False) -> passed=4, fired=2, total=4
    results_io.save_result("trigger", "gemini-2.5-pro", {
        "mode": "live",
        "passed": 4,
        "fired": 2,
        "total": 4,
        "misses": [],
        "rows": [
            {"query": "q1", "skill": "yagni", "expected": True, "fired": True, "verdict": "PASS"},
            {"query": "q2", "skill": "yagni", "expected": True, "fired": True, "verdict": "PASS"},
            {"query": "q3", "skill": "yagni", "expected": False, "fired": False, "verdict": "PASS"},
            {"query": "q4", "skill": "yagni", "expected": False, "fired": False, "verdict": "PASS"},
        ],
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| trigger | gemini-2.5-pro |" in out
    assert "4/4" in out
    # Must NOT flag fired 2/4 as failure packet
    assert "all-green: no open failures" in out
    assert "trigger misses" not in out


def test_trigger_never_fire_model_evidence_and_score(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    # 4 queries: 2 should-trigger (fired=False -> FAIL), 2 should-not (fired=False -> PASS)
    # Result: passed=2, fired=0, total=4
    results_io.save_result("trigger", "never-fire-model", {
        "mode": "live",
        "passed": 2,
        "fired": 0,
        "total": 4,
        "misses": ["yagni: trigger rate 0.00 < 0.50"],
        "rows": [
            {"query": "add cache?", "skill": "yagni", "expected": True, "fired": False, "verdict": "FAIL", "error": "skill did not fire"},
            {"query": "speculative generalization", "skill": "yagni", "expected": True, "fired": False, "verdict": "FAIL", "error": "skill did not fire"},
            {"query": "two plus two", "skill": "yagni", "expected": False, "fired": False, "verdict": "PASS"},
            {"query": "fibonacci sequence", "skill": "yagni", "expected": False, "fired": False, "verdict": "PASS"},
        ],
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| trigger | never-fire-model |" in out
    assert "2/4" in out
    assert "## Failure Evidence Packets" in out
    assert "- [trigger] target: `add cache? (skill: yagni)` | model: `never-fire-model`" in out
    assert "- [trigger] target: `speculative generalization (skill: yagni)` | model: `never-fire-model`" in out
    # Passing should-not queries must not be in failure packets
    assert "two plus two" not in out
    assert "fibonacci sequence" not in out


def test_trigger_summary_fallback_with_passed_less_than_total(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    # Trigger with passed < total but without rows or misses list
    results_io.save_result("trigger", "m1", {
        "passed": 70,
        "fired": 40,
        "total": 80,
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "- [trigger] target: `trigger misses` | model: `m1`" in out
    assert "error: passed 70/80" in out


def test_render_duration_and_reported_cost_columns(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    results_io.save_result("trap", "gpt-4o", {
        "passed": 18,
        "total": 18,
        "scenarios": [],
        "duration_s_mean": 12.345,
        "reported_usage": {"tokens_total": 1000, "cost_usd": 0.42},
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| duration | reported cost |" in out
    assert "12.345s" in out
    assert "$0.42" in out


def test_render_old_docs_dash_new_columns(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    results_io.save_result("trap", "gpt-4o", {
        "passed": 18,
        "total": 18,
        "scenarios": [],
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    row = [ln for ln in out.splitlines() if ln.startswith("| trap | gpt-4o |")]
    assert row, "expected a table row for gpt-4o"
    assert row[0].endswith("| - | - |")


def test_ablate_excluded_from_main_table(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    results_io.save_result("trap", "m1", {"passed": 18, "total": 18, "scenarios": []}, results_dir=res_dir)
    results_io.save_result("ablate", "m1", {
        "repeat": 2,
        "metric": "inlined-prompt contribution",
        "experimental": True,
        "ambient_skills_controlled": False,
        "passed": 1, "total": 1,
        "per_skill": [],
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "| ablate |" not in out
    assert "| trap | m1 |" in out


def test_experimental_ablation_section_raw_only(tmp_path):
    res_dir = tmp_path / "results"
    base_dir = tmp_path / "baselines"
    base_dir.mkdir(parents=True)

    results_io.save_result("ablate", "m1", {
        "repeat": 3,
        "metric": "inlined-prompt contribution",
        "experimental": True,
        "ambient_skills_controlled": False,
        "duration_s_total": 40.0,
        "duration_s_mean": 10.0,
        "reported_usage": {"tokens_total": 500, "cost_usd": 0.25},
        "per_skill": [
            {"skill": "yagni", "pass_rate_with": 0.8, "pass_rate_without": 0.2,
             "delta": 0.6, "scenarios_affected": 5},
        ],
    }, results_dir=res_dir)

    out = trend.render(results_dir=res_dir, baselines_dir=base_dir)
    assert "## Experimental inlined-prompt contribution" in out
    assert "uncontrolled" in out
    assert "non-conclusive" in out
    assert "yagni" in out
    assert "10.000s" in out
    assert "$0.25" in out
    # raw only, no candidate/deletion/causal wording
    lowered = out.lower()
    assert "candidate" not in lowered
    assert "delete" not in lowered
    assert "remove" not in lowered
    assert "causal" not in lowered


def test_ablation_section_malformed_per_skill_never_crashes():
    runs = [{
        "model": "m1",
        "utc": "2026-08-25T00:00:00Z",
        "repeat": 2,
        "duration_s_mean": 10.0,
        "reported_usage": {"cost_usd": 0.25},
        "per_skill": [
            {"skill": "mixed-neg", "pass_rate_with": 0.8,
             "pass_rate_without": 0.5, "delta": -0.25,
             "scenarios_affected": 1},
            {"skill": "str-delta", "pass_rate_with": "0.8",
             "pass_rate_without": "0.2", "delta": "0.6",
             "scenarios_affected": 2},
            {"skill": "nan-num", "pass_rate_with": float("nan"),
             "pass_rate_without": float("inf"), "delta": float("nan"),
             "scenarios_affected": 3},
            {"skill": "bool-num", "pass_rate_with": True,
             "pass_rate_without": False, "delta": True,
             "scenarios_affected": 4},
            {"skill": "good", "pass_rate_with": 0.8,
             "pass_rate_without": 0.2, "delta": 0.6,
             "scenarios_affected": 5},
        ],
    }]

    # must not raise on a mixed string/nonfinite/bool per_skill list
    lines = ablation_report.render_ablation_section(runs, trend._duration_str, trend._reported_cost_str)
    body = "\n".join(lines)

    assert "## Experimental inlined-prompt contribution" in body
    assert "uncontrolled" in body
    assert "non-conclusive" in body
    assert "causal" not in body.lower()

    # exact valid numeric output preserved (rate repr + signed delta + n/repeat)
    assert "| m1 | good | 0.8 | 0.2 | +0.600 | 5 | 2 | 10.000s | $0.25 |" in body
    assert "| m1 | mixed-neg | 0.8 | 0.5 | -0.250 | 1 | 2 | 10.000s | $0.25 |" in body

    # invalid numeric fields render '-' (string / NaN/Inf / bool)
    assert "| m1 | str-delta | - | - | - | 2 | 2 | 10.000s | $0.25 |" in body
    assert "| m1 | nan-num | - | - | - | 3 | 2 | 10.000s | $0.25 |" in body
    assert "| m1 | bool-num | - | - | - | 4 | 2 | 10.000s | $0.25 |" in body

    # type-safe ordering: valid numeric deltas ascending, malformed after
    assert body.index("| m1 | mixed-neg |") < body.index("| m1 | good |")
    assert body.index("| m1 | good |") < body.index("| m1 | str-delta |")


def test_duration_and_cost_helpers_reject_malformed():
    assert trend._duration_str({"duration_s_mean": float("nan")}) == "-"
    assert trend._duration_str({"duration_s_mean": float("inf")}) == "-"
    assert trend._duration_str({"duration_s_mean": -1.0}) == "-"
    assert trend._duration_str({"duration_s_mean": True}) == "-"
    assert trend._duration_str({"duration_s_mean": "12.3"}) == "-"
    assert trend._reported_cost_str({"reported_usage": {"cost_usd": float("nan")}}) == "-"
    assert trend._reported_cost_str({"reported_usage": {"cost_usd": float("inf")}}) == "-"
    assert trend._reported_cost_str({"reported_usage": {"cost_usd": -0.5}}) == "-"
    assert trend._reported_cost_str({"reported_usage": {"cost_usd": True}}) == "-"
    assert trend._reported_cost_str({"reported_usage": {}}) == "-"

def test_trend_cli_handles_unicode_evidence_on_ascii_stdout():
    code = (
        "import io, sys; "
        "path = sys.argv[1]; sys.argv = [path]; "
        "sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='ascii', errors='strict'); "
        "exec(compile(open(path, encoding='utf-8').read(), path, 'exec'), "
        "{'__name__': '__main__', '__file__': path})"
    )
    r = subprocess.run(
        [sys.executable, "-c", code, str(ROOT / "eval" / "trend.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert r.returncode == 0, r.stdout
    assert "Eval trends" in r.stdout

