---
name: learn
description: 'Use when the user wants the agent to teach itself a NEW reusable skill FROM this session/chat/procedure/URL — i.e. CONVERT what we just did into a reusable skill ("learn", "/learn", "turn this session into a skill", "make a skill from this workflow", "сделай скилл из этой процедуры", "teach yourself this procedure", "скилл из", "навык из"). The raw material is the current conversation or a named procedure. The raw material is what happened here, not a skill-format question (skill-authoring) and not a conclusion to remember (that is dev-wiki).'
---

# Learn — turn experience into a reusable skill

The Hermes `/learn` equivalent, kit-style: a prompt flow, not runtime. The agent writes
the SKILL.md itself. Format and quality rules: load `skill-authoring` before drafting.

## Flow

1. **Isolate the repeatable procedure.** From the source (this chat, a directory, a URL,
   notes): what did you actually do that a fresh session would have to rediscover?
   Write down the steps in order, with the "why" behind non-obvious decisions.
   - One-off facts are NOT skills → memory instead (`dev-wiki` / findings).
   - General knowledge the agent already has is NOT a skill (YAGNI).

2. **Trigger test before writing.** In a fresh session, would the description fire for the
   natural phrase a user would say? If no plausible trigger exists — stop, don't write it.
   The description is the only thing a future session sees (progressive disclosure).

3. **Draft SKILL.md** (rules: `skill-authoring`):
   - `name`: lowercase-hyphen slug, == folder name.
   - `description`: 1–1024 chars, trigger words first, «what it does + when».
   - Body: numbered imperative procedure, defaults (not menus), gotchas — the most
     valuable section. <500 lines; details go to `references/` with «read when X».

4. **Choose the location.**
   - Portable (any machine, any project) → kit `skills/<slug>/`, commit — subject to the
     kit gates: English, file-size, review. Propagates to every harness automatically
     (junctions/copies).
   - Machine/user-specific → the harness's user skills dir (e.g. `~/.claude/skills/`).
     Does NOT propagate (Gemini's junction sees only kit skills).

5. **Verify before claiming done.**
   - Frontmatter: delimiters, `name` == folder, description within limits.
   - Trigger test: pick the most natural trigger phrase; does the description match it?
   - Replay one real past case through the new skill; the steps must lead to the same
     outcome — ideally with fewer wasted moves.

## Gotchas

- Don't over-generalize: encode the procedure that exists, not the class of procedures.
- Russian belongs only in user-facing trigger words; skill content stays English.
- Scripts stay in `scripts/`, never inline blob in SKILL.md.
- File-size gate applies: SKILL.md soft 300 / hard 500 lines (`check_file_sizes.py`).
- A skill that was wrong once is fixed like code: edit + verify against the same case.