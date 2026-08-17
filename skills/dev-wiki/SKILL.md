---
name: dev-wiki
description: 'Always-on. Кросс-чатовая память для разработки: запись решений, ошибок, паттернов в глобальную Wiki (../memory). Использовать при «запиши», «сохрани», «запомни», «что мы знаем про X». Иерархия: переносимое → ../memory/Wiki/; проектное → WORK/<проект>/docs/. Цикл: файл → index.md → log.md → python ../memory/db-tools/build.py → lint.'
---

# Dev Wiki — кросс-чатовая память разработчика

Always-on скилл. База знаний: решения, баги, паттерны, архитектурные решения.
Память вынесена в `../memory/` (иерархия global + per-project).

## Правило границы

| Знание | Куда | Индекс |
|--------|------|--------|
| **Переносимое** (паттерны, уроки, решения) | `../memory/Wiki/<тип>/` | `python ../memory/db-tools/build.py` |
| **Проектное** (статус, конфиги, контекст) | `WORK/<проект>/docs/` | `python ../memory/db-tools/build.py -r <корень> -o ../memory/db/<имя>.db` |

Знание живёт/умирает с проектом → проект; переносимо между проектами → глобальная Wiki.

## Типы записей (глобальная Wiki)

| Тип | Папка | Когда |
|-----|-------|-------|
| `reference` | `../memory/Wiki/reference/` | Факт, документация, знание |
| `howto` | `../memory/Wiki/howto/` | Инструкция, guide |
| `error` | `../memory/Wiki/errors/` | Баг, инцидент, lesson learned |
| `decision` | `../memory/Wiki/decisions/` | ADR, архитектурное решение |
| `idea` | `../memory/Wiki/ideas/` | Идея |

## Workflow — сохранить (глобальное)

1. Определить тип → папка в `../memory/Wiki/`.
2. Создать файл `../memory/Wiki/<тип>/<slug>.md` с frontmatter:
   ```yaml
   ---
   type: reference
   title: "Заголовок"
   description: "О чём"
   date: 2026-08-15
   tags: [категория, тема]
   ---
   ```
3. Обновить `../memory/Wiki/index.md`.
4. Дописать `../memory/Wiki/log.md`.
5. `python ../memory/db-tools/build.py`
6. `python ../memory/db-tools/lint_wiki.py`
7. Важный вывод → `python ../memory/db-tools/findings.py add "тема" --text "вывод" --source путь`

## Workflow — поиск

```bash
python ../memory/db-tools/search_all.py "запрос"          # все базы разом
python ../memory/db-tools/search_all.py "запрос" --substring   # склонения/подстроки
```

- Искать по базе, НЕ по памяти разговора.
- Нашёл → ответ со ссылкой на файл.
- Не нашёл → «в базе нет».

## Триггеры авто-записи

- «Запиши», «сохрани», «запомни» → полный цикл.
- Баг/инцидент → `../memory/Wiki/errors/`.
- Архитектурное решение → `../memory/Wiki/decisions/`.
- Новый паттерн → `../memory/Wiki/reference/`.

## Категории тегов

`architecture`, `engineering`, `security`, `performance`, `devops`, `testing`, `frontend`, `backend`, `database`, `api`