---
name: design-documentation
description: "Domain skill. Design Documentation — create and maintain design documents"
---

# Design Documentation — SKILL

## Overview

Creates and maintains lightweight design documents at `docs/design/`. Every document
follows a template that captures context, decisions, and structure — not prose essays.
Documents are living: they update as the system evolves, and stale ones get a
`STALE: <date>` header.

## Template

```
# <Title>

## Context
Why this document exists, what problem it addresses, what constraints apply.

## Decision
Key architectural choices and their rationale.

## Structure
Diagrams, models, and links that describe the design.

## Status
[Proposed | Accepted | Deprecated | Superseded by <link>]
```

## What a design document covers

### C4 model — system context

- **Level 1 (System Context)**: a box for the system, boxes for external actors
  (users, services, data stores). Arrows show data flow, not control flow.
- **Level 2 (Container)**: deployable units (web app, worker, database, queue).
  Technology choices noted per container.
- **Level 3 (Component)**: major modules inside a container. Boundaries and
  interfaces matter; internal implementation details do not.
- **Level 4 (Code)**: optional — used only when a component's internal
  structure is non-obvious and critical.

Format: text-based diagrams (e.g. Mermaid `C4Context`, `ContainerDiagram`) so
they diff cleanly in code review.

### Sequence diagrams

Purpose: show the order of messages between actors/containers for a single
scenario. Not a state machine — one happy path and one notable failure path
per diagram.

- Include lifelines for every participant.
- Activation bars mark synchronous wait.
- `alt`/`opt`/`loop` fragments for branching and retries.
- `note` for external timeouts or side effects.

Format: Mermaid `sequenceDiagram` block embedded in the markdown document.

### Data models

- **Entity-Relationship** (logical): entities, attributes, and relationships.
  No foreign keys or storage details at this level.
- **Physical schema** (if needed): tables, columns, types, indexes, constraints.
  Generated from migrations — not hand-maintained.
- **JSON/API schemas**: request/response shapes for service boundaries.
  Prefer OpenAPI 3.x or a compact DSL.

Store ER diagrams as Mermaid `erDiagram` blocks. Physical schemas live in
migration files; the design doc links to them.

### ADRs (Architecture Decision Records)

Every non-trivial decision gets a short ADR file. Format:

```
# ADR-<N>: <Title>

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-<M>]

## Context
Forces, constraints, and alternatives considered.

## Decision
The chosen approach and why.

## Consequences
What becomes easier, harder, or impossible.
```

ADR files live at `docs/design/adr/ADR-<N>.md`. Number sequentially. A
`docs/design/adr/index.md` lists all ADRs with status.

## File layout

```
docs/
  design/
    README.md              — index of all design documents
    architecture.md         — system overview, C4 level 1-2
    <component>-design.md  — per-component design (C4 level 3+)
    adr/
      index.md              — ADR registry
      ADR-001-initial-stack.md
      ADR-002-payment-provider.md
      ...
```

## Workflow

1. **Propose**: create a branch, write the document, open a PR.
2. **Review**: stakeholders comment on the markdown diff. No diagram tool
   required — text-based diagrams are reviewable inline.
3. **Accept**: merge to `main`. The doc becomes the source of truth for that
   design area.
4. **Update**: when the implementation diverges from the doc, update the doc
   before (or as part of) the change. Stale docs accumulate trust debt.
5. **Deprecate**: add a `Superseded by` header and link to the replacement.
   Leave the old file in place for archaeology.

## Principles

- **Short over long.** A design document that fits in one screen is more likely
  to be read and kept current. Depth lives in referenced ADRs.
- **Diagrams as code.** Mermaid, PlantUML, or D2 — anything that generates from
  text and diffs cleanly. No binary diagram files.
- **One concern per document.** A document about payment processing does not
  also describe the notification system. Split.
- **Decisions, not descriptions.** The value of a design doc is the rationale
  behind the structure, not the structure itself. Code already describes the
  structure.
- **Alternatives matter.** Every ADR must list at least one alternative that was
  rejected and why. This prevents re-debating settled questions.

## Tools

- `docs-lookup` agent — fetch current documentation for libraries/frameworks
  referenced in design docs.
- `code-explorer` agent — trace existing code paths to inform the design.
- `architect` agent — review design documents for consistency and feasibility
  before PR.