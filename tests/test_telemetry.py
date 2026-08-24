"""Contract tests for eval/telemetry.py — wall-time aggregation and
user-reported usage ingestion. No model calls."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from telemetry import load_reported_usage, summarize_durations


def test_summarize_durations_sums_finite_attempts():
    rows = [
        {"attempts": [{"verdict": "PASS", "duration_s": 2.5}]},
        {"attempts": [{"verdict": "FAIL", "duration_s": 1.0},
                      {"verdict": "PASS", "duration_s": 3.0}]},
    ]
    total, mean = summarize_durations(rows)
    assert total == 6.5
    assert mean == round(6.5 / 3, 3)


def test_summarize_durations_empty_returns_zeros():
    assert summarize_durations([]) == (0.0, 0.0)
    assert summarize_durations([{"attempts": []}]) == (0.0, 0.0)


def test_summarize_durations_skips_missing_and_non_numeric():
    rows = [
        {"attempts": [{"verdict": "FAIL"}]},          # no duration_s
        {"attempts": [{"verdict": "PASS", "duration_s": None}]},
        {"attempts": [{"verdict": "PASS", "duration_s": "2.5"}]},
    ]
    assert summarize_durations(rows) == (0.0, 0.0)


def test_summarize_durations_skips_negative_and_nonfinite():
    rows = [
        {"attempts": [{"duration_s": -1.0}]},
        {"attempts": [{"duration_s": float("nan")}]},
        {"attempts": [{"duration_s": float("inf")}]},
        {"attempts": [{"duration_s": True}]},         # bool is not a duration
        {"attempts": [{"duration_s": 2.0}]},
    ]
    total, mean = summarize_durations(rows)
    assert total == 2.0
    assert mean == 2.0


def test_load_reported_usage_parses_valid_file(tmp_path):
    f = tmp_path / "u.json"
    f.write_text(json.dumps({"tokens_total": 12345, "cost_usd": 0.42}),
                 encoding="utf-8")
    assert load_reported_usage(str(f)) == {"tokens_total": 12345, "cost_usd": 0.42}


def test_load_reported_usage_none_path_returns_none():
    assert load_reported_usage(None) is None


def test_load_reported_usage_missing_file_warns_and_returns_none(tmp_path, capsys):
    assert load_reported_usage(str(tmp_path / "nope.json")) is None
    assert "usage-json" in capsys.readouterr().err


def test_load_reported_usage_rejects_garbage_json(tmp_path, capsys):
    f = tmp_path / "u.json"
    f.write_text("not json", encoding="utf-8")
    assert load_reported_usage(str(f)) is None
    assert "usage-json" in capsys.readouterr().err


def test_load_reported_usage_rejects_non_object(tmp_path, capsys):
    f = tmp_path / "u.json"
    f.write_text("[1, 2]", encoding="utf-8")
    assert load_reported_usage(str(f)) is None
    assert "usage-json" in capsys.readouterr().err


def test_load_reported_usage_rejects_negative(tmp_path):
    f = tmp_path / "u.json"
    f.write_text(json.dumps({"tokens_total": -1, "cost_usd": 0.1}),
                 encoding="utf-8")
    assert load_reported_usage(str(f)) is None


def test_load_reported_usage_rejects_bool(tmp_path):
    f = tmp_path / "u.json"
    f.write_text(json.dumps({"tokens_total": True, "cost_usd": 0.1}),
                 encoding="utf-8")
    assert load_reported_usage(str(f)) is None
    f2 = tmp_path / "u2.json"
    f2.write_text(json.dumps({"tokens_total": 10, "cost_usd": False}),
                  encoding="utf-8")
    assert load_reported_usage(str(f2)) is None


def test_load_reported_usage_rejects_nan_and_infinity(tmp_path):
    f = tmp_path / "nan.json"
    f.write_text('{"cost_usd": NaN}', encoding="utf-8")
    assert load_reported_usage(str(f)) is None
    f2 = tmp_path / "inf.json"
    f2.write_text('{"tokens_total": Infinity}', encoding="utf-8")
    assert load_reported_usage(str(f2)) is None


def test_load_reported_usage_optional_keys(tmp_path):
    f = tmp_path / "only_cost.json"
    f.write_text(json.dumps({"cost_usd": 0.5}), encoding="utf-8")
    assert load_reported_usage(str(f)) == {"cost_usd": 0.5}


def test_load_reported_usage_empty_object_returns_none(tmp_path):
    f = tmp_path / "u.json"
    f.write_text("{}", encoding="utf-8")
    assert load_reported_usage(str(f)) is None


def test_load_reported_usage_both_keys_null_returns_none(tmp_path):
    f = tmp_path / "u.json"
    f.write_text(json.dumps({"tokens_total": None, "cost_usd": None}),
                 encoding="utf-8")
    assert load_reported_usage(str(f)) is None


def test_load_reported_usage_unknown_keys_only_returns_none(tmp_path):
    f = tmp_path / "u.json"
    f.write_text(json.dumps({"unknown_key": 1, "foo": "bar"}), encoding="utf-8")
    assert load_reported_usage(str(f)) is None