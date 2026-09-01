---
name: grill-me
description: 'Domain skill. Adversarial requirements interrogation: ask 15-50 questions before writing code. Covers edge cases, error handling, data flow, failure modes, state management, concurrency. Use for ANY new feature, system design, or non-trivial task before implementation begins.'
---

# Grill-Me — adversarial requirements interrogation

Domain skill. Activate BEFORE writing any code for a new feature, system design, or non-trivial task.

## Why

AI generates code instantly. The bottleneck is not code generation — it is specification quality. A 200-word spec yields good code on the first attempt. Vague specs yield code that gets rewritten five times. This skill forces thorough specification through systematic questioning before implementation.

Inspired by mattpocock/skills /grill-me (101k GitHub stars, May 2026): the most trending repo for making AI work *slower* — 45 minutes of questions before the first line of code — because it cuts total time 2-3x by getting code right the first time.

## Core principle

Do NOT write code. Do NOT propose solutions. ASK QUESTIONS until you understand the problem completely. Only after the user has answered enough questions to produce a complete specification, begin implementation.

## Protocol

### Phase 1: Scope and intent (5-10 questions)
- What is the core problem you are solving?
- Who is the user or stakeholder?
- What does "done" look like — concretely?
- What is explicitly OUT of scope?
- What constraints exist (time, budget, tech stack, team size)?

### Phase 2: Data and state (5-10 questions)
- What data flows in? Format, volume, frequency?
- What data flows out? Format, destination?
- Where is state stored? How long does it persist?
- What happens to state between restarts?
- What are the data ownership boundaries?

### Phase 3: Edge cases and failure (5-10 questions)
- What if input is missing, null, empty, or malformed?
- What if an external service is down, times out, or returns garbage?
- What if concurrent requests arrive simultaneously?
- What if the user does something unexpected?
- Which failure modes are acceptable? Which are not?

### Phase 4: Integration and contracts (5-10 questions)
- What external systems are involved?
- What APIs do you call? What APIs call you?
- What are the authentication and authorization boundaries?
- What backwards compatibility constraints exist?
- What monitoring or observability is needed?

### Phase 5: Non-functional (5-10 questions)
- What is the expected performance? Latency? Throughput?
- What is the security model? Threat surface?
- What is the deployment model?
- What compliance or regulatory requirements apply?
- Who owns this operationally after launch?

## Rules

1. **Ask one question at a time** — not a wall of questions. Wait for each answer before asking the next.
2. **Track coverage** — note which of the 5 phases are covered. Do not stop until all 5 have answers.
3. **Probe vague answers** — "it should be fast" becomes "what latency target? what throughput? under what load?"
4. **Surface hidden assumptions** — "you said 'user' — do you mean end-user, admin, or another service?"
5. **Never write code during questioning** — not even a sketch. The goal is understanding, not solutioning.
6. **Summarize before coding** — after all questions are answered, produce a concise spec summary. Get explicit user confirmation. THEN begin implementation.
7. **Adapt depth to task** — a one-line bug fix needs 2-3 questions. A new service needs 30-50. Scale accordingly.

## Antipatterns

- Asking all questions at once in a wall of text
- Skipping to implementation after 2-3 questions
- Accepting vague answers without probing
- Asking generic questions that do not depend on the user's specific context
- Hardcoding sensitive data (API keys, tokens) in the spec or code

## Differentiation from brainstorming

`brainstorming` is internal ideation — the agent explores design space on its own. `grill-me` is external interrogation — the agent extracts requirements from the user through systematic questioning. Use `brainstorming` for design exploration; use `grill-me` for requirements extraction before any design begins.