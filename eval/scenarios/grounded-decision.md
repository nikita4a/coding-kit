---
name: grounded-decision
skill: production-first-decisions
trap: the question "which tool/library to choose" requires web research and industry data, not an answer from your head
expect: the action plan includes web search / primary sources before a recommendation; "everyone does it this way" is measured
---

# Scenario: grounded decision

You are an agent on coding-kit. Skill: production-first-decisions.

## Request

"Which JS library should I pick for virtualizing a table with 100k rows?"

## Task

Describe the sequence of actions. Expectation: first web research (primary sources, at least 2), comparison against industry criteria — then a recommendation. An answer from your head without searching = scenario failure.