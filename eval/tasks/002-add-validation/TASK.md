---
name: add-validation
---
In the repository in your working directory: `parse_int("abc")` raises
ValueError with an unhelpful message, and `parse_int(" 42 ")` fails.
Accept surrounding whitespace and raise ValueError("not an integer: <input>")
for non-numeric input. Add tests covering both cases. Run pytest to prove it.
