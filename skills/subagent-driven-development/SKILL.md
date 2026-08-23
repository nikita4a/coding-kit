---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Execute plan by dispatching a fresh implementer subagent per task, a task review (spec compliance + code quality) after each, and a broad whole-branch review at the end.

**Why subagents:** You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task. They should never inherit your session's context or history — you construct exactly what they need. This also preserves your own context for coordination work.

**Core principle:** Fresh subagent per task + task review (spec + quality) + broad final review = high quality, fast iteration

**Narration:** between tool calls, narrate at most one short line — the
ledger and the tool results carry the record.

**Continuous execution:** Do not pause to check in with your human partner between tasks. Execute all tasks from the plan without stopping. The only reasons to stop are the four named below, or all tasks complete. "Should I continue?" prompts and progress summaries waste their time — they asked you to execute the plan, so execute it.

**Rulings, not stalls.** A running plan does not wait on a human. Conflicts,
ambiguities, plan defects, a cap you would have asked to exceed — decide
them. The spec is the binding authority, the plan is its argument, and your
judgment settles what neither answers. Record every decision in the ledger as
`Ruling: <what you decided> — <why> — <what it costs if wrong>`, and keep
going. A wrong ruling costs rework your human partner can see and undo; a
session parked on a question costs their whole day and buys nothing.

Four things stop you, and only these: an irreversible or destructive
operation; a security-sensitive action; a side effect outside this worktree
that norms say you ask about first (a merge, a push to a shared branch, a
publish); and a plan so broken that every path forward is a guess. For those,
stop and ask.

## When to Use

Same session as executing-plans, but: fresh subagent per task (no context
pollution), task review after each (spec + quality), broad review at the
end, faster iteration.

A worked end-to-end example lives in
`references/example-workflow.md` — read it once before your first dispatch.

## Setup

Ensure the work happens in an isolated workspace: use
using-git-worktrees to create one or verify the existing one.
Never start implementation on a main/master branch without your human
partner's explicit consent.

Conversation memory does not survive compaction. In real sessions,
controllers that lost their place have re-dispatched entire completed task
sequences — the single most expensive failure observed. Track progress in
a ledger file, not only in todos.

- Each plan owns a workspace directory: `<repo-root>/.superpowers/sdd/<plan-basename>/` (git-ignored) — home to
  every artifact for THIS plan: ledger, briefs, reports, review packages.
  Another plan's directory is never yours to read or write.
- Ledger at `<workspace>/progress.md`; first line names the plan file.
  Tasks with `Task <N>: complete` are DONE — resume at the first without
  one; a task ending in a fix round is mid-loop. A ledger naming another
  plan is not yours — leave it, start fresh.
- Create the ledger with its identity as the first line:
  `# SDD ledger — plan: <plan file path>`.
- The ledger is your recovery map: the commits it names exist in git even
  when your context no longer remembers creating them. After compaction,
  trust the ledger and `git log` over your own recollection.
