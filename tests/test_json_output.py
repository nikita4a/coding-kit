import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_runner_dry_run_json(tmp_path):
    out = tmp_path / "r.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "runner.py"), "--json", str(out)],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["kind"] == "trap" and data["total"] >= 18
    assert data["passed"] == data["total"]  # dry-run: all scenarios valid


def test_trigger_dry_run_json(tmp_path):
    out = tmp_path / "t.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "trigger_eval.py"),
         "--queries", str(ROOT / "eval" / "trigger_queries.json"),
         "--json", str(out)],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["kind"] == "trigger" and data["total"] == 80
    assert data["mode"] == "dry-run"


def test_auto_json_writes_shared_store(tmp_path, monkeypatch):
    # --json auto must land in eval/results with a timestamped name;
    # patch RESULTS_DIR via a temp copy is impossible cross-process,
    # so assert the file appears in the real store and clean up.
    before = set((ROOT / "eval" / "results").glob("*.json"))
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "runner.py"), "--json", "auto"],
        capture_output=True, text=True, encoding="utf-8")
    after = set((ROOT / "eval" / "results").glob("*.json"))
    new = after - before
    try:
        assert r.returncode == 0, r.stderr
        assert len(new) == 1
        data = json.loads(new.pop().read_text(encoding="utf-8"))
        assert data["kind"] == "trap"
    finally:
        for p in new:
            p.unlink()
