# ZCode (Z.ai) — Setup Guide (coding-kit)

> How to wire coding-kit into ZCode (Z.ai Agentic Development Environment & CLI).

## 1. What ZCode reads

- Global instructions: `~/.zcode/AGENTS.md` (and `~/.zcode/CLAUDE.md` for compatibility).
- Global skills: `~/.zcode/skills/` — directories with Hermes-compatible `SKILL.md`.
- Workspace instructions: `<project-root>/AGENTS.md`.
- Workspace skills: `<project-root>/.zcode/skills/`.

## 2. Install

### Step 1: Rules
Copy the kit router to `~/.zcode/AGENTS.md`:
```bash
cp <kit>/AGENTS.md ~/.zcode/AGENTS.md
```
Or on Windows PowerShell:
```powershell
Copy-Item "<kit>\AGENTS.md" "$env:USERPROFILE\.zcode\AGENTS.md"
```

### Step 2: Skills — junction (single source)
```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.zcode\skills" -Target "<kit>\skills"
```
On Linux/macOS:
```bash
ln -s <kit>/skills ~/.zcode/skills
```

### Step 3: Memory
Memory lives outside the kit: `~/.memory/` (Wiki + db-tools + research.db).
Rebuild indexes:
```bash
python ~/.memory/db-tools/build.py
```

### Step 4: Verify
In ZCode chat or CLI:
- Ask the agent to show its method (plan → TDD → implement → verify → report): superpowers, YAGNI, cross-chat memory via database.
- Ask it to search memory for X — must route through a database search (`search_all.py`), not answer from conversation.
