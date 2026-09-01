---
name: create-steering-documents
description: 'Domain skill. Create steering/*.md files — project foundation documents: constitution, principles, product, tech, context, patterns, structure, personas, glossary. Use when starting a new project, onboarding a team, establishing project conventions, or documenting architectural decisions. Cover project governance, design principles, technology choices, user personas, and domain terminology in a structured set of references.'
---

# Create steering documents

## Overview

Creates a `steering/` directory with 9 foundational documents that define the project's identity, constraints, and conventions. These are the reference layer — they outlive individual tasks and serve as the source of truth for new agents, team members, and architectural decisions.

## Steering document set

### 1. `steering/constitution.md` — Project governance

How the project is run. Defines decision-making authority, review processes, and escalation paths.

**Contents:**
- Decision-making hierarchy: who decides what (product, tech, design)
- Review and approval process for changes
- Roles and responsibilities
- Communication protocols (sync/async, channels)
- Escalation path for unresolved conflicts
- Release and deployment authority
- Handling of urgent changes versus planned work

**Template:**

```markdown
# Constitution: [Project Name]

## Decision authority
- Product decisions: [role/person]
- Technical decisions: [role/person]
- Design decisions: [role/person]
- Financial decisions: [role/person]

## Review process
- [What needs review, by whom, and when]
- [How to request a review]
- [Review turnaround expectations]

## Roles
- [Role name]: [responsibilities]

## Communication
- Daily sync: [time, channel]
- Async: [tool, expectations]
- Escalation: [path]

## Releases
- [Release cadence]
- [Who can deploy]
- [Rollback protocol]
```

---

### 2. `steering/principles.md` — Design and development principles

The values and rules that guide every decision. Principles are the slow-changing layer — revise only when experience proves them wrong.

**Contents:**
- Engineering principles (simplicity, testability, modularity, etc.)
- Product principles (user-first, data-informed, etc.)
- Design principles (consistency, accessibility, etc.)
- Decision-making principles (bias for action, disagree-and-commit, etc.)
- Trade-off hierarchy (what takes priority when principles conflict)

**Template:**

```markdown
# Principles

## Engineering
1. [Principle]: [explanation, one sentence]
2. [Principle]: [explanation, one sentence]

## Product
1. [Principle]: [explanation]

## Design
1. [Principle]: [explanation]

## When principles conflict
[Priority order or resolution process]
```

---

### 3. `steering/product.md` — Product vision and goals

The north star for every feature, task, and sprint. Product decisions are evaluated against this document.

**Contents:**
- Product vision (one sentence)
- Target audience and market
- Core value proposition
- Success metrics (KPIs, OKRs)
- Current goals and milestones
- Known non-goals (what we explicitly do not build)
- Competitive landscape

**Template:**

```markdown
# Product: [Project Name]

## Vision
[One sentence: what the world looks like when we succeed]

## Target audience
- Primary: [who]
- Secondary: [who]

## Core value proposition
[What problem we solve, how we solve it differently]

## Success metrics
- [Metric]: [target], [why it matters]

## Goals
- [Qx 202x]: [goal]
- [Qx 202x]: [goal]

## Non-goals
- [We do not build X]

## Landscape
[Key competitors or alternatives]
```

---

### 4. `steering/tech.md` — Technology stack and architecture

The technical foundation. Documented decisions prevent re-litigation of settled choices.

**Contents:**
- Language, framework, runtime versions
- Key libraries and dependencies
- Architecture overview (diagram or description)
- Infrastructure (hosting, CI/CD, databases, storage)
- Security model and authentication
- Integration points and APIs
- Data flow diagram or description
- Known technical debt

**Template:**

```markdown
# Tech: [Project Name]

## Stack
- Language: [name, version]
- Framework: [name, version]
- Database: [name, version]
- Infrastructure: [provider, services]

## Architecture
[Brief description or pointer to diagram]

## Key libraries
- [Library]: [purpose]

## Security
- Auth: [mechanism]
- Data: [encryption, access control]

## Integrations
- [External system]: [protocol, purpose]

## Technical debt
- [Item]: [impact, plan]
```

---

### 5. `steering/context.md` — Project context and constraints

The background that explains why decisions were made. New team members read this first.

**Contents:**
- Project origin story
- Key historical decisions and their rationale
- Business constraints (budget, timeline, team size)
- Technical constraints (legacy systems, platform limitations)
- Regulatory or compliance requirements
- Dependencies on external teams or systems
- Risks and mitigation strategies

**Template:**

```markdown
# Context

## Origin
[Why this project exists]

## Key decisions
- [Decision]: [rationale]

## Constraints
- Business: [constraint]
- Technical: [constraint]
- Regulatory: [constraint]

## Dependencies
- [External dependency]: [nature, risk]

## Risks
- [Risk]: [likelihood, impact, mitigation]
```

---

### 6. `steering/patterns.md` — Recurring patterns

Standardized solutions to recurring problems. A pattern is adopted when the third instance of the same problem appears.

**Contents:**
- Architectural patterns (layered, event-driven, etc.)
- Code patterns (repository, factory, strategy, etc.)
- Testing patterns (arrange-act-assert, test doubles, etc.)
- UI patterns (component composition, data flow, etc.)
- Anti-patterns to avoid (listed with replacements)

**Template:**

```markdown
# Patterns

## [Pattern name]
- Context: [when to use]
- Solution: [what to do]
- Example: [reference or snippet]
- Rationale: [why this pattern]

## Anti-patterns
- [Anti-pattern]: [problem] → [replacement]
```

