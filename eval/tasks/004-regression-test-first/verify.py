"""Verify task 004: median even-count bug fixed, regression test written
first (red run shown before the fix).

Run: python verify.py <sandbox> — exit 0 iff the sandbox repo passes.
"""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


# Shared AST oracle helpers (eval/tasks/_verify_common.py).
_TASKS_DIR = Path(__file__).resolve().parent.parent
if str(_TASKS_DIR) not in sys.path:
    sys.path.insert(0, str(_TASKS_DIR))
from _verify_common import audit_test_calc_file  # noqa: E402
_TASK_ID = "004-regression-test-first"



def _isolated_suite(sandbox: Path, calc_source: str, tmp_dir: Path):
    """Run the candidate's test_calc.py against one calc.py in an empty dir.

    Only test_calc.py is copied from the sandbox; conftest.py and config files
    are not copied and pytest plugin autoload is disabled, so a candidate cannot
    manufacture a control outcome via conftest/plugin hooks or control files.
    """
    shutil.copy2(sandbox / "test_calc.py", tmp_dir / "test_calc.py")
    (tmp_dir / "calc.py").write_text(calc_source, encoding="utf-8",
                                     newline="\n")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--noconftest",
         "-p", "no:cacheprovider", "test_calc.py"],
        cwd=str(tmp_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def _answer_reports_red_run(sandbox: Path) -> bool:
    """The TASK.md demands the red-then-green evidence in the final answer.

    task_runner feeds TASK.md to the executor via stdin and keeps no executor
    transcript beyond its stdout, which lands in the sandbox as the runner
    contract's response artifact only under --answer-path; the runner can
    therefore only verify the machine-checkable half of the contract here:
    the test must fail on pristine and pass on fixed (steps 3a/3b below).
    This check looks for the red-run evidence file the TASK.md tells the
    candidate to leave in the sandbox: red_run.txt containing a pytest
    FAILED line naming the regression test.
    """
    marker = sandbox / "red_run.txt"
    if not marker.is_file():
        return False
    try:
        text = marker.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "FAILED" in text and "test_" in text


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing sandbox path argument")
        return 1

    sandbox = Path(sys.argv[1]).resolve()
    calc_path = sandbox / "calc.py"
    if not sandbox.is_dir() or not calc_path.is_file():
        print(f"FAIL: invalid sandbox directory: {sandbox}")
        return 1

    tasks_dir = _TASKS_DIR
    pristine_calc = tasks_dir / "repo-fixture" / "calc.py"
    if not pristine_calc.is_file():
        print(f"FAIL: pristine fixture missing at {pristine_calc}")
        return 1

    # 0. AST audit: reject implementation introspection and require real
    #    behavioral regression coverage before any behavior/mutation check.
    ok, failures = audit_test_calc_file(sandbox, _TASK_ID)
    if not ok:
        for reason in failures:
            print(f"FAIL: {reason}")
        return 1

    # 0b. Red-first evidence: the TASK.md demands the failing run before the
    #     fix. The candidate leaves that run's output in red_run.txt.
    if not _answer_reports_red_run(sandbox):
        print("FAIL: no red-run evidence: TASK.md requires running pytest "
              "BEFORE the fix and saving the failing output to red_run.txt "
              "(expected a pytest FAILED line naming the new test)")
        return 1

    # 1. Direct behavior checks on candidate calc.py
    spec = importlib.util.spec_from_file_location("calc", str(calc_path))
    if spec is None or spec.loader is None:
        print("FAIL: cannot load calc.py from sandbox")
        return 1
    calc = importlib.util.module_from_spec(spec)
    sys.modules["calc"] = calc
    try:
        spec.loader.exec_module(calc)
    except Exception as e:
        print(f"FAIL: exception importing candidate calc.py: {type(e).__name__}: {e}")
        return 1

    median_checks = [
        ([1, 2, 3], 2),
        ([7], 7),
        ([4, 1, 3, 2], 2.5),
        ([10, 20], 15),
        ([1, 2, 3, 100], 2.5),
        ([-5, -1, -2, -4], -3),
    ]
    for values, expected in median_checks:
        try:
            res = calc.median(values)
        except Exception as e:
            print(f"FAIL: median({values}) raised {type(e).__name__}: {e}")
            return 1
        if res != expected:
            print(f"FAIL: median({values}) returned {res!r}, expected {expected!r}")
            return 1

    # Check unaffected behavior
    try:
        if calc.divide(6, 3) != 2:
            print("FAIL: divide(6, 3) behavior changed")
            return 1
        if calc.parse_int("42") != 42:
            print("FAIL: parse_int('42') behavior changed")
            return 1
        if calc.clamp(5, 0, 10) != 5:
            print("FAIL: clamp(5, 0, 10) behavior changed")
            return 1
    except Exception as e:
        print(f"FAIL: unexpected exception checking unaffected behavior: {type(e).__name__}: {e}")
        return 1

    # 2. Run candidate sandbox's full pytest suite (must be green)
    try:
        r_cand = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=sandbox,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print("FAIL: candidate pytest suite timed out")
        return 1
    if r_cand.returncode != 0:
        print(f"FAIL: candidate pytest suite failed in sandbox:\n{r_cand.stdout}\n{r_cand.stderr}")
        return 1

    # 3. Regression oracle: a real test must (a) pass with the fix, (b) fail
    #    against the pristine fixture, and (c) fail when only `median` is
    #    reverted to pristine. Runs are isolated and plugin autoload is off, so
    #    a conftest/plugin cannot manufacture failure. Only pytest rc==1 (tests
    #    collected and at least one failed) counts as regression evidence: rc 0
    #    (passed), 2/3/4 (collection/internal/usage error) and 5 (no tests
    #    collected) all reject.
    cand_code = calc_path.read_text(encoding="utf-8")
    pristine_code = pristine_calc.read_text(encoding="utf-8")
    revert_code = cand_code + "\n\n# Pristine median override\ndef median(values):\n    ordered = sorted(values)\n    mid = len(ordered) // 2\n    if len(ordered) % 2 == 0:\n        return ordered[mid] + ordered[mid - 1]\n    return ordered[mid]\n"

    with tempfile.TemporaryDirectory() as td:
        try:
            r_ok = _isolated_suite(sandbox, cand_code, Path(td))
        except subprocess.TimeoutExpired:
            print("FAIL: candidate isolated pytest timed out")
            return 1
        if r_ok.returncode != 0:
            print(f"FAIL: candidate tests not green in isolation (rc={r_ok.returncode}):\n{r_ok.stdout}\n{r_ok.stderr}")
            return 1

    with tempfile.TemporaryDirectory() as td:
        try:
            r_pris = _isolated_suite(sandbox, pristine_code, Path(td))
        except subprocess.TimeoutExpired:
            print("FAIL: pristine fixture pytest timed out")
            return 1
        if r_pris.returncode != 1:
            print(f"FAIL: candidate tests did not fail on pristine calc.py (rc={r_pris.returncode}); missing regression test for the median even-count defect:\n{r_pris.stdout}\n{r_pris.stderr}")
            return 1

    with tempfile.TemporaryDirectory() as td:
        try:
            r_rev = _isolated_suite(sandbox, revert_code, Path(td))
        except subprocess.TimeoutExpired:
            print("FAIL: revert pytest timed out")
            return 1
        if r_rev.returncode != 1:
            print(f"FAIL: candidate tests did not fail when median was reverted to pristine (rc={r_rev.returncode}); regression test does not target median:\n{r_rev.stdout}\n{r_rev.stderr}")
            return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
