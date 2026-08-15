---
name: dev-wiki
description: 'Always-on. Кросс-чатовая память для разработки: запись решений, ошибок, паттернов в Wiki/. Использовать при «запиши», «сохрани», «запомни», «что мы знаем про X». Цикл: файл → index.md → log.md → python db-tools/build.py → lint.'
---

# Dev Wiki — кросс-чатовая память разработчика

Always-on скилл. База знаний: решения, баги, паттерны, архитектурные решения.

## Типы записей

| Тип | Папка | Когда |
|-----|-------|-------|
| `reference` | `Wiki/reference/` | Факт, документация, знание |
| `howto` | `Wiki/howto/` | Инструкция, guide |
| `error` | `Wiki/errors/` | Баг, инцидент, lesson learned |
| `decision` | `Wiki/decisions/` | ADR, архитектурное решение |
| `pattern` | `Wiki/reference/` | Повторяющийся паттерн, идиома |

## Workflow — сохранить

1. Определить тип → папка.
2. Создать файл `Wiki/<тип>/<slug>.md` с frontmatter:
   ```yaml
   ---
   type: reference
   title: "Заголовок"
   description: "О чём"
   date: 2026-08-15
   tags: [категория, тема]
   ---
   ```
3. Обновить `Wiki/index.md`.
4. Дописать `Wiki/log.md`.
5. `python db-tools/build.py`
6. `python db-tools/lint_wiki.py Wiki`

## Workflow — поиск

```bash
python scripts/memory-warmup.py -q "запрос"
```

- Искать по базе, НЕ по памяти разговора.
- Нашёл → ответ со ссылкой на файл.
- Не нашёл → «в базе нет».

## Триггеры авто-записи

- «Запиши», «сохрани», «запомни» → полный цикл.
- Баг/инцидент → `Wiki/errors/`.
- Архитектурное решение → `Wiki/decisions/`.
- Новый паттерн → `Wiki/reference/`.

## Категории тегов

`architecture`, `engineering`, `security`, `performance`, `devops`, `testing`, `frontend`, `backend`, `database`, `api`