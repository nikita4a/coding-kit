---
name: troubleshooting
description: "Domain skill. Troubleshooting — systematic problem diagnosis and resolution. Use for bugs, failures, unexpected behavior. 5-phase workflow: problem statement, reproduce, diagnose, fix, verify."
---

# Troubleshooting — systematic problem diagnosis

Domain skill. Systematic approach to diagnosing and resolving problems.

## When to use

- Bug reports or unexpected behavior
- System failures or crashes
- Performance degradation
- User says "not working", "broken", "debug this"

## Workflow

### Phase 1: Problem Statement
1. Describe the symptom — what is observed vs what is expected.
2. Note when it started, what changed recently.
3. Capture the exact error message, stack trace, or log output.
4. Identify the affected component and its dependencies.

### Phase 2: Reproduce
1. Find the minimal reproduction steps.
2. Isolate the failing path — strip away unrelated code.
3. If non-deterministic, note the frequency and conditions.
4. A bug that can't be reproduced is a hypothesis, not a diagnosis.

### Phase 3: Diagnose
1. Trace the execution path from symptom to root cause.
2. Use diagnostic tools: logs, debugger, metrics, traces.
3. Form hypotheses and test them one at a time.
4. Rule out the obvious first: config, permissions, connectivity, recent changes.
5. Don't fix the symptom — find the root cause.

### Phase 4: Fix
1. Apply the minimal fix that addresses the root cause.
2. Verify the fix resolves the reproduction case.
3. Check for similar patterns elsewhere (the bug may have siblings).
4. Add a regression test to prevent recurrence.

### Phase 5: Verify
1. Confirm the original symptom is gone.
2. Run the full test suite.
3. Monitor in production if applicable.
4. Document the root cause and fix for future reference.

## Diagnostic Tools

| Tool | Purpose |
|------|---------|
| Logs | Trace execution, find error messages |
| Debugger | Step through code, inspect state |
| Metrics | Identify anomalies, trends, bottlenecks |
| Traces | Follow request flow across services |
| git bisect | Find the commit that introduced the bug |
| strace/ltrace | System call and library call tracing |

## Common Patterns

| Symptom | Likely Causes |
|---------|--------------|
| Works locally, fails in prod | Config, env vars, network, permissions |
| Intermittent failure | Race condition, timeout, resource exhaustion |
| Works then suddenly breaks | Recent deploy, config change, dependency update |
| Silent failure | Swallowed exception, missing error handling |
| Performance regression | N+1 query, missing index, unbounded growth |

## Anti-patterns

- Fixing the symptom instead of the root cause
- Guessing without evidence
- Changing multiple things at once — can't tell which fixed it
- Skipping the reproduction step
- Not adding a regression test after the fix