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
| Evals | `eval/` | trap-suite: 18 scenarios + runner, trigger-eval (80 queries) |
| Adapters | `adapters/` | per-environment setup guides |

## Install (one command)

```bash
git clone <this-repo> coding-kit
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

```
python scripts/kitctl.py context               # every ~10 turns (0=ok 1=warn 2=critical)
python ~/.memory/db-tools/search_all.py "X"    # before "what do we know about X"
```

`scripts/kitctl.py` — one command for the kit's lifecycle: `install`,
`doctor` (10 self-diagnostic checks), `gate`, `eval`, `triggers`, `tests`,
`warmup`, `checkpoint`, `context`.

## Where your data lives

The kit repo contains only methodology and engine. Your knowledge (Wiki posts, findings, indexes) lives in `~/.memory/` — personal, never committed, gitignored in every place it can appear.

## License

MIT — see LICENSE.