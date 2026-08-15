# Coding Agent OS — Skill Runtime

> **v1.0** | For platforms with ≥16K context.
> Superpowers: plan → TDD → implement → verify → report.
> For <8K context → see SKILL_RUNTIME_COMPACT.md.

## For every non-trivial task

### 1. SUPER POWERS (always)

```
PLAN → TDD → IMPLEMENT → VERIFY → REPORT
```

### 2. PLAN
- Сформулируй «что значит готово» — конкретно, наблюдаемо.
- Назови scope: какие файлы трогаешь, какие НЕ трогаешь.
- Сложная задача (>3 файлов) → разбей на атомарные tasks.

### 3. TDD
- Красный тест → зелёный код → рефакторинг.
- Никакого кода без падающего теста.
- Баг-фикс → Prove-It Pattern: тест, воспроизводящий баг, ПЕРВЫМ.

### 4. IMPLEMENT
- Минимальное изменение, делающее тест зелёным.
- YAGNI: не добавляй ничего сверх теста.
- Стиль — как в окружающем коде.

### 5. VERIFY
- Тест зелёный? → наблюдал.
- Все существующие тесты зелёные? → прогнал.
- Сборка не сломана? → проверил.
- Баг-фикс → TWINS: поискал такой же паттерн в кодовой базе.

### 6. REPORT
- Результат первой строкой.
- Какие файлы тронуты.
- Что проверено.

## Skill loading

```
1. IDENTIFY: проверь skills/ — есть ли скилл под задачу?
2. LOAD: read skills/<name>/SKILL.md
3. APPLY: следуй Protocol/Workflow секции
4. MARK: 📚 skill-name
```

## Cross-chat memory

```bash
python scripts/memory-warmup.py          # прогрев
python scripts/memory-warmup.py -q "X"   # поиск
python db-tools/build.py                 # пересобрать индекс
```

## Context monitor

```bash
python scripts/context-monitor.py --check
```

## Never
- Write code without a plan and a test
- Build abstractions with one consumer
- Add dependencies without measuring the pain
- Claim "done" without evidence
- Answer from conversation memory — use database