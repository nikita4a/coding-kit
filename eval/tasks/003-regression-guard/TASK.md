---
name: regression-guard
---
In the repository in your working directory there is a bug in one of the
functions in calc.py: find it from the function names and semantics alone,
write a failing test that demonstrates it, then fix the function minimally.
Run pytest to prove red→green. Do NOT change function signatures.

The test must be a real regression test: explicit boundary calls with literal
arguments for every way the function can misbehave (a value below the range
and a value above the range, each asserted against the correct clamped
result), plus at least one in-range value. The verifier re-runs your test
against the pristine (buggy) code — it must fail there — and against your fix
with only that function reverted — it must fail there too.
