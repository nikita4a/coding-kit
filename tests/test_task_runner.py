import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_task_runner_discovers_tasks():
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "task_runner.py"), "--dry-run"],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert "3 tasks" in r.stdout


def test_verify_rejects_pristine_fixture(tmp_path):
    # pristine fixture keeps the clamp bug and old parse_int -> both fail
    for task in ("002-add-validation", "003-regression-guard"):
        sandbox = tmp_path / task
        shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sandbox)
        v = ROOT / "eval" / "tasks" / task / "verify.py"
        r = subprocess.run([sys.executable, str(v), str(sandbox)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        assert r.returncode == 1, f"{task} verify must reject pristine fixture"


def test_verify_accepts_fixed_fixture(tmp_path):
    # apply the reference fix for 001, verify must accept
    sandbox = tmp_path / "fixed"
    shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sandbox)
    (sandbox / "calc.py").write_text(
        (sandbox / "calc.py").read_text(encoding="utf-8")
        .replace("    return a / b",
                 '    if b == 0:\n        raise ValueError("division by zero")\n'
                 "    return a / b"),
        encoding="utf-8", newline="\n")
    tests = (sandbox / "test_calc.py").read_text(encoding="utf-8")
    tests += '''

def test_divide_by_zero():
    import pytest
    with pytest.raises(ValueError):
        divide(1, 0)
'''
    (sandbox / "test_calc.py").write_text(tests, encoding="utf-8", newline="\n")
    v = ROOT / "eval" / "tasks" / "001-fix-div-zero" / "verify.py"
    r = subprocess.run([sys.executable, str(v), str(sandbox)],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout + r.stderr
