# Design: coding-kit v2 — "thin smart kit"

> Brainstorm 2026-08-19. Status: approved, in implementation.
> User decisions: (1) personal → public later, (2) "smartness" = all 5 axes, (3) thin kit trusts the harness, (4) memory → user profile.

## 1. Deference

The thin kit trusts the harness. For maximally distributed skills it relies on the harness — but since the kit runs in 4 environments (OMP, Antigravity, Hermes, Gemini CLI), part of those skills we still bundle into the kit for non-OMP environments.

## 2. Memory — separate from kits (user profile)

```
C:/Users/<user>/.memory/          ← physical memory (Wiki + db + engine)
C:/Users/<user>/Desktop/memory    → junction → ~/.memory (compatibility with kits' ../memory)
```

Git backup: `~/.memory` is a separate repository. Databases are generated (db/*.db gitignored).

## 3. Methodology: own card + obra depth

**Orchestrator: our `superpowers`** (5-phase cycle). As layers — pointed obra skills for each phase:

- **Plan** → `brainstorming`, `writing-plans`
- **Execute** → `executing-plans`, `dispatching-parallel-agents`, `subagent-driven-development`
- **Verify** → `verification-before-completion`, `requesting-code-review`, `receiving-code-review`
- **Debug** → `systematic-debugging`
- **Git** → `using-git-worktrees`, `finishing-a-development-branch`

**We don't take:** their `using-superpowers` bootstrap; their subagent skills are portable — we take them with memory adaptation (`~/...` → `../../.memory`).

## 4. Soul — AGENTS.md

Restructure into 5 sections (see below). The agent reads the soul; anything long goes into skills.

## 5. What we DON'T do (YAGNI)

- Our own runtime/MCP/daemons — the harness
- Semantics/vectors on top of FTS — personal volumes are covered by trigrams
- multimodel-judge panels — expensive, OMP subagents will cover it
- Translating bodies to English now, licenses — at publication

## 6. Roadmap

1. Import 11 obra skills (memory-path adaptation)
2. AGENTS.md → soul
3. OPS/BOOT consistency with the soul
4. Cleanup: my-skill, TDD skill duplicates
5. Trap-suite evals: scenarios + model run
6. Final verification

## 7. Readiness criteria

- All 4 environments find the memory (~/.memory) — smoke passed
- Obra skills load, memory paths work
- AGENTS.md reads as a "soul" — agent-vanilla answers just as meaningfully