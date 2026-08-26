# Gemini CLI — Setup Guide (coding-kit)

## 1. What Gemini CLI reads

- Global instructions: `~/.gemini/GEMINI.md`.
- Skills: `~/.gemini/skills/` (recognized as the Global tier — per CLI internals).
- Settings: `~/.gemini/settings.json`.

## 2. Install

### Step 1: Rules
```bash
cp <kit>/AGENTS.md ~/.gemini/GEMINI.md
```

### Step 2: Skills — junction (single source)
```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.gemini\skills" -Target "<kit>\skills"
```
Kit updates appear in the CLI immediately — no copies to sync.

### Step 3: Memory
`~/.memory/` external to the kit. Warmup + search commands live in GEMINI.md.

### Step 4: Verify
`gemini -p "show your method for a non-trivial code task and search memory for <topic>"` — must give plan → TDD → implement → verify → report, and route the memory query through `python ~/.memory/db-tools/search_all.py "<topic>"`, not answer from conversation.