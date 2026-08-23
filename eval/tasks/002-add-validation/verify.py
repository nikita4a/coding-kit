"""Verify task 002: parse_int accepts whitespace, clear error on garbage.

Run: python verify.py <sandbox>   — exit 0 iff the sandbox repo passes.
"""
import subprocess
import sys
from pathlib import Path

sandbox = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(sandbox))

from calc import parse_int  # noqa: E402

checks = [
    (parse_int(" 42 ") == 42, "parse_int(' 42 ') must be 42"),
    (parse_int("\t7\n") == 7, "parse_int('\\t7\\n') must be 7"),
]
for ok, msg in checks:
    if not ok:
        print(f"FAIL: {msg}")
        sys.exit(1)

try:
    parse_int("abc")
except ValueError as e:
    if "not an integer" not in str(e) or "abc" not in str(e):
        print(f"FAIL: wrong message format: {e}")
        sys.exit(1)
else:
    print("FAIL: parse_int('abc') must raise ValueError")
    sys.exit(1)

r = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                   cwd=sandbox, capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
if r.returncode != 0:
    print(f"FAIL: pytest red:\n{r.stdout[-800:]}")
    sys.exit(1)
print("PASS")
