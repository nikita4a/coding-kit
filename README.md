# coding-kit — Coding Agent OS

A portable agent-brain kit: methodology (superpowers), minimalism (YAGNI), cross-chat memory (SQLite FTS5), adversarial evals (trap-suite). 37 Hermes-compatible skills, English instructions, one command install.

Works in any environment that reads an agent rules file and SKILL.md skills: Claude Code, OMP, Gemini CLI, Antigravity, Hermes.

## What's inside

| Layer | File | Role |
|---|---|---|
| Soul | `AGENTS.md` | identity, red lines, routing (read first) |
| Contract | `OPS.md` | phases, memory hierarchy, gates, changelog |
| Runtime | `SKILL_RUNTIME.md` | context-size modes |
| Manifest | `profile.yml` | single source of truth: paths, skills |
| Skills | `skills/` | 37: always-on core + obra phase skills + domain |
| Memory engine | `memory/db-tools/` | build, search_all, findings, repomap (FTS5) |
| Evals | `eval/` | trap-suite (18 scenarios), task smoke (3 tasks, oracle-verified), trigger-eval (80 queries), schema-v1 store + trend |
| Adapters | `adapters/` | per-environment setup guides |

## Install (one command)

```bash
git clone https://github.com/oleg494/coding-kit.git coding-kit
cd coding-kit
python scripts/install.py
```

`install.py` creates `~/.memory/` (your private knowledge base — fixtures, engine link, indexes), idempotent, safe to re-run. Custom location: `MEMORY_ROOT=/x/y python scripts/install.py`.

## Wire your environment

Pick your agent from `adapters/`:

- **Claude Code / OMP**: rules → `~/.claude/CLAUDE.md`; skills → `~/.claude/skills/`
- **Gemini CLI**: rules → `~/.gemini/GEMINI.md`; skills → `~/.gemini/skills/` (junction recommended)
- **Antigravity**: rules → `~/AGENTS.md`; skills → `~/.agents/skills/`
- **ZCode (Z.ai)**: rules → `~/.zcode/AGENTS.md`; skills → `~/.zcode/skills/` (junction recommended)
- **Hermes**: soul → `SOUL.md`; `config.yaml` → `skills.external_dirs`

## Daily loop

```bash
python scripts/kitctl.py context               # every ~10 turns (0=ok 1=warn 2=critical)
python ~/.memory/db-tools/search_all.py "X"    # before "what do we know about X"
```

`scripts/kitctl.py` — one command for the kit's lifecycle:
- `doctor` — 10 self-diagnostic health checks.
- `tests` — run unit test suite via pytest.
- `gate` — file-size limits enforcement (`--ci`).
- `eval` — trap-suite (18 adversarial scenarios, dry-run validate by default).
- `tasks` — task smoke canary on 3 oracle-verified coding tasks (dry-run validate by default).
- `triggers` — 80-query trigger evaluation.
- `trend` — pass-rate history and failure evidence packets across runs.
- `warmup`, `checkpoint`, `context` — memory and session monitoring tools.

## Evals & Trend Loop

The kit includes an evidence-first evaluation harness:
- **Trap-suite (`eval/runner.py`)**: 18 adversarial scenarios testing adherence to superpowers, YAGNI, and security invariants.
- **Task Smoke (`eval/task_runner.py`)**: 3 real coding tasks verified by deterministic `verify.py` test oracles (no LLM judge). Each attempt runs in an isolated sandbox cloned fresh from `eval/tasks/repo-fixture` (default `--tries 2`). This serves as a smoke canary, not a statistical benchmark.
- **Trigger Evals (`eval/trigger_eval.py`)**: 80 queries testing skill activation routing.
- **Schema-v1 Results Store (`eval/results_io.py`)**: atomic append-only JSON storage under `eval/results/` with microsecond UTC timestamps, UUID `run_id`, separate `model` metadata, and standardized failure taxonomies.
- **Trend Reporting (`eval/trend.py`)**: summarizes newest runs by `(kind, model)`, reports baseline deltas, and produces structured Failure Evidence Packets with bounded trace tails for debugging.

## Where your data lives

The kit repo contains only methodology and engine. Your knowledge (Wiki posts, findings, indexes) lives in `~/.memory/` — personal, never committed, gitignored in every place it can appear.

## Platform note

Developed and tested Windows-first (CI also runs ubuntu-latest). The engine link
is a junction on Windows, a symlink elsewhere — `install.py` picks automatically.

## Credits

Phase-workflow skills (`brainstorming`, `writing-plans`, `executing-plans`,
`subagent-driven-development`, `using-git-worktrees`, `requesting-code-review`,
`receiving-code-review`, `verification-before-completion`, `systematic-debugging`,
`dispatching-parallel-agents`, `finishing-a-development-branch`) are derived from
[obra/superpowers](https://github.com/obra/superpowers) (MIT) © Jesse Vincent,
reworked and extended for coding-kit. See `skills/superpowers/LICENSE`.

## License


MIT — see LICENSE.