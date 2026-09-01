---
name: requirements-engineering
description: 'Domain skill. Requirements Engineering — capture, clarify, and validate requirements'
---

# Requirements Engineering

---

## Overview

Requirements Engineering (RE) is the disciplined process of establishing what a system must do and the constraints under which it must operate. RE transforms ambiguous stakeholder needs into precise, testable specifications that drive design, implementation, and verification.

---

## Five-Phase Process

### 1. Elicitation

Gather raw needs from stakeholders, users, documents, and domain analysis.

**Techniques:**
- Stakeholder interviews and workshops
- Document analysis (existing specs, contracts, logs)
- Observation and ethnography
- Prototyping and mockups
- Surveys and questionnaires
- Reverse engineering legacy systems

**Inputs:** Business goals, user personas, problem statements, existing systems
**Outputs:** Raw stakeholder needs list, elicitation transcripts, glossary of domain terms

### 2. Analysis

Structure, prioritise, and resolve conflicts in the raw needs. Detect gaps, ambiguities, and inconsistencies.

**Activities:**
- Categorise and group needs by feature or subsystem
- Prioritise (MoSCoW, Kano model, value/effort matrix)
- Detect conflicts and negotiate trade-offs
- Feasibility assessment (technical, schedule, budget)
- Risk identification tied to requirements
- Derive implied requirements from stated goals

**Inputs:** Raw needs list, domain glossary, constraint catalogue
**Outputs:** Prioritised requirement candidates, conflict log, risk register, feasibility notes

### 3. Specification

Write precise, unambiguous, verifiable requirements in a structured format.

**Types:**
- **Functional requirements:** What the system does (behaviour, data, interfaces)
- **Non-functional requirements:** Quality attributes (performance, security, usability, scalability, reliability)
- **Constraints:** Design decisions, platform, regulatory, standards

**Writing rules (per IEEE 830 / ISO 29148):**
- One requirement per statement
- Clear subject, action, object, condition
- Use consistent terminology from the glossary
- Avoid vague terms: "user-friendly", "fast", "robust", "efficient"
- Prefer "shall" for mandatory, "should" for desirable, "may" for optional
- Each requirement must be uniquely identified and traceable

**Inputs:** Prioritised candidates, risk register, conflict log
**Outputs:** Requirements specification document, traceability matrix

### 4. Validation

Confirm that requirements correctly represent stakeholder intent and are feasible.

**Methods:**
- Reviews and walkthroughs (peer, stakeholder, expert)
- Prototyping to validate understanding
- Acceptance criteria definition (Given/When/Then, Fit criteria)
- Formal inspections of requirement statements
- Checklist-based validation (completeness, consistency, testability)

**Validation checklist:**
- [ ] Complete — no missing features or scenarios
- [ ] Consistent — no contradictory statements
- [ ] Unambiguous — single interpretation
- [ ] Testable — objective pass/fail criteria exist
- [ ] Feasible — technically achievable within constraints
- [ ] Traced — linked to source and downstream artefacts
- [ ] Modifiable — structured for change without cascade

**Inputs:** Draft specification, traceability matrix, stakeholder list
**Outputs:** Signed-off requirements baseline, validation report, issue log

### 5. Management

Control changes, maintain traceability, and keep requirements alive throughout the lifecycle.

**Practices:**
- Baseline management and version control
- Change control board (CCB) and impact analysis
- Bidirectional traceability (source → spec → design → test)
- Requirements status tracking (proposed → approved → implemented → verified)
- Tool support (requirements management systems, issue trackers, wikis)

**Inputs:** Approved baseline, change requests, test results
**Outputs:** Change log, impact analysis reports, status dashboard, updated specification

---

## Quality Criteria

| Criterion | Definition | Check |
|---|---|---|
| Correct | Accurately reflects stakeholder intent | Validated against source |
| Unambiguous | One interpretation, no vagueness | Reviewed by two readers |
| Complete | No missing conditions, scenarios, or outputs | Coverage analysis |
| Consistent | No contradictions within or across requirements | Automated conflict scan |
| Testable | Pass/fail conditions observable | Acceptance criteria defined |
| Feasible | Achievable within cost, schedule, technology | Technical assessment |
| Necessary | Eliminates gold-plating | Trace to value or risk |
| Verifiable | Evidence of satisfaction can be collected | Test or inspection plan |
| Prioritised | Relative importance assigned | MoSCoW or ordinal rank |
| Atomic | Single concern per statement | Sentence-level review |

---

## Outputs Artefacts

| Phase | Artefact | Description |
|---|---|---|
| Elicitation | Needs catalogue | Raw unstructured stakeholder statements |
| Elicitation | Domain glossary | Consistent terminology and definitions |
| Analysis | Prioritised backlog | Ranked requirement candidates |
| Analysis | Conflict log | Resolved and open trade-off decisions |
| Specification | SRS document | Structured requirements specification |
| Specification | Traceability matrix | Source → requirement → test links |
| Validation | Baseline specification | Reviewed and signed-off specification |
| Validation | Validation report | Findings, discrepancies, sign-off |
| Management | Change log | History of all change requests and decisions |
| Management | Status dashboard | Live status of every requirement |

---

## Cross-References

- **System Design:** Requirements are the input to architecture and component design.
- **Verification & Validation:** Test cases are derived from requirements acceptance criteria.
- **Agile Development:** User stories are lightweight requirements; acceptance criteria are validation.
- **Technical Debt:** Poor requirements (ambiguous, incomplete) are a primary source of technical debt.
- **Risk Management:** Requirements risks (volatility, misinterpretation) feed the project risk register.
- **Quality Assurance:** Non-functional requirements define the quality attributes QA validates.
- **Change Management:** Requirements changes trigger impact analysis before approval.
- **Stakeholder Communication:** The SRS is the contract between stakeholders and the development team.

---

> **Domain skill.** This document is part of the requirements-engineering skill kit. Use it as a process reference, not a rigid methodology — adapt formality to project context.