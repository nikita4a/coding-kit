---
name: spec-mode
description: Domain skill. Spec Mode — structured spec-driven development. Use for multi-step features, before writing code, or when the user says 'spec mode', 'write a spec'.
---

# Spec Mode

## Overview

Spec Mode is a structured spec-driven development workflow. It launches the `spec-mode` CLI, then proceeds through four gated phases: SPECIFY, CLARIFY, PLAN, TASKS. Each phase produces artifacts in `specs/` and `steering/` directories, and each phase gates on human review before the next begins.

## When to Use

- Multi-step features that span several files or modules
- Before writing any code for a new capability
- When the user says "spec mode", "write a spec", or "let's spec this out"
- Architectural decisions that need explicit documentation
- Tasks that would take more than 30 minutes to implement

**When NOT to use:** Single-line fixes, typo corrections, or changes where requirements are unambiguous.

## The Gated Workflow

```
SPECIFY ──→ CLARIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT
   │           │          │        │          │
   ▼           ▼          ▼        ▼          ▼
 Human      Human      Human    Human      Human
 reviews    reviews    reviews  reviews    reviews
```

### Phase 1: SPECIFY

Launch `spec-mode` to create the initial specification. The CLI prompts for the feature name, then generates a structured spec file in `specs/`.

**Spec template (6 core areas):**

```markdown
# Spec: [Project/Feature Name]

## Objective
[What we're building and why. User stories or acceptance criteria.]

## Tech Stack
[Framework, language, key dependencies with versions]

## Commands
[Build, test, lint, dev — full commands]

## Project Structure
[Directory layout with descriptions]

## Code Style
[Example snippet + key conventions]

## Testing Strategy
[Framework, test locations, coverage requirements, test levels]

## Boundaries
- Always: [Run tests before commits, follow naming conventions, validate inputs]
- Ask first: [DB schema changes, adding dependencies, changing CI config]
- Never: [Commit secrets, edit vendor directories, remove failing tests]

## Success Criteria
[How we'll know this is done — specific, testable conditions]

## Open Questions
[Anything unresolved that needs human input]
```

**Surface assumptions immediately:**
```
ASSUMPTIONS I'M MAKING:
1. This is a web application (not native mobile)
2. Authentication uses session-based cookies (not JWT)
3. The database is PostgreSQL
— Correct me now or I'll proceed with these.
```

**Reframe instructions as success criteria:**
```
REQUIREMENT: "Make the dashboard faster"
REFRAMED:
- Dashboard LCP < 2.5s on 4G connection
- Initial data load completes in < 500ms
- No layout shift during load (CLS < 0.1)
```

**Output:** `specs/<feature-name>.md`

**Gate:** Human reviews the spec. Open questions must be resolved before proceeding.

### Phase 2: CLARIFY

With the approved spec, run `spec-mode clarify` to identify gaps, ambiguities, and implicit assumptions. This phase produces a steering document in `steering/`.

**Clarify checklist:**

1. **Ambiguous terms** — Flag every term that could mean different things to different people
2. **Missing constraints** — Performance budgets, supported browsers, accessibility targets
3. **Edge cases** — Empty states, error states, concurrent access, data races
4. **Dependency assumptions** — What external services must exist, what versions are required
5. **Scope boundaries** — Explicitly list what is NOT in scope
6. **Success criteria gaps** — Are the criteria specific, measurable, and verifiable?

**Output:** `steering/<feature-name>-clarify.md`

**Gate:** Human reviews the clarify document. Ambiguities resolved before planning.

### Phase 3: PLAN

Run `spec-mode plan` to generate the technical implementation plan. The plan lives in `steering/`.

**Plan template:**

```markdown
# Plan: [Feature Name]

## Architecture
[Major components, data flow, module boundaries]

## Build Order
1. [Foundation — scaffolding, types, data model]
2. [Core — primary business logic]
3. [Integration — wiring to existing systems]
4. [Polish — error handling, edge cases, observability]

## Risks & Mitigations
- [Risk]: [Mitigation]
- [Risk]: [Mitigation]

## Verification Checkpoints
- [After phase 1]: [What must pass]
- [After phase 2]: [What must pass]
- [After phase 3]: [What must pass]

## Files to Create/Modify
- [path/to/file] — [reason]
- [path/to/file] — [reason]
```

**Output:** `steering/<feature-name>-plan.md`

**Gate:** Human reviews the plan. Build order and risks must be approved.

### Phase 4: TASKS

Run `spec-mode tasks` to break the plan into discrete implementation tasks. Stored in `steering/`.

**Task format:**

```markdown
## Task: [Short description]

### Acceptance Criteria
- [Specific, testable condition]
- [Specific, testable condition]

### Files to Touch
- [path/to/file]

### Verify
- [Command to run or observation to make]

### Dependencies
- [Task name or "None"]
```

**Task rules:**
- Each task is completable in a single focused session
- Each task touches no more than ~5 files
- Tasks are ordered by dependency
- Each task has explicit, verifiable acceptance criteria

**Output:** `steering/<feature-name>-tasks.md`

**Gate:** Human reviews the task list. Tasks are then executed one at a time following test-driven development and incremental implementation.

## Artifact Structure

```
specs/
  <feature-name>.md          — Phase 1: specification

steering/
  <feature-name>-clarify.md  — Phase 2: clarifications
  <feature-name>-plan.md     — Phase 3: implementation plan
  <feature-name>-tasks.md    — Phase 4: task breakdown
```

## Keeping Specs Alive

- Update `specs/` when decisions change
- Update `steering/` when scope changes
- Commit spec and steering artifacts in version control
- Reference the spec and steering documents in PRs

## Red Flags

- Writing code without any written spec
- Implementing features not mentioned in any spec or task list
- Making architectural decisions without documenting them
- Skipping the CLARIFY phase because "it's obvious"
- Moving to TASKS before the human has approved the plan

## Verification

- [ ] Spec covers all six core areas (specs/)
- [ ] Clarify document addresses gaps and ambiguities (steering/)
- [ ] Plan defines build order, risks, and verification checkpoints (steering/)
- [ ] Tasks are discrete, ordered, and have acceptance criteria (steering/)
- [ ] Human reviewed and approved each phase gate
- [ ] Success criteria are specific, measurable, and testable
- [ ] Boundaries (Always/Ask First/Never) are defined