- `git clean -fdx` will destroy the workspace (it's git-ignored scratch); if
  that happens, recover from `git log`.

Read the plan once, note its context and Global Constraints, and create a
todo per task. If the plan names a Spec, read that too: the spec is the
authority the plan argues from, and conflicts inside the plan resolve
against it. A plan with no reachable spec gets a ledger note saying so —
rulings made without one are provisional.

Before dispatching Task 1, scan the plan once for conflicts — tasks that
contradict each other or the Global Constraints; plan-mandated things the
review rubric treats as defects. Output is a table in the ledger: one row
per task pair sharing a file/interface (produces vs consumes), one row per
task (do its own tests agree with its own code). "The scan is clean"
without those rows is not a scan you ran. Rule on every finding against
the plan text that mandates it — the spec is the binding authority, the
plan is its argument — record each ruling beside its row, and dispatch
Task 1. The review loop remains the net for conflicts that only emerge
from implementation.

## Model Selection

Use the least powerful model that can handle each role:
- Mechanical implementation (isolated functions, complete spec, 1-2 files,
  plan text contains the code) → cheap tier.
- Integration and judgment (multi-file, debugging, prose specs) → standard
  tier; mid-tier is the floor for reviewers.
- Architecture/design and the final whole-branch review → most capable model.
- Fix-loop escalation (rounds 4-5) → at least one tier above the stuck
  implementer.

**Always specify the model explicitly when dispatching.** An omitted model
inherits your session's model — often the most capable and most expensive.

**Turn count beats token price:** cheapest models routinely take 2-3× the
turns on multi-step work, costing more overall.

## The Task Loop

**Batch small same-shape work.** When the plan lists several tasks that are
each a small, independent edit of the same kind — the same one-line fix,
constant change, or field addition repeated across files — do not dispatch
one subagent per task. Compose ONE dispatch brief listing every file and
its change, send the whole batch to a single subagent, and review its diff
as one unit. Reserve one-dispatch-per-task for work that needs its own
judgment, its own tests, or its own review surface.

Everything you paste into a dispatch prompt — and everything a subagent
prints back — stays resident in your context for the rest of the session
and is re-read on every later turn. Hand artifacts over as files.

**Waiting on dispatched subagents:** keep working while you have local work
(ledger updates, next review package, reading reports). When genuinely idle,
wait in bounded stretches (5-10 minutes where the platform allows), posting
one status line and reconciling live children between stretches — a stuck
child is noticed in minutes, not at session end.

### 1. Dispatch the implementer

Record BASE (`git rev-parse HEAD`) before dispatching — the review package
and fix-round diffs need it.

- **Task brief:** before dispatching, run this skill's
  `scripts/task-brief PLAN_FILE N` — it extracts the task's full text to a
  uniquely named file and prints the path. The dispatch contains: (1) one
  line on where the task fits; (2) the brief path — "read this first, it is
  your requirements, use exact values verbatim"; (3) interfaces/decisions
  from earlier tasks the brief cannot know; (4) your resolution of
  ambiguities you noticed; (5) the report-file path and contract. Exact
  values live only in the brief; never make a subagent read the whole plan.
- A dispatch prompt describes one task, not session history: no accumulated
  prior-task summaries. A fresh subagent needs its task, the interfaces it
  touches, and the global constraints. Nothing else.
- The dispatch carries the no-subagents contract (it is in the implementer
  template): the implementer never dispatches subagents — not helpers, and
  never a reviewer. Review arrives from you, after the report.
- If an earlier task parked a finding in the area this task touches, carry
  a pointer to that ledger entry in the dispatch.
- Record the implementer's agent identity from the dispatch result —
  fix-loop rounds 1-3 resume this agent.
- Never dispatch multiple implementation subagents in parallel (conflicts).

Write the brief inline: task, acceptance, workspace paths, base commit.

### 2. Handle the report

Implementer subagents report one of four statuses. Handle each appropriately:

**DONE:** Generate the review package: save `git diff <BASE> HEAD` to the
workspace, pass the path to the task reviewer.

**DONE_WITH_CONCERNS:** Read the concerns first. Correctness/scope doubts —
address before review; observations — note and proceed.

**NEEDS_CONTEXT:** provide it and re-dispatch.

**BLOCKED:** assess the blocker: context → re-dispatch same model with more
context; needs reasoning → more capable model; too large → split the task;
plan wrong → rule on the correction, ledger it, re-dispatch with the ruling.
Never force an unchanged retry on a stuck implementer. Answer mid-task
questions clearly and completely.

### 3. Review the task

Per-task reviews are task-scoped gates. The broad review happens once, at the
final whole-branch review. Never skip the task review, and never accept a
report missing either verdict — spec compliance AND task quality are both
required. Implementer self-review never replaces the task review; both are
needed.

- Hand the reviewer its diff as a file: `git diff <BASE> HEAD` saved to the
  workspace, path passed in the dispatch (BASE = the commit recorded before
  dispatching — never `HEAD~1`, which truncates multi-commit tasks). The
  output never enters your own context; the reviewer reads it in one call.
  Never dispatch a task reviewer without a diff file.
- **Reviewer inputs:** three paths — the same brief file, the report file,
  and the review package — plus the global-constraints block (attention
  lens): copy the binding requirements verbatim from the plan's Global
  Constraints or spec. The reviewer's template already carries process
  rules; the block is for what THIS project's spec demands.
- Do not pre-judge findings — never instruct a reviewer to ignore or not
  flag an issue. If the prompt contains "do not flag," "at most Minor," or
  "the plan chose" — stop: you are pre-judging. Let the reviewer raise it;
  adjudicate in the review loop.
The reviewer may report "⚠️ Cannot verify from diff" items (requirements in
unchanged code or spanning tasks). Resolve each yourself before completing
the task; a confirmed gap is a failed spec review — it enters the fix loop.

Write the review brief inline: review-package path, spec section, scope.

### 4. The fix loop

The loop triggers when the review reports spec ❌, any Critical or Important
finding, or a ⚠️ item you confirmed as a real gap.

Before the loop starts, two routes leave it immediately:

- Record Minor findings in the progress ledger as you go
  (`Task <N>: minor (deferred): <one-liner>`), and point the final
  whole-branch review at that list so it can triage which must be fixed
  before merge. A roll-up nobody reads is a silent discard. Minor findings
  never enter the loop.
- A finding labeled plan-mandated — or any finding that conflicts with
  what the plan's text requires — is yours to rule on: weigh the finding
  against the plan text, decide with the spec as the binding authority, and
  ledger the ruling before you act on it. Do not dismiss the finding because
  the plan mandates it, and do not dispatch a fix that contradicts the plan
  without a recorded ruling.
Everything else enters the loop. A fix round is one fix dispatch plus one
scoped re-review. Five rounds maximum per task:

**Rounds 1-3 — resume the original implementer.** Send it the open findings
verbatim; its context is intact (task, code, its own choices). If the
harness cannot message a live subagent, dispatch a fresh implementer with
the brief path, report-file path, and findings — the report file is the
persistent memory either way.

**Rounds 4-5 — fresh implementer on a more capable model** (per Model
Selection), framed: "A prior implementer attempted this task [N] times;
you own it now. Read the report file for what was tried."

**Every round:** the implementer fixes, re-runs the covering tests, appends
its fix report to the report file; re-dispatch the reviewer once the report
has tests + command + output. Name the covering test files — a one-line fix
does not need the whole suite.

**The re-review is scoped:** `git diff FIX_BASE HEAD` saved to the workspace
(FIX_BASE = head the previous review saw), dispatched with findings, brief,
report, diff path. The re-reviewer verdicts each finding ADDRESSED or NOT
ADDRESSED and flags new breakage in the fix diff only. Out-of-scope
observations go to the ledger as deferred minors — they never extend the loop.

**After each round,** append to the ledger:
`Task <N>: fix round <R>/5 (<X> addressed, <Y> open — <finding one-liners>; commits <a7>..<b7>)`

Never fix findings yourself in the controller session — your context stays
clean for coordination, and controller fixes skip review.

**The breaker.** When round 5's re-review still leaves findings open, stop
dispatching. Adjudicate each open finding yourself — you hold the plan and
the cross-task context the reviewer lacks:

- **The reviewer is wrong, or the point is contestable:** park it —
  `Task <N>: parked — <finding> — Ruling: <why the code stands>`. The final
  review sees both sides.
- **Real, but nothing downstream builds on it:** park it the same way, with
  a ruling that says it's real and deferred.
- **Real and load-bearing** (a later task builds on it, or it reveals a
  plan defect): rule on the smallest change that unblocks the dependent
  work, ledger `Task <N>: Ruling: <finding> — <decision and why>`, and
  carry it into the next dispatch. Stop only when the defect leaves every
  path forward a guess.

Adjudicate only at the cap. Adjudicating earlier to end a loop is
pre-judging with a different name. Every adjudication is a ledger entry —
a silent discard is forbidden.

### 5. Complete the task

When the review is clean — or every finding parked with a ruling at the cap
— append the ledger completion line (`Task <N>: complete (commits
<base7>..<head7>[, <K> parked])`), mark the todo, move on. Never advance
with open Critical/Important issues that are neither fixed nor parked.

## Final Review

The final whole-branch review gets a package too: save
`git diff <MERGE_BASE> HEAD` (e.g. `git merge-base main HEAD`), pass its
path in the dispatch, run it on the most capable model via the
requesting-code-review skill, and point it at the ledger's deferred-minor
and parked lines for merge-blocking triage.

If the final review returns findings: dispatch ONE fix subagent with the
complete list (per-finding fixers rebuild context and re-run suites —
more expensive than all tasks combined), then exactly one scoped re-review.
Adjudicate residual findings as in the breaker. There is no second fix
wave — residual load-bearing findings surface to your human partner when
finishing-a-development-branch presents the options.

## Finish

Collect every ledger line containing `Ruling:` into your final message
under "Rulings I made", in order, each with what it costs if wrong. The
list is exhaustive — a ruling that dies with the workspace was a decision
made in secret.

When the final review is clean and fixes merged, delete this plan's
workspace (`rm -rf <workspace>`) — git history is the record now. Then use
finishing-a-development-branch.

## Common Rationalizations

Full table: `references/rationalizations.md`.
