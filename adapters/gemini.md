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
`gemini -p "who are you and what do you know?"` — engineer agent answer.
`gemini -p "what do we know about <topic>"` — must try a base search first.