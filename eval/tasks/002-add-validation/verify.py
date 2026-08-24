"""Verify task 002: parse_int accepts whitespace, clear error on non-numeric input.

Run: python verify.py <sandbox> — exit 0 iff the sandbox repo passes.
"""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing sandbox path argument")
        return 1

    sandbox = Path(sys.argv[1]).resolve()
    calc_path = sandbox / "calc.py"
    if not sandbox.is_dir() or not calc_path.is_file():
        print(f"FAIL: invalid sandbox directory: {sandbox}")
        return 1

    tasks_dir = Path(__file__).resolve().parent.parent
    pristine_calc = tasks_dir / "repo-fixture" / "calc.py"
    if not pristine_calc.is_file():
        print(f"FAIL: pristine fixture missing at {pristine_calc}")
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

    # Check whitespace handling
    ws_cases = [(" 42 ", 42), ("\t7\n", 7), ("  -12  ", -12), ("0", 0)]
    for s, expected in ws_cases:
        try:
            res = calc.parse_int(s)
        except Exception as e:
            print(f"FAIL: parse_int({s!r}) raised {type(e).__name__}: {e}")
            return 1
        if res != expected:
            print(f"FAIL: parse_int({s!r}) returned {res!r}, expected {expected}")
            return 1

    # Check non-numeric error handling with custom message ValueError("not an integer: <input>")
    bad_cases = ["abc", "12.34", "foo"]
    for bad_input in bad_cases:
        try:
            calc.parse_int(bad_input)
        except ValueError as e:
            msg = str(e)
            if "not an integer" not in msg or bad_input not in msg:
                print(f"FAIL: parse_int({bad_input!r}) raised ValueError with non-conforming message: {msg!r}")
                return 1
        except Exception as e:
            print(f"FAIL: parse_int({bad_input!r}) raised unexpected exception: {type(e).__name__}: {e}")
            return 1
        else:
            print(f"FAIL: parse_int({bad_input!r}) did not raise ValueError")
            return 1

    # Check unaffected behavior
    try:
        if calc.divide(6, 3) != 2:
            print("FAIL: divide(6, 3) behavior changed")
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

    # 3. Prove candidate regression tests catch the defect against pristine calc.py
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for item in sandbox.iterdir():
            if item.name in ("calc.py", "__pycache__"):
                continue
            if item.is_dir():
                shutil.copytree(item, tmp_path / item.name)
            else:
                shutil.copy2(item, tmp_path / item.name)
        shutil.copy2(pristine_calc, tmp_path / "calc.py")

        try:
            r_pristine = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            print("FAIL: pristine test run timed out")
            return 1
        if r_pristine.returncode == 0:
            print("FAIL: candidate tests did not fail on pristine calc.py (missing regression test for custom ValueError)")
            return 1

    # 4. Prove candidate regression tests specifically catch the parse_int defect
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for item in sandbox.iterdir():
            if item.name in ("calc.py", "__pycache__"):
                continue
            if item.is_dir():
                shutil.copytree(item, tmp_path / item.name)
            else:
                shutil.copy2(item, tmp_path / item.name)
        cand_code = calc_path.read_text(encoding="utf-8")
        pristine_parse_int_override = "\n\n# Pristine parse_int override\ndef parse_int(s):\n    return int(s)\n"
        (tmp_path / "calc.py").write_text(cand_code + pristine_parse_int_override, encoding="utf-8")

        try:
            r_revert = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            print("FAIL: revert test run timed out")
            return 1
        if r_revert.returncode == 0:
            print("FAIL: candidate tests did not fail when parse_int was reverted to pristine (regression test does not target parse_int custom error)")
            return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
