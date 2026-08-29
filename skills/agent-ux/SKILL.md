---
name: agent-ux
description: Use when designing a dashboard feature that includes an AI assistant, copilot, automation, tool calls, recommendations, or agent-generated actions. Defines trustworthy states, user control, progress, approvals, editable outputs, recovery, and feedback without pretending the agent is human.
---

# AI Agent UX

Design the agent as a visible collaboration loop. The user should know what the agent can do, what it is doing now, what data it used, and how to correct or stop it.

## Workflow

1. **Define the job and boundary.** State the user's goal, the agent's capabilities, the data it may access, and actions it must not take. Do not imply certainty or human judgment.
2. **Map the lifecycle.** Design explicit states for first run, idle, composing, planning, waiting for approval, running a tool, waiting, completed, partially completed, failed, cancelled, and expired/stale results. Keep the user's context visible.
3. **Preserve user control.** Require clear confirmation before consequential or irreversible actions. Provide cancel, undo, edit, and retry paths where the operation allows them. Never hide a side effect behind a vague button such as `Continue`.
4. **Show useful progress.** Communicate the current operation, relevant data source or scope, and whether the agent is waiting on the user, a tool, or a long-running job. Avoid fake progress bars and noisy step-by-step narration.
5. **Make output editable.** Let users inspect, refine, copy, or apply generated content deliberately. Keep assumptions, uncertainty, citations, or affected records discoverable when they matter to the decision.
6. **Design recovery first.** For an error or incomplete result, say what happened, what was preserved, and the smallest next action: revise request, retry, choose another scope, or continue manually. Do not force a full restart when partial work is safe to keep.
7. **Handle feedback and data controls.** Make feedback purposeful, explain how it is used, and expose relevant history, privacy, data-source, and retention controls. Do not treat every click as approval or training feedback.
8. **Verify the complete state matrix.** Test keyboard access, focus management, narrow layouts, long responses, slow tools, duplicate submissions, permission denial, partial failure, and refresh/navigation during a run.

## Interaction defaults

- Use neutral, task-focused language; do not claim feelings or human understanding.
- Distinguish suggestion, preview, and applied change in both copy and styling.
- Keep the initiating user action and the resulting action name consistent.
- Put destructive or externally visible actions behind explicit, specific confirmation.
- Preserve drafts and partial results whenever doing so cannot create a misleading state.
- Use visible status text in addition to color, animation, or icons.

## Output before coding

Write a compact agent contract:

- user goal and allowed scope;
- data sources and permissions;
- lifecycle states;
- actions requiring confirmation;
- cancel/undo/retry behavior;
- failure and partial-success copy;
- one browser scenario that proves user control.

If the feature has no agent behavior, use `dashboard-design` and skip this skill.
