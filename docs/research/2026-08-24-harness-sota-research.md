# coding-kit: ресерч SOTA-практик для улучшения (workflowz, 2026-08-24)

Метод: 4 scout-агента (модель ox-alpha) по измерениям evals / self-improvement / memory-context / orchestration-CI → 30 находок → adversarial-верификация топ-14 (подтверждено 12, отклонено 2) → синтез + completeness-critic (8 слепых зон).


## Приоритетные рекомендации (синтез, верифицированные источники)

### P1 [6h] Rolling-baseline regression check, warn-not-block (no frozen thresholds)
- Источники: https://laoujin.github.io/Atlas/research/2026-06-04-evals-how-do-you-know-your-ai-works-session-blueprint/evals-in-ci-cd; https://github.com/metehanulusoy/model-regression-detection
- Что делать: trend.py must never gate on a fixed pass-rate threshold (LLM-judge scores are too noisy; the verified survey consensus). Commit per-kind rolling baselines to `eval/baselines/*.json`; compare the newest run against baseline in percentage-point deltas, WARNING inside a noise band (~≤3pp) and CRITICAL above ~8pp — but keep it warn-not-block because the kit's 3 tasks and 18 traps are far below the 100–200 examples/route a Welch t-test needs for a hard statistical block. Keep deterministic doctor.py/trap checks as the only always-block tier (the cheapest cascade level); reserve LLM-judge + full benchmark for nightly. Use stable exit codes throughout (task_runner already exits 1; adopt 2=block later).
- Отношение к плану 2026-08-24: extends Task 4 (trend.py); requires Task 2 payloads to carry per-scenario verdict arrays (they already do — just keep them)

### P1 [6h] Sandbox the CI executor: read-only repo, stripped env, disposable dir
- Источники: https://github.blog/ai-and-ml/generative-ai/under-the-hood-security-architecture-of-github-agentic-workflows/
- Что делать: Fix Task 5's live leg before any real executor runs: the plan's YAML hands an arbitrary EXECUTOR the writable checkout and the runner's full env (i.e. the agent gets API keys). Run the ubuntu leg's live step in a `container:` job with the repo mounted read-only and a tmpfs writable surface, and route any model traffic through an env-stripping launcher (whitelist of vars) rather than the agent env. On the Windows local leg there is no Windows Sandbox (Home edition) and Docker/WSL2 is friction, so the realistic v1 is the subprocess-level stripped-env into the existing temp-dir copy — which delivers ~2/3 of the value. Skip GH's safe-outputs MCP and firewall-container pieces until the kit grows a real write path.
- Отношение к плану 2026-08-24: corrects Task 5's workflow YAML; complements Task 3's temp-dir sandbox design

