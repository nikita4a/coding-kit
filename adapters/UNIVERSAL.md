# Universal Adapter — coding-kit

> Developer kit: superpowers, YAGNI, TDD, cross-chat memory. For any agent that reads AGENTS.md and skills.

## Install (general principle)

Terminology: agents have a "skills dir" (progressive disclosure) and a "rules dir" (always loaded, e.g. ~/.claude/CLAUDE.md, AGENTS.md).

1. Rules: point the agent's rules file at `AGENTS.md` (or copy its content). Memory paths use the `~/.memory` convention — env `MEMORY_ROOT` overrides.
2. Skills: copy/link `skills/` into the agent's skills dir. Hermes-format SKILL.md, 36 skills.
3. Memory (external): `~/.memory/` — Wiki + db-tools engine + research.db. Kit and memory are separate: the kit is pure methodology, knowledge lives in the memory root.
4. Context monitor: `python scripts/context-monitor.py --check` every ~10 turns.

## Specific agents

### Claude Code / OMP
```bash
# rules: ~/.claude/CLAUDE.md — append the router
# skills: ~/.claude/skills/ — copy or junction
cp -r skills ~/.claude/skills/   # keeps per-skill dirs
```

### Gemini CLI
```bash
# rules: ~/.gemini/GEMINI.md
# skills: ~/.gemini/skills/ (Global tier) — junction recommended:
#   mklink /J ~/.gemini/skills <kit>/skills
```

### Hermes
```yaml
# rules: SOUL.md gets the kit soul (AGENTS.md content)
# skills: config.yaml → skills.external_dirs:
#   - <kit>/skills
```

### Antigravity
```bash
# rules: ~/AGENTS.md (user-level)
# skills: ~/.agents/skills/
```

## Verify

Ask the agent: "who are you and what do you know?" — it must answer: engineer agent, superpowers method, memory from the base. And "what do we know about X" must trigger a search, not memory.