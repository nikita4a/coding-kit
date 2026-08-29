---
name: regression-test-first
---
In the repository in your working directory there is a bug in one of the
functions in calc.py: find it from the function names and semantics alone.
Write the failing test FIRST: run pytest BEFORE fixing anything and save
that failing output to red_run.txt in the repo root, then fix the function
minimally and run pytest again to show red→green. The saved red output must
show the new test failing, not an error. Do NOT change function signatures.
