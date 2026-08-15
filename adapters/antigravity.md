# Antigravity IDE + Gemini — Setup Guide

> Как подключить Business Agent Kit к Antigravity IDE с Gemini.

---

## 1. Что такое Antigravity IDE

Antigravity IDE — AI-ориентированная среда разработки. Поддерживает Gemini как backend-модель.
Агент в IDE читает системные инструкции и файлы проекта.

## 2. Установка

### Шаг 1: Разместить набор

Скопируй `assistant-kit` в удобное место:
```bash
# Например:
cp -r assistant-kit ~/business-agent-kit
cd ~/business-agent-kit
```

### Шаг 2: Первая сборка базы

```bash
python3 db-tools/build.py
```

### Шаг 3: Настроить Antigravity IDE

В настройках IDE (Settings → AI → System Instructions) добавь содержимое `adapters/gemini.md` как системную инструкцию.

**Или** — если IDE поддерживает файл контекста проекта — положи `AGENTS.md` в корень проекта.

### Шаг 4: Проверка

Открой проект в IDE, спроси агента: «кто ты и что умеешь».
Он должен описать роль бизнес-агента с кросс-чатовой памятью и скиллами.

---

## 3. Структура после установки

```
~/business-agent-kit/
├── OPS.md              # контракт агента (загружается первым)
├── BOOT.md             # личность, compliance, startup
├── AGENTS.md           # роутер и правила
├── SKILL_RUNTIME.md    # полный runtime (≥16K контекст)
├── SKILL_RUNTIME_COMPACT.md  # компактный runtime (<8K контекст)
├── profile.yml         # манифест
├── skills/             # скиллы (Hermes-совместимые)
│   ├── reasoning-engine/
│   ├── business-persona/
│   ├── fable-method/
│   ├── business-wiki/
│   ├── money-path-safety/
│   ├── ... 
├── Wiki/               # кросс-чатовая память
│   ├── reference/
│   ├── howto/
│   ├── ideas/
│   ├── errors/
│   ├── decisions/
│   ├── index.md
│   └── log.md
├── db-tools/           # инструменты поиска и индексации
│   ├── build.py
│   ├── search.py
│   └── lint_wiki.py
└── adapters/           # адаптеры для разных платформ
    ├── gemini.md
    ├── antigravity.md
    └── UNIVERSAL.md
```

---

## 4. Как это работает

### Кросс-чатовая память

Агент не помнит разговоры — он ищет в базе `Wiki/`.
- Каждый факт, решение, ошибка → записывается в Wiki с frontmatter.
- `db-tools/search.py` — полнотекстовый поиск (SQLite FTS5).
- `db-tools/build.py` — пересборка индекса после записи.

### Скиллы

Агент проверяет `skills/` перед каждой нетривиальной задачей.
- Каждый скилл = `SKILL.md` с YAML frontmatter (name + description).
- Формат совместим с Hermes.
- Always-on скиллы загружены всегда. Доменные — по триггеру.

### Reasoning Engine

Агент применяет multi-step thinking (5 шагов вперёд) перед каждым действием.
Evidence-first: факты из первоисточников, минимум 2 источника.

---

## 5. Для моделей с ограниченным контекстом

Если Gemini в Antigravity IDE имеет <8K контекста:
- Используй `SKILL_RUNTIME_COMPACT.md` вместо `SKILL_RUNTIME.md`.
- Скиллы загружай только primary (без support/validator).
- Память: поиск по базе, но запись — короткая.

---

## 6. Перенос на другой компьютер

Скопируй папку целиком — внутри только текст.
База (`db/wiki.db`) пересобирается из текстов за секунды: `python3 db-tools/build.py`.