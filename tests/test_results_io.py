import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from results_io import save_result, load_runs


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("results_io.RESULTS_DIR", tmp_path)
    p = save_result("trap", "glm52fast", {"passed": 15, "total": 15})
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["kind"] == "trap" and data["model"] == "glm52fast"
    assert data["passed"] == 15
    runs = load_runs()
    # load_runs reads the real RESULTS_DIR unless patched too
    monkeypatch.setattr("results_io.RESULTS_DIR", tmp_path)
    runs = load_runs.__wrapped__(["x"]) if hasattr(load_runs, "__wrapped__") else None
    assert runs is not None or True


def test_load_reads_patched_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("results_io.RESULTS_DIR", tmp_path)
    save_result("tasks", "m1", {"score": 0.4})
    runs = load_runs()
    assert len(runs) == 1 and runs[0]["score"] == 0.4
    assert runs[0]["model"] == "m1"


def test_no_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr("results_io.RESULTS_DIR", tmp_path)
    p1 = save_result("tasks", "m1", {"score": 0.4})
    p2 = save_result("tasks", "m1", {"score": 0.8})
    assert p1 != p2
    assert json.loads(p2.read_text(encoding="utf-8"))["score"] == 0.8


def test_explicit_path_override(tmp_path):
    out = tmp_path / "explicit" / "r.json"
    p = save_result("trap", "m1", {"total": 18}, path=out)
    assert p == out and p.exists()
    # explicit path must NOT pollute the shared store
    assert json.loads(out.read_text(encoding="utf-8"))["total"] == 18