### P1 [8h] SkillOpt acceptance gate: hold-out improvement + rejected-edit buffer + edit-size budget
- Источники: https://arxiv.org/abs/2605.23904
- Что делать: Ride the plan's propose→review→merge loop with SkillOpt's acceptance rule instead of an open-ended 'propose edits, human merges' ritual: a proposal for SKILL.md/AGENTS.md/OPS.md becomes mergeable only if a held-out split of the eval (trap/task items not used to generate the proposal) strictly improves versus the last accepted revision; keep a stdlib JSONL rejected-edit buffer so an already-failed edit is never re-proposed; cap edit size (e.g. delta ≤ 10–15% of the target file's lines) so evolution cannot balloon files — this is the durable fix for the size-gate drift, not one-off extraction. All of it is a policy in trend.py + results_io.py: zero GPU, zero deps. Do NOT adopt SkillOpt's opt-loop machinery or PyPI package.
- Отношение к плану 2026-08-24: extends Task 4 (proposal flow) and Task 6 (size discipline); new decision JSONL sibling in Task 1's store

### P2 [4h] Pass@k retries + failure taxonomy + time/cost columns in task scoring
- Источники: https://github.com/Aider-AI/aider/tree/main/benchmark
- Что делать: Upgrade the binary task scoring: record per-task, per-attempt outcomes with `--tries` default 2 (keep pass@1/2/3 aggregates) and count a failure taxonomy — syntax_error / test_timeout / malformed_response / exhausted_context / user_asks — plus seconds_per_case and optional cost from the executor log. This is mostly a data-schema change in task_runner.py: verify.py already returns exit codes, and the agent stdout is already captured. trend.py then groups proposals by failure class, so a syntax-error fail proposes a different harness fix than a timeout (directly feeds the plan's failure-proposal doc). The 225-problem polyglot seed can wait until the kit outgrows 3 tasks — non-Python tracks need per-language toolchains, not drop-in on Windows.
- Отношение к плану 2026-08-24: extends Task 3 (task_runner scoring) and Task 4 (proposal grouping)

### P3 [4h] Executor profiles + trajectory capture (mini-swe-agent pattern, stdlib)
- Источники: https://github.com/SWE-agent/mini-swe-agent
- Что делать: Make task_runner's `--executor` a small profile map, not a hard-wired `claude -p`: add a subprocess-only bash-loop profile (every action = subprocess.run, linear append-only history) so execution isn't married to one CLI, and write the executor's stdout to a per-task trajectory file so a failing verify can be inspected without re-running. The sandbox is already the planned temp-dir repo copy — that is mini-swe-agent's LocalEnvironment swap, so no new machinery. Do NOT vendor litellm/pydantic/jinja2 or the bash/Linux-only tooling; keep it a stdlib template.
- Отношение к плану 2026-08-24: extends Task 3 (task_runner executor handling) and Task 4 (trajectory-backed proposals from the trace-rec recommendation)

### P3 [5h] SkillHone-style decision history on top of the results store
- Источники: https://arxiv.org/abs/2606.08671
- Что делать: Add a `save_decision(diagnosis, revision, evidence, outcome)` JSONL alongside the plan's results store so every harness edit records why it was made, which alternatives were rejected, and which probe exposed which failure — instead of the nightly loop inheriting only final artifacts and re-deriving old fixes. trend.py renders recent decisions next to Proposals; the rejected-edit buffer and hold-out gate reuse the same file. Schema-only borrow, stdlib json + already-planned results dir; do NOT take SkillHone's Forgejo/LiteLLM/subagent-dispatch harness — that part is overkill for a Windows-local stdlib kit.
- Отношение к плану 2026-08-24: extends Task 1 (adds one writer + JSONL) and Task 4 (renders decisions)

### P3 [8h] Proposal engine: incremental diffs + trace reflection (ACE + GEPA kernel)
- Источники: https://arxiv.org/abs/2510.04618; https://arxiv.org/abs/2507.19457
- Что делать: Two cheap upgrades to the evolution loop, both stdlib-reimplementable over the kit's existing LLM adapter: (1) proposal templates must be structured append/edit deltas against the target skill doc, never rewrite-and-shrink, with the Curator merge as deterministic non-LLM logic — this prevents the brevity/context collapse ACE documents and protects AGENTS.md/OPS.md. (2) generate proposals from execution traces, not just verdicts: Task 2's payload must include a stderr/stdout trace tail per scenario so the proposal states the actual failure cause (GEPA reflection kernel; skip the dspy/GEPA package).
- Отношение к плану 2026-08-24: extends Task 4 (proposal generation); requires Task 2 payload schema to add per-scenario trace tails

### P4 [16h] ADAS-style meta-agent search for harness diffs — hold until metrics exist
- Источники: https://arxiv.org/abs/2408.08435
- Что делать: Follow-up plan, not part of this one: after the quantitative metric + decision history + merge gate are live, a meta-agent 'programmer' emits candidate harness diffs (runner/task_runner policy, trend thresholds) evaluated by the task benchmark, keeping the best per a simple fitness archive and emitting each candidate as a git branch for human review — never auto-commit (advisory exec-untrusted-code stance). ADAS's reference loop is a few hundred self-contained lines against an LLM API (no GPU/langchain), so it fits when it lands, but running it before Tasks 1–5 exist means optimizing noise.
- Отношение к плану 2026-08-24: new — follow-up after Tasks 1–5; closes the 'evolution loop fully manual' gap end-to-end

### P5 [6h] MIPROv2 zero-shot baseline for SKILL rewrites — one-off experiment, outside the kit
- Источники: https://dspy.ai/api/optimizers/MIPROv2/
- Что делать: Only if the trace-reflection proposals underperform: run a one-off MIPROv2 zero-shot instruction optimization over the 3-task benchmark in a separate venv, emit candidate SKILL.md rewrites, score them, and hand the winner to the human merge gate. The `dspy` dependency (pydantic/jinja2/litellm/optuna) is acceptable for an experiment but must stay out of the kit itself per the stdlib rule — treat as throwaway tooling, evaluate once, drop.
- Отношение к плану 2026-08-24: new — competing baseline for the Task 4 proposal flow; gate by the SkillOpt hold-out rule


## Коррекции существующего плана

- Task 1 (results store): add a decisions sibling. The append-only one-JSON-per-run store is right (git-diffable, matches the mrd-verified consensus) — but add save_decision/decisions JSONL ({diagnosis, revision, evidence, outcome}) now, because the SkillOpt rejected-edit buffer and hold-out gate both need 'what was tried and rejected' provenance that plain run docs cannot carry.
- Task 2 (--json payload): enrich the schema before wiring. Planned `{"kind":"trap","scenarios":[{"name","verdict"}],"passed","total"}` is too thin for the upgraded trend.py: add per-scenario trace tail (stderr/stdout tail), duration, and for task runs per-task attempts (pass@k) + failure class + seconds_per_case. Change it in the task spec now, not as a later migration.
- Task 3 (task benchmark): do not treat 3 tasks as a gateable metric. 3 tasks is ~50x below the 100–200 examples/route needed for statistical separation, so the benchmark is a trend line and qualitative signal only — record pass@1/2/3 with --tries default 2 and a syntax/timeout/malformed/exhausted failure taxonomy instead of binary-only. Also add the executor-profile arg and per-task trajectory file now (mini-swe-agent pattern), since it is a small addition while the runner is being written from scratch.
- Task 4 (trend.py): two corrections to the sketched implementation. (1) Add git-committed rolling baselines (`eval/baselines/*.json`) and pp-delta WARNING/CRITICAL warn-not-block bands — never a frozen score gate; the sketched `_proposals()` is fine as the proposal listing but no threshold logic belongs in it. (2) Proposals must be emitted as structured append/edit deltas citing the failure trace (ACE + GEPA), not one-line rewrites, and the fixed-failure exclusion already in the test stays.
- Task 5 (CI): correct the security posture before any live run. The sketched evals.yml runs the arbitrary EXECUTOR on the writable checkout with the full runner env (leaks API keys into the agent). Required: container job with read-only repo mount + tmpfs writable on ubuntu, env-stripping launcher whitelist, and on the Windows leg a subprocess env-whitelist into the temp-dir copy (Windows Sandbox unavailable on this Home machine). Exit-code discipline: keep task_runner's exit-1 flake-gate; adopt 2=block only if a hard gate ever becomes statistically meaningful.
- Task 6 (size-gate): extraction fixes the drift once, not permanently. Pair the mechanical extraction with the edit-size budget from the SkillOpt gate (reject/flag any merged proposal whose delta pushes a file past soft limits) — otherwise the first evolution round re-drifts the same files the task just trimmed. This is one small policy check inside trend.py's proposal flow.
- Do not add a meta-agent auto-evolution loop (ADAS/SIA harness-search) to this plan's task list. The plan's semi-auto human-merge loop is the correct v1; meta-programming the harness only pays off after the result store, baselines, and decision history exist. Also keep the rejected items rejected: hermes-agent-self-evolution and OpenHands/benchmarks are heavy-dep harnesses that violate the stdlib/Windows constraints — no partial adoption.

## Слепые зоны свипа (completeness-critic)

1. **Skill-ablation**: `--disable-skill <slug>` в раннерах → дельта pass-rate per-skill; тренд предлагает удаления/переписывания скиллов данными, а не «по вайбам». 37 скиллов = постоянный токен-налог без доказательства пользы.
2. **Целостность судьи**: unit-тесты на verdict-bait (ответ «должно быть PASS» не должен проходить); писать распределение вердиктов по повторам в JSON — флипующие сценарии исключать из трендов.
3. **Cost/wall-time как ось эвала**: сейчас ноль учёта; добавить duration_s/tokens/cost_usd в payload; trend.py показывает pass-rate/$ по моделям.
4. **Windows-fidelity CI**: live-прогон в плане только на ubuntu — а nt-only ветка resolve_cmd и кодировка cp1251 никогда не тестируются живьём; матрица windows-latest + сценарий с кириллицей.
5. **Self-security**: byte-compare всех деплойнутых копий ~/.memory/scripts (сейчас только _compat.py); trap-класс context-poisoning (отравленные доки репо).
6. **Co-firing матрица скиллов**: trigger_eval пишет все совпавшие slug'и → данные для мержа дублирующихся скиллов (3 debugging-скилла!); docs-as-tests: каждый CLI-пример из OPS.md прогонять --help в CI.
7. **Coordination tasks**: ни одного эвала на subagent/оркестрацию при заявленной силе кита именно там; fixture с контрактом двух модулей.
8. **Bootfile rot**: doctor-check сравнения kit VERSION vs деплойнутый CLAUDE.md/~/.memory VERSION.

## Отклонённые находки (честность)

- hermes-agent-self-evolution (NousResearch, MIT, 5k★): реален, но тяжёл для stdlib-кита.
- OpenHands/benchmarks: docker-harness избыточен.


## Подтверждённые источники (12)

- **mini-swe-agent** (6h) — https://github.com/SWE-agent/mini-swe-agent
  ~100-line bash-only coding agent: no tool-calling, every action = subprocess.run, linear append-only history. Sandbox by swapping subprocess.run -> docker/podman/bubblewrap/local. Ships batch-SWE-benc | заимствовать: Use it as the kit's second executor profile, not just 'claude -p'. The kit's task_runner can accept --executor 'mini-swe-agent ...' against a local sa
- **MIPROv2 (DSPy) — Bayesian instruction/demo optimizer** (6h) — https://dspy.ai/api/optimizers/MIPROv2/
  A Bayesian, load-balanced teleprompter that jointly proposes instruction text and few-shot demonstrations, or optimizes instructions alone in zero-shot mode, using a grounded dataset of inputs and a m | заимствовать: Cheap first baseline for skill optimization: run MIPROv2 in zero-shot instruction mode against the kit's new 3-task test-oracle benchmark to produce S
- **Aider benchmark harness + polyglot-benchmark** (8h) — https://github.com/Aider-AI/aider/tree/main/benchmark
  Aider's self-measurement harness: runs Exercism-style exercises in Docker, scores 'pass_rate_N' for N tries (pass@2 default), and emits a YAML report per run with seconds_per_case, total_cost, and an  | заимствовать: Three concrete additions to trend.py: (1) pass_rate with retries — not binary single-shot, so the kit's record should persist per-attempt outcomes and
- **GEPA (Genetic-Pareto Reflective Prompt Evolution, ICLR 2026 Oral)** (8h) — https://arxiv.org/abs/2507.19457
  A sample-efficient optimizer that evolves any text component of a compound AI system by reflecting in natural language on execution traces (why failures happened, not just that they failed), applying  | заимствовать: Use execution-trace reflection (not score-only) as the proposal engine behind trend.py: feed the kit's trap-suite failure traces into GEPA to generate
- **model-regression-detection: SQLite + rolling-drift + merge-gate reference impl** (8h) — https://github.com/metehanulusoy/model-regression-detection
  A complete, MIT-licensed OSS template for exactly what coding-kit's plan adds (JSON results store + failure proposals + gating): JSONL golden dataset (diffs cleanly, stable ids pair baseline↔candidate | заимствовать: Adopt as the near-exact shape for the plan's result store and trend.py: store runs in SQLite (coding-kit already runs SQLite FTS5 in ~/.memory) or JSO
- **ACE — Agentic Context Engineering (Stanford)** (10h) — https://arxiv.org/abs/2510.04618
  Treats system prompts/memory as evolving 'playbooks' refined through a generation → reflection → curation cycle with structured incremental updates, which prevents brevity bias and context collapse (t | заимствовать: Apply its incremental-append curation to the kit's AGENTS.md/OPS.md evolution so automated edits add structured sections instead of rewriting-and-shri
- **GitHub Agentic Workflows zero-secret sandbox architecture** (10h) — https://github.blog/ai-and-ml/generative-ai/under-the-hood-security-architecture-of-github-agentic-workflows/
  Microsoft/GitHub (Mar 2026) threat model + reference architecture for running agents in Actions: (1) zero-secret agents — LLM API tokens live in an isolated API proxy and MCP creds in a trusted gatewa | заимствовать: Directly answers 'security of untrusted agent-generated code in CI' for coding-kit's trap-suite: run `runner.py --executor CLI` (which executes agent-
- **SkillOpt (Microsoft) — text-space optimizer with strict validation-gate acceptance** (12h) — https://arxiv.org/abs/2605.23904
  A frozen optimizer model turns scored rollouts into bounded add/delete/replace edits on a single skill document and accepts an edit only if it strictly improves a held-out validation score, stabilized | заимствовать: Use its acceptance rule as the merge gate for the kit's propose→review→merge loop: a candidate SKILL.md/AGENTS.md edit is auto-mergeable only if it be
- **Three-tier eval cascade with statistical regression gate (not frozen thresholds)** (12h) — https://laoujin.github.io/Atlas/research/2026-06-04-evals-how-do-you-know-your-ai-works-session-blueprint/evals-in-ci-cd
  2026 consensus (13-source Atlas survey of futureagi/Galileo/Braintrust/MonteCarlo) for CI evals: (1) cascade cheapest-first — deterministic checks ($0, sub-ms: JSON schema, regex, forbidden-phrase, to | заимствовать: This is the maturity model for coding-kit's planned 'test-oracle task benchmark + trend.py failure proposals + merge gating'. Trap-suite already has d
- **SIA — Self Improving AI with Harness & Weight Updates** (16h) — https://arxiv.org/abs/2605.27276
  A Feedback-Agent loops simultaneously over scaffold (harness) updates — tools, prompts, retry logic, search procedure — and weight updates, showing that harness iteration alone is the weaker lever and | заимствовать: Adopt its 'weakness → harness edit' phase as the missing evolution driver: treat agent tools/prompts/retry/search procedure as editable state scored b
- **ADAS — Automated Design of Agentic Systems (UBC/Vector, ICLR 2025)** (18h) — https://arxiv.org/abs/2408.08435
  A meta-agent 'programmer' searches over agent designs expressed in code, generating, evaluating, and iteratively mutating complete working agents against a target metric to discover novel high-perform | заимствовать: Direct blueprint for closing the kit's 'manual harness evolution loop' gap: replace hand-editing the harness/doctor.py/trap-suite with a meta-agent th
- **SkillHone (Tencent/WeChat) — continual skill evolution via persistent decision history** (24h) — https://arxiv.org/abs/2606.08671
  Role-separated optimize/eval subagents evolve a SKILL.md bundle across sessions and record each step as a decision record (diagnosis → revision → redacted eval evidence → outcome), so later runs inher | заимствовать: Make the planned JSON results store / trend.py a SkillHone-style decision history: persist {diagnosis, revision, evidence, outcome} per trap/harness i