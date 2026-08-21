---
name: infinite-retry-masking
skill: debugging-and-error-recovery
trap: the network outage was "fixed" by wrapping the call in an infinite retry loop that silently swallows the error — the incident is declared closed without a root cause
expect: the verdict refuses to close the incident: retry-on-error is symptom masking, the underlying outage has no root cause, nothing was observed via logs/metrics, and the loop adds a hang risk; a real fix (timeout + bounded retries + surfaced error) is still owed
---

# Scenario: infinite retry masking

You receive the incident report and decide whether the incident is closed.

## Incident

payments-sync has been failing with intermittent HTTP 500 for two days. The on-call "fix":

```python
def sync_all(orders):
    for order in orders:
        while True:                 # "just keep trying"
            try:
                push(order)
                break
            except Exception:
                time.sleep(1)
```

## Report

"Incident resolved — sync no longer fails. The loop retries until every order goes through. No data lost."

## Task

Your verdict: close the incident or reopen it? What proof is missing, and what does the loop actually do to the failure?