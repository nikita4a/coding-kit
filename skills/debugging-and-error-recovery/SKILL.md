---
name: debugging-and-error-recovery
description: Guides systematic root-cause debugging. Use when tests fail, builds break, behavior doesn't match expectations, or you encounter any unexpected error. Use when you need a systematic approach to finding and fixing the root cause rather than guessing.
---

# Debugging and Error Recovery

## Overview

Systematic debugging with structured triage. When something breaks, stop adding features, preserve evidence, and follow a structured process to find and fix the root cause. Guessing wastes time.

## The Stop-the-Line Rule

When anything unexpected happens:
```
1. STOP adding features or making changes
2. PRESERVE evidence (error output, logs, repro steps)
3. DIAGNOSE using the triage checklist
4. FIX the root cause
5. GUARD against recurrence
6. RESUME only after verification passes
```

## The Triage Checklist

### Step 1: Reproduce
Make the failure happen reliably. If you can't reproduce it, you can't fix it with confidence.

### Step 2: Localize
Narrow down WHERE the failure happens:
```
Which layer is failing?
├── UI/Frontend     → Check console, DOM, network tab
├── API/Backend     → Check server logs, request/response
├── Database        → Check queries, schema, data integrity
├── Build tooling   → Check config, dependencies, environment
├── External service → Check connectivity, API changes, rate limits
└── Test itself     → Check if the test is correct (false negative)
```

**Use bisection for regression bugs:**
```bash
git bisect start
git bisect bad              # Current commit is broken
git bisect good <known-good-sha>  # This commit worked
```

### Step 3: Reduce
Create the minimal failing case. Remove unrelated code until only the bug remains. A minimal reproduction makes the root cause obvious.

### Step 4: Fix the Root Cause
Fix the underlying issue, not the symptom. Ask "Why does this happen?" until you reach the actual cause.

### Step 5: Guard Against Recurrence
Write a test that catches this specific failure. This test should fail without the fix and pass with it.

### Step 6: Verify End-to-End
After fixing:
- Run the specific test
- Run the full test suite
- Build the project
- Manual spot check if applicable

## Error-Specific Patterns

### Test Failure Triage
```
Test fails after code change:
├── Did you change code the test covers? → Check if test or code is wrong
├── Did you change unrelated code? → Check shared state, imports, globals
└── Test was already flaky? → Check timing issues, order dependence
```

### Build Failure Triage
```
Build fails:
├── Type error → Read error, check types at cited location
├── Import error → Check module exists, exports match, paths correct
├── Config error → Check build config files
├── Dependency error → Check package.json, run install
└── Environment error → Check version, OS compatibility
```

## Safe Fallback Patterns

```typescript
// Safe default + warning (instead of crashing)
function getConfig(key: string): string {
  const value = process.env[key];
  if (!value) {
    console.warn(`Missing config: ${key}, using default`);
    return DEFAULTS[key] ?? '';
  }
  return value;
}
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I know what the bug is, I'll just fix it" | You might be right 70% of the time. The other 30% costs hours. Reproduce first. |
| "It works on my machine" | Environments differ. Check CI, config, dependencies. |
| "This is a flaky test, ignore it" | Flaky tests mask real bugs. Fix the flakiness. |

## Red Flags
- Skipping a failing test to work on new features
- Guessing at fixes without reproducing the bug
- Fixing symptoms instead of root causes
- "It works now" without understanding what changed
- No regression test added after a bug fix