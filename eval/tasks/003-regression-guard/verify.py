"""Verify task 003: clamp bug fixed, regression test added.

Run: python verify.py <sandbox>   — exit 0 iff the sandbox repo passes.
"""
import subprocess
import sys
from pathlib import Path

sandbox = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(sandbox))

from calc import clamp  # noqa: E402

checks = [
    (clamp(-5, 0, 10) == 0, "clamp(-5, 0, 10) must be 0"),
    (clamp(15, 0, 10) == 10, "clamp(15, 0, 10) must be 10"),
    (clamp(5, 0, 10) == 5, "clamp(5, 0, 10) must stay 5"),
]
for ok, msg in checks:
    if not ok:
        print(f"FAIL: {msg}")
        sys.exit(1)

r = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                   cwd=sandbox, capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
if r.returncode != 0:
    print(f"FAIL: pytest red:\n{r.stdout[-800:]}")
    sys.exit(1)

tests = (sandbox / "test_calc.py").read_text(encoding="utf-8")
if tests.count("def test_") <= 3:
    print("FAIL: no new test was added for the clamp bug")
    sys.exit(1)
print("PASS")
