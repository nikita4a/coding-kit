---
name: code-graph-review
description: 'Использовать ПЕРЕД КОММИТОМ или ревью изменений, когда нужно понять «что сломает эта правка из N файлов»: blast radius по диффу, затронутые execution-пути, мёртвый код, архитектурные хабы/мосты, слабые места, переименование с предпросмотром. Не использовать для поиска по коду — CRG для структурного анализа диффа, не для навигации.'
compatibility: git-репо с построенным графом (code-review-graph MCP)
---

# Code graph review: что сломает правка

MCP-сервер code-review-graph отвечает на вопрос «что сломает эта правка из N файлов» — impact/blast radius по ДИФФУ, dead-code, communities, flows.

## Workflow (порядок применения)

1. **Правки готовы → сначала диагностика** (lsp): 0 ошибок до любого линтера.
2. **Пересобери граф** — `build_or_update_graph_tool` (инкрементально). Граф устарел = ложный анализ.
3. **Прогони `detect_changes`** — дифф → risk-скор, приоритеты (что смотреть первым), пробелы в тестах. Это главный инструмент ревью.
4. **Оцени blast radius** — `get_impact_radius` (глубина BFS по диффу), `get_review_context` (сниппеты кода). Вопрос: «что сломает правка из N файлов».
5. **Проверь затронутые флоу** — `get_affected_flows`/`list_flows`: какие пользовательские пути проходят через изменённые файлы.
6. **Архитектура (если нужно)** — `get_hub_nodes` (кто хаб), `get_bridge_nodes` (мосты), `get_surprising_connections`, `get_architecture_overview`, `get_knowledge_gaps`.
7. **Мёртвый код / rename** — `refactor_tool(mode="dead_code")`; `refactor_tool(mode="rename")` → `apply_refactor_tool`.
8. **Ложные срабатывания dead-code проверь через lsp** (`find_references`), не удаляй вслепую.

## Таблица: задача → инструмент

| Задача | Инструмент |
|---|---|
| ревью изменений (дифф → риск → приоритеты) | `detect_changes` |
| blast radius правки из N файлов | `get_impact_radius`, `get_review_context` |
| затронутые execution-пути | `get_affected_flows`, `list_flows` |
| мёртвый код | `refactor_tool(mode="dead_code")` |
| хабы/мосты/неожиданная связанность | `get_hub_nodes`, `get_bridge_nodes`, `get_surprising_connections` |
| слабые места | `get_knowledge_gaps`, `get_suggested_questions` |
| rename с предпросмотром | `refactor_tool(mode="rename")` → `apply_refactor_tool` |

## Грабли

- **dead-code даёт ложные срабатывания** на callback-паттернах и `Thread(target=...)` — проверять через lsp, не удалять вслепую.
- Граф строится/обновляется инкрементально: `build_or_update_graph_tool` после правок — иначе устаревшие данные.