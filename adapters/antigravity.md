# Antigravity IDE + Gemini — Setup Guide (coding-kit)

> How to wire the coding-kit into Antigravity IDE.

## 1. What Antigravity reads

- User-level instructions: `~/AGENTS.md` (home directory, applies to all workspaces).
- Skills: `~/.agents/skills/` — SKILL.md dirs.
- Workspace: `WORK/` is the typical opened folder; per-project AGENTS.md would go there.

## 2. Install

### Step 1: Rules
Copy the kit router to `~/AGENTS.md`:
```bash
cp <kit>/AGENTS.md ~/AGENTS.md
```
Adjust memory paths inside if your memory root is not `~/.memory` (env `MEMORY_ROOT` overrides).

### Step 2: Skills
```bash
mkdir -p ~/.agents/skills
cp -r <kit>/skills/* ~/.agents/skills/
```
Or keep a single source with a junction per skill.

### Step 3: Memory
Memory lives outside the kit: `~/.memory/` (Wiki + db-tools + research.db). Rebuild indexes:
```bash
python ~/.memory/db-tools/build.py
python ~/.memory/db-tools/build.py -r <project-root> -o ~/.memory/db/<name>.db
```

### Step 4: Verify
In the IDE ask: «кто ты и что умеешь?» — must answer: engineer agent, superpowers, YAGNI, cross-chat memory via database. Then ask «что мы знаем про X» — must run a search first.

## 3. What the agent does after install

```
STARTUP   read OPS.md → memory-warmup → context-monitor --check
QUESTION  known → search_all.py "X" → answer with file link
TASK      superpowers: plan → TDD → implement → verify → report
"write"   hierarchy: portable → ~/.memory/Wiki/; project → WORK/<proj>/docs/
```