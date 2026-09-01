---
name: ai-prompting
description: "Domain skill. AI Prompting — best practices for prompting AI coding agents. Use when crafting prompts for coding tasks, debugging agent output, or improving instruction quality. Covers clarity, context, constraints, examples, iterative refinement."
---

# AI Prompting — best practices for coding agents

Domain skill. Craft effective prompts for AI coding agents.

## Principles

### 1. Clarity
- State the goal explicitly — what should the output be?
- Specify the format: code, explanation, plan, review.
- Use concrete language, not vague directives.

### 2. Context
- Provide relevant background: project structure, conventions, constraints.
- Include file paths, existing patterns, dependency versions.
- Reference specific files or functions the agent should work with.

### 3. Constraints
- Define what NOT to do: don't add dependencies, don't refactor, don't touch certain files.
- Set quality gates: must pass tests, must follow style guide, must be under N lines.
- Specify the environment: language version, framework, OS.

### 4. Examples
- Show expected input/output pairs.
- Reference existing code in the project as a style guide.
- Provide a template if the output has a specific format.

### 5. Iterative Refinement
- Start broad, then narrow based on the agent's output.
- If the agent misunderstands, rephrase rather than repeat.
- Break complex tasks into smaller, sequential prompts.

## Prompt Template

```
## Goal
[One sentence: what should be accomplished]

## Context
- Project: [name, language, framework]
- Relevant files: [paths]
- Conventions: [style, patterns, rules]

## Constraints
- Do NOT: [forbidden actions]
- Must: [requirements]

## Output
[Format, structure, acceptance criteria]
```

## Anti-patterns

- Ambiguous instructions: "make it better"
- Missing context: the agent has to guess the project structure
- Over-constraining: contradictory or impossible requirements
- One-shotting complex tasks: expecting perfect output from a single prompt
- Repeating the same prompt: if it didn't work, change the approach

## Verification

After the agent produces output:
1. Does it match the specified format?
2. Does it respect all constraints?
3. Does it handle edge cases mentioned in the prompt?
4. If not, refine the prompt and retry.