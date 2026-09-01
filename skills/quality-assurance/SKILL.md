---
name: quality-assurance
description: Domain skill. Quality Assurance — test planning, review checklists, quality gates, coverage targets.
---

# Quality Assurance

## Overview

Creates `specs/quality/plan.md` — a living quality plan for the project. The plan defines test strategy, review checklists, quality gates, and coverage targets. Every feature, refactor, or integration gets a quality plan before code is merged.

## When to use

- Starting a new feature or module — write a quality plan first
- Setting up a new repository — create the initial quality baseline
- Reviewing a change that touches money, auth, data, or user-facing output
- Enforcing a quality gate before merge or release
- Auditing test coverage and identifying gaps

## Output

Write or update `specs/quality/plan.md`. Structure:

```markdown
# Quality Plan: <scope>

## Test Strategy
- Unit vs integration vs e2e split
- What lives in offline tests vs what needs a sandbox
- Fixture strategy (factories, mocks, fakes, temp storage)

## Quality Gates
- What must pass before merge (compile, lint, test, type-check)
- What must pass before release (e2e, perf, security scan)
- Blocking vs advisory gates

## Coverage Targets
- Line / branch / mutation coverage minimums
- Excluded paths and why
- Enforcement mechanism (CI threshold, blocking or warning)

## Review Checklists
- Per domain: code review, security review, data review, money review
- What each reviewer checks
- Sign-off requirements

## Risk Inventory
- Known fragile areas
- Past regressions
- What to smoke-test on every deploy
```

## Workflow

### 1. Assess the scope

Determine the scope of the quality plan. Options:

| Scope | When | Coverage target |
|-------|------|----------------|
| Feature | New capability, single module | 80% unit, 60% integration |
| Refactor | No behavior change, structural | 80% on changed modules |
| Integration | Connecting external service | 70% integration, 90% on adapter |
| Money path | Payments, billing, balance | 95% unit, 100% on money logic |
| Data migration | Schema change, data transform | Dry-run comparison, rollback test |

### 2. Define the test strategy

Pick the test levels and their split:

- **Unit tests** (~70-80%): Pure logic, domain rules, utility functions. No I/O. Milliseconds.
- **Integration tests** (~15-20%): Component interactions, API boundaries, database access, external service fakes.
- **E2E tests** (~5-10%): Full user flows, critical paths, smoke tests on staging.

**Fixture rules:**
- Use temp storage, never prod or shared dev stores
- Module-level side effects: fresh import per test or fixture
- Fakes at the I/O boundary, not inside your logic
- Prefer real implementations over mocks where deterministic

### 3. Set quality gates

Define gates by stage:

```
PRE-MERGE GATES:
  [ ] Compile / type-check — 0 errors
  [ ] Lint — 0 errors (ruff, eslint, etc.)
  [ ] Unit tests — pass, ≥80% coverage
  [ ] Integration tests — pass
  [ ] Security scan — no CRITICAL/HIGH findings
  [ ] No hardcoded secrets (gitleaks / trufflehog)

PRE-RELEASE GATES:
  [ ] E2E smoke tests — pass
  [ ] Performance regression — within 5% of baseline
  [ ] Dependency audit — no known vulnerabilities
  [ ] Manual exploratory pass on changed paths
```

### 4. Set coverage targets

```
MINIMUM:
  Line coverage:      80%
  Branch coverage:    70%
  Money-path lines:   95% (no untested balance/billing code)

EXEMPTIONS (documented in plan):
  - Generated code
  - Boilerplate entrypoints
  - Debug-only utilities
  - Third-party wrappers with no logic

ENFORCEMENT:
  - CI blocks merge below threshold
  - Coverage report posted on every PR
  - Exemptions reviewed quarterly
```

### 5. Build review checklists

**Code review checklist:**
- [ ] Correctness: edge cases, error paths, null/empty inputs
- [ ] Readability: names, control flow, no dead code
- [ ] Architecture: follows existing patterns, clean boundaries
- [ ] Security: input validated, secrets external, queries parameterized
- [ ] Performance: N+1 queries, unbounded loops, missing pagination

**Money review checklist:**
- [ ] Idempotency: double-submit produces same result
- [ ] Ledger: balance is a derived value, not a mutable field
- [ ] Reversibility: refund/rollback is a ledger operation
- [ ] Webhook: signature verified before any logic
- [ ] Error injection: provider failure leaves state unchanged

**Security review checklist:**
- [ ] Authentication enforced on every protected endpoint
- [ ] Authorization checked per resource, not globally
- [ ] Input validated at every system boundary
- [ ] Secrets in environment variables, not code
- [ ] SQL queries parameterized
- [ ] Output encoded for context (HTML, JSON, etc.)
- [ ] Rate limiting on public endpoints

**Data review checklist:**
- [ ] Migration has rollback script
- [ ] Schema change is backward-compatible or has a migration plan
- [ ] Irreversible operations have confirmation
- [ ] Data export produces correct, complete output

### 6. Maintain the risk inventory

Track in the plan:

```markdown
## Risk Inventory

| Area | Risk | Mitigation | Last verified |
|------|------|------------|---------------|
| Payment webhooks | Duplicate delivery | Idempotency key on every webhook | 2026-08-15 |
| Balance calculation | Race condition | Ledger pattern, serial writes | 2026-08-10 |
| User deletion | Cascade orphans | Soft delete, dry-run preview | 2026-07-28 |
```

Update after every incident or regression.

## Gotchas

- **Coverage is a floor, not a goal.** 80% coverage of bad tests is still bad. Focus on behavioral coverage: every rule has a named test. Test names should read like a specification.
- **Money coverage is strict.** Money-path code must be 100% tested for idempotency, error handling, and state consistency. No exemptions.
- **Gates without enforcement are suggestions.** Every gate must have an automated check in CI. If you can't automate it, document who signs off and how.
- **Review checklists rot.** Update checklists when you find a new class of bug. A checklist that misses a real bug is worse than no checklist.
- **Risk inventory is for the team.** Don't hide risks. An explicit risk you manage is safer than an implicit risk you ignore.
- **Plan is a living document.** Update it when scope changes, architecture changes, or you discover a new failure mode. Stale plans become noise.
- **Don't over-plan.** Feature of <100 lines with no money or security surface: one checklist item, not a full plan. The plan exists to prevent predictable failures, not to generate paperwork.

## References

- `specs/quality/plan.md` — current quality plan generated by this skill
- Architecture simplicity skill — patterns for staying lean
- Money path safety skill — idempotency, ledger, webhook rules
- Security hardening skill — OWASP, input validation, secret management
- Code review and quality skill — five-axis review process
- Testing discipline skill — test isolation, naming, DoD
- Verification before completion skill — evidence before claims

## Verification

- [ ] `specs/quality/plan.md` exists and is current
- [ ] Every gate has an automated check (CI or script)
- [ ] Coverage report proves ≥80% line, ≥70% branch
- [ ] Money-path lines verified at ≥95%
- [ ] Risk inventory is current (updated within last 30 days)
- [ ] Review checklists are used in every PR