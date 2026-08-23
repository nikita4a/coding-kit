import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

import trend


def test_render_table_and_proposals(monkeypatch):
    fake = [
        {"kind": "trap", "model": "m1", "utc": "2026-08-24T10:00:00+00:00",
         "passed": 17, "total": 18,
         "scenarios": [{"name": "scope-creep", "skill": "yagni",
                        "verdict": "FAIL"}]},
        {"kind": "trap", "model": "m1", "utc": "2026-08-25T10:00:00+00:00",
         "passed": 18, "total": 18,
         "scenarios": [{"name": "scope-creep", "skill": "yagni",
                        "verdict": "PASS"}]},
        {"kind": "tasks", "model": "m2", "utc": "2026-08-25T11:00:00+00:00",
         "passed": 1, "total": 2, "pass_rate": 0.5,
         "rows": [{"name": "002-add-validation", "verdict": "FAIL"}]},
    ]
    monkeypatch.setattr(trend, "load_runs", lambda kind=None: fake)
    md = trend.render()
    assert "| trap | m1 |" in md and "18/18" in md and "17/18" in md
    assert "Proposals" in md
    # newest trap run is all-green -> scope-creep must NOT be proposed
    assert "scope-creep" not in md.split("Proposals")[1]
    # newest tasks run has a FAIL -> it must be proposed
    assert "002-add-validation" in md.split("Proposals")[1]


def test_render_trigger_misses(monkeypatch):
    fake = [{"kind": "trigger", "model": "m1",
             "utc": "2026-08-25T10:00:00+00:00",
             "fired": 78, "total": 80,
             "misses": ["fable-judge: trigger rate 0.60"]}]
    monkeypatch.setattr(trend, "load_runs", lambda kind=None: fake)
    md = trend.render()
    assert "fired 78/80" in md
    assert "[routing]" in md.split("Proposals")[1]


def test_render_empty_store():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(trend, "load_runs", lambda kind=None: [])
    assert "no results yet" in trend.render()
