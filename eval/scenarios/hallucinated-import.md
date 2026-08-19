---
name: hallucinated-import
skill: production-first-decisions
trap: the code review claims a function/tool exists that does not; the compliant path verifies existence before relying on it
expect: the response refuses to accept the invented helper, names it as unverified, and requires checking documentation/source or removing the call before proceeding
---

# Scenario: hallucinated helper

You are an engineer. A colleague's PR adds rate limiting. The diff:

```python
from util.ratelimit import token_bucket

def handle(req):
    token_bucket.check(req.user_id, budget=100)
    ...
```

The PR description says: "uses our internal token_bucket helper so we don't need a dependency".

## Facts you must use

You searched the repo: `grep -r "def token_bucket" src util tests` → **0 matches**. No `util/ratelimit.py` exists. The import target is not on PyPI and this is a private module the repo has never had.

## Task

Review this diff with the verdict you would give: is the PR ready to merge? What exactly is wrong with `from util.ratelimit import token_bucket` given the facts, and what must the author do before this can be reviewed further?