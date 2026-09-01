---
name: task-breakdown
description: "Domain skill. Task Breakdown — decompose work into actionable tasks with parallelization, estimation, dependency ordering, and acceptance criteria per task."
---

Break down vague or large-scope work items into a concrete, ordered, and estimable set of tasks. The output lives in `specs/tasks.md` and serves as the single source of truth for execution order, ownership, and validation.

## When to use

- A feature request lacks clear sub-steps
- A task spans multiple domains (backend, frontend, infra, research)
- You need to estimate effort before committing to a timeline
- Multiple agents or people need to work in parallel without conflict
- The work involves risky dependencies that must be sequenced

## Output format

**File:** `specs/tasks.md`

Each task has the following structure:

```markdown
## Task: <short imperative name>

**Owner:** <role or agent>
**Depends on:** <task names or `none`>
**Estimate:** <XS / S / M / L / XL>
**Parallelizable:** <yes / no / partial>

### Acceptance Criteria

- [ ] <observable, testable condition 1>
- [ ] <observable, testable condition 2>

### Notes

<optional context, gotchas, references>
```

## How to decompose

### 1. Collect inputs

- Product goal or feature request
- Known constraints (existing architecture, compliance, platform limits)
- Research documents or prior art

### 2. Identify independent work streams

Look for tasks that touch different:

- **Domains** (payments vs. media vs. auth)
- **Layers** (API vs. database vs. UI)
- **Owners** (agent A vs. agent B)
- **Risk profiles** (exploratory research vs. routine implementation)

Each independent stream can be its own parallelization group.

### 3. Map dependencies

Three types of dependency:

| Type | Meaning | Example |
|------|---------|---------|
| **Hard** | B cannot start until A finishes | Schema migration before query code |
| **Soft** | B can start on a stub, but full value needs A | UI before real API integration |
| **Info** | B needs a decision from A's output | Architecture choice before implementation |

Hard dependencies determine the critical path. Soft and info dependencies
allow partial parallelism.

### 4. Estimate effort

Use relative sizing. Do not convert to hours — the estimate is for ordering
and sequencing, not timesheets.

| Size | Scope | Typical content |
|------|-------|-----------------|
| XS | Trivial, < 1 unit | Rename, config change, one-file edit |
| S | Small, 1-2 units | Single feature in one file, simple test |
| M | Medium, 2-4 units | Cross-file change, new endpoint, moderate test suite |
| L | Large, 4-8 units | Multi-file feature, new module, schema + API + tests |
| XL | Very large, 8+ units | Cross-cutting concern, new subsystem, research spike |

If a task exceeds XL, it needs further decomposition.

### 5. Write acceptance criteria

Every criterion must be:

- **Observable** — someone can verify it without reading the code
- **Testable** — has a clear pass/fail signal
- **Atomic** — one condition per bullet

**Good:**
```markdown
- [ ] POST /api/orders returns 201 with valid order body
- [ ] Balance reflects the transaction in the ledger
- [ ] Webhook is retried on 5xx response from callback URL
```

**Bad:**
```markdown
- [ ] Payment works correctly
- [ ] Code is clean
- [ ] User is happy
```

### 6. Order the task list

Produce the final sequence in `specs/tasks.md`:

1. **Foundation first** — schema, config, shared types, infra
2. **High-risk early** — spike research, uncertain integration points
3. **Parallelizable streams** — group independent tasks together
4. **Integration last** — compose, test, and verify the whole

Use `---` section dividers between parallel groups. Tasks within a group
have no hard dependencies on each other.

```markdown
## Parallel Group 1 — Foundation

- [ ] Task: Define order schema
- [ ] Task: Set up payment provider stub

---

## Parallel Group 2 — Independent streams

- [ ] Task: Build order API
- [ ] Task: Implement ledger client
```

## Template

Use this minimal template when starting a new breakdown:

```markdown
# Task Breakdown: <Feature Name>

## Goal

<one-line description of what this breakdown achieves>

## Tasks

<!-- List tasks here, ordered by dependency, grouped by parallelization -->

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| <risk> | H/M/L | H/M/L | <plan> |
```

## Examples

### Example 1: Payment integration

```markdown
# Task Breakdown: Add Crypto Payment Rail

## Goal

Accept USDT (TRC-20) alongside existing Stars and ruble payments.

## Tasks

### Parallel Group 1 — Research

#### Task: Audit wallet integration contract

**Owner:** security
**Depends on:** none
**Estimate:** M
**Parallelizable:** yes

Acceptance Criteria:
- [ ] Access control reviewed: owner, pause, withdraw
- [ ] Upgrade mechanism identified (proxy or not)
- [ ] Known vulnerability classes checked (reentrancy, overflow)
- [ ] Report written to `research/crypto-audit.md`

#### Task: Select TRC-20 provider API

**Owner:** backend
**Depends on:** none
**Estimate:** S
**Parallelizable:** yes

Acceptance Criteria:
- [ ] Provider API documented with endpoints and auth
- [ ] Webhook format and signature scheme known
- [ ] Fee structure and settlement terms recorded

---

### Parallel Group 2 — Implementation

#### Task: Add USDT ledger account type

**Owner:** backend
**Depends on:** Audit wallet integration contract
**Estimate:** S
**Parallelizable:** no

Acceptance Criteria:
- [ ] New `USDT` currency type in ledger schema
- [ ] Migration adds `usdt_wallet_address` to user profile
- [ ] Balance query returns correct USDT amount

#### Task: Implement deposit webhook handler

**Owner:** backend
**Depends on:** Select TRC-20 provider API, Add USDT ledger account type
**Estimate:** M
**Parallelizable:** no

Acceptance Criteria:
- [ ] Webhook signature verified before processing
- [ ] Idempotency key deduplicates retries
- [ ] Ledger credits USDT amount on confirmed deposit
- [ ] User notified via Telegram on success
```

### Example 2: X-reply farm feature

```markdown
# Task Breakdown: Add Topic Monitoring to X-Farm

## Goal

Allow the X-reply system to monitor specific topic keywords (not just
specific accounts) and generate replies to matching posts.

## Tasks

### Task: Add topic keyword model

**Owner:** backend
**Depends on:** none
**Estimate:** S
**Parallelizable:** yes

Acceptance Criteria:
- [ ] `TopicKeyword` model with `keyword`, `is_active`, `created_at`
- [ ] CRUD API for managing keywords
- [ ] Keywords persisted to database

### Task: Extend X stream filter

**Owner:** backend
**Depends on:** Add topic keyword model
**Estimate:** M
**Parallelizable:** no

Acceptance Criteria:
- [ ] Stream consumes both account-based and keyword-based rules
- [ ] Keyword-matched posts enter the same reply pipeline
- [ ] Daily limit applies per keyword group
- [ ] Logs distinguish keyword-source vs account-source posts

### Task: Add keyword reply prompt variant

**Owner:** content
**Depends on:** Extend X stream filter
**Estimate:** S
**Parallelizable:** no

Acceptance Criteria:
- [ ] Prompt includes the matched keyword and post context
- [ ] Reply adds value to the thread (not just keyword-stuffed)
- [ ] Stylization matches the account's voice
```

## Anti-patterns

| Anti-pattern | Why it fails | Fix |
|-------------|-------------|-----|
| Single monolithic task | No parallelism, no visibility | Decompose into at least 3 sub-tasks |
| All tasks in series | Ignores independent streams | Find parallelizable groups |
| No acceptance criteria | Cannot verify completion | Write one observable condition per task |
| Hour-based estimates | False precision | Use relative sizing (XS-XL) |
| Orphan tasks with no owner | Nobody picks them up | Assign every task to a role or agent |
| Tasks that mix concerns | Confuses ownership | Split: one task = one concern |
| Skipping risk register | Surprises mid-project | Write risks before starting |

## Integration with other skills

- **agent-delegation** — tasks from this breakdown can be assigned to
  specific agents via `task` or `hub`.
- **spec-writing** — the `specs/tasks.md` output feeds into
  implementation specs.
- **progress-tracking** — task status (pending / in-progress / done /
  blocked) maps to a todo tracker.

## Checklist

Before marking a breakdown complete:

- [ ] Every task has a name, owner, estimate, and dependencies
- [ ] Acceptance criteria are observable and testable
- [ ] Parallelizable groups are identified and separated
- [ ] Hard dependencies define a clear critical path
- [ ] Risk register is filled for non-trivial features
- [ ] No task exceeds XL — oversized tasks are decomposed
- [ ] File is written to `specs/tasks.md`