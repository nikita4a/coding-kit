# Universal Adapter

> Для любого агента, который читает `AGENTS.md` и скиллы.

## Установка (общий принцип)

У агента есть место для «глобальных скиллов» и место для «правил агента».
Найди их в настройках и:

1. Скопируй содержимое `skills/` в папку скиллов агента.
2. Скопируй `AGENTS.md` туда, откуда агент читает правила (или положи в корень проекта).
3. Запусти `python3 db-tools/build.py` из корня набора.

## Конкретные агенты

### Claude Code
```bash
cp AGENTS.md ~/.claude/CLAUDE.md
cp -r skills/* ~/.claude/skills/
```

### opencode
```bash
cp AGENTS.md ~/.config/opencode/AGENTS.md
cp -r skills/* ~/.config/opencode/skills/
```

### Hermes
```bash
cp AGENTS.md ~/.hermes/SOUL.md
cp -r skills/* ~/.hermes/skills/
```

### Codex
```bash
cp AGENTS.md ~/.codex/AGENTS.md
```

### Cursor
```bash
# Положи AGENTS.md в корень проекта как .cursorrules
cp AGENTS.md .cursorrules
```

### Любой другой
```bash
# AGENTS.md → туда, откуда агент читает правила
# skills/* → туда, где агент ищет скиллы
# python3 db-tools/build.py → первая сборка базы
```

## Проверка

Спроси агента «кто ты и что умеешь». Он должен описать роль бизнес-агента с кросс-чатовой памятью и скиллами.