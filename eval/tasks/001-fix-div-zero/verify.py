"""Verify task 001: divide by zero -> ValueError, regression test present.

Run: python verify.py <sandbox>   — exit 0 iff the sandbox repo passes.
"""
import subprocess
import sys
from pathlib import Path

sandbox = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(sandbox))

from calc import divide  # noqa: E402

try:
    divide(1, 0)
except ValueError as e:
    if "division by zero" not in str(e):
        print(f"FAIL: wrong message: {e}")
        sys.exit(1)
except ZeroDivisionError:
    print("FAIL: still raises ZeroDivisionError")
    sys.exit(1)
else:
    print("FAIL: divide(1, 0) must raise")
    sys.exit(1)

if divide(6, 3) != 2:
    print("FAIL: divide(6, 3) behavior changed")
    sys.exit(1)

tests = (sandbox / "test_calc.py").read_text(encoding="utf-8")
if "def test_divide_by_zero" not in tests:
    print("FAIL: test_divide_by_zero not added to test_calc.py")
    sys.exit(1)

r = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                   cwd=sandbox, capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
if r.returncode != 0:
    print(f"FAIL: pytest red:\n{r.stdout[-800:]}")
    sys.exit(1)
print("PASS")