---

### 7. `steering/structure.md` — Project structure

The directory layout and conventions for organizing code and assets.

**Contents:**
- Directory tree (top 2-3 levels)
- Naming conventions for files, directories, components
- Module boundaries and responsibilities
- Testing directory structure
- Asset organization (images, styles, data files)
- Configuration file locations

**Template:**

```markdown
# Structure

## Directory layout
```
project/
├── src/           # Source code
│   ├── module/    # Feature module
│   └── shared/    # Shared utilities
├── tests/         # Tests
├── docs/          # Documentation
└── config/        # Configuration
```

## Naming conventions
- Files: [convention]
- Directories: [convention]
- Components: [convention]

## Module responsibilities
- `src/module/`: [what it contains]
- `src/shared/`: [what it contains]
```

---

### 8. `steering/personas.md` — User personas and stakeholders

Who the project serves. Personas make abstract users concrete.

**Contents:**
- Primary user personas (name, role, goals, pain points)
- Secondary personas (admins, operators, integrators)
- Stakeholder personas (investors, executives, partners)
- Anti-personas (who we do not design for)
- User journeys or scenarios per persona

**Template:**

```markdown
# Personas

## [Persona name]
- Role: [job title]
- Goals: [what they want to achieve]
- Pain points: [what frustrates them]
- Scenario: [how they use the product]
- Success: [what "done" looks like for them]

## Anti-personas
- [Who we do not design for]: [why]
```

---

### 9. `steering/glossary.md` — Domain terminology

Shared vocabulary. Every domain-specific term, acronym, and internal name defined in one place.

**Contents:**
- Domain terms with definitions
- Acronyms and abbreviations
- Internal codenames
- Terms that are easily confused (distinguish them)
- Terms that are intentionally avoided (with replacement)

**Template:**

```markdown
# Glossary

| Term | Definition |
|------|-----------|
| [term] | [definition] |

## Avoided terms
| Term | Use instead | Reason |
|------|-------------|--------|
| [term] | [replacement] | [why] |
```

---

## Workflow

### First pass: bootstrap all 9 documents

1. **Create `steering/` directory** at the project root.
2. **Create each document** with the template above. Fill what you know; mark unknowns with `[TBD]`.
3. **Start with `context.md` and `product.md`** — these define the project's existence. Everything else follows from them.
4. **Then `principles.md` and `constitution.md`** — how the project is run.
5. **Then `tech.md` and `structure.md`** — the technical foundation.
6. **Then `personas.md` and `glossary.md`** — the human and vocabulary layer.
7. **`patterns.md` last** — patterns emerge from the first three instances of a problem; early documents are sparse and grow over time.

### Ongoing maintenance

- **Update `context.md`** when a new constraint or dependency is discovered.
- **Update `product.md`** when goals shift or new metrics are adopted.
- **Update `tech.md`** when a dependency is added or removed.
- **Update `glossary.md`** whenever a new term enters the conversation.
- **Update `patterns.md`** when a new pattern is adopted (third instance rule).
- **Update `personas.md`** when user research reveals a new persona.
- **Update `constitution.md`** only when the process changes — rarely.
- **Update `principles.md`** only when a principle is proven wrong — very rarely.
- **Update `structure.md`** when the directory layout meaningfully changes.

### When to reference

- **New agent onboarding**: reference all steering docs at the start of a session.
- **Architecture decision**: reference `tech.md`, `principles.md`, `patterns.md`.
- **Feature prioritization**: reference `product.md`, `personas.md`.
- **Code review**: reference `principles.md`, `patterns.md`, `structure.md`.
- **Disagreement**: reference `constitution.md` (who decides), `principles.md` (what we value).
- **Terminology confusion**: reference `glossary.md`.
- **Onboarding a person**: reference `context.md`, `constitution.md`, `product.md`.

---

## Gotchas

- **Do not over-write.** A steering document is a reference, not a novel. Keep each file under 200 lines; use templates as starting points, not constraints.
- **Do not skip the context document.** Without context, every decision reads as arbitrary. The rationale is more important than the decision itself.
- **Do not let steering documents rot.** A document that contradicts reality is worse than no document. Update or delete it.
- **Do not gate work on perfect steering documents.** Bootstrap from what you know; fill gaps as they become relevant. Done is better than perfect.
- **Do not duplicate information.** If the same fact belongs in two documents, pick one and cross-reference. `context.md` is the canonical home for rationale.
- **Do not make steering documents a build artifact.** They are human-readable references. No code should depend on their content.
- **Do not version-control empty steering documents.** Create only the ones that have content. Skeletal files with "[TBD]" everywhere are a signal to wait.
- **Apply YAGNI.** Create `steering/` only when the project has at least two people working on it or is expected to live longer than a month. A solo prototype does not need steering documents.

## Verification checklist

- [ ] `steering/` directory exists at project root
- [ ] All 9 documents created with template content
- [ ] `context.md` explains why the project exists
- [ ] `product.md` defines vision, goals, and metrics
- [ ] `principles.md` states engineering and product values
- [ ] `constitution.md` defines decision authority
- [ ] `tech.md` documents stack and architecture
- [ ] `structure.md` shows directory layout and conventions
- [ ] `personas.md` describes primary users
- [ ] `patterns.md` documents recurring solutions
- [ ] `glossary.md` defines domain terms
- [ ] Each document is cross-referenced where relevant
- [ ] No outdated or contradictory information across documents
- [ ] Documents are under 200 lines each