---
name: mock-pollution
skill: testing-discipline
trap: the test mocks the very function it is supposed to verify, so the green assertion proves the mock returns what it was told — not that the real code works
expect: the review names the tautology: mocking calc_bonus inside the calc_bonus test makes the assertion circular and the green test meaningless; the real implementation path must be exercised (or the mock removed) before the test counts as coverage
---

# Scenario: mock pollution review

You review a new unit test.

## The test

```python
def test_bonus_calculation():
    mocker.patch("bonus.calc_bonus", return_value=5)
    result = bonus.calc_bonus(100)
    assert result == 5
```

## Author's comment

"Fast and isolated — no database, no files. Coverage for bonus.py is now 100%."

## Task

Your verdict as the testing reviewer. What does this test actually prove about calc_bonus?