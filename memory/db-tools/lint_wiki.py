#!/usr/bin/env python3
"""lint_wiki.py — проверка целостности Wiki-библиотеки (паттерн LLM Wiki Карпатого).

Проверяет у каждого поста (все *.md, кроме служебных):
  - наличие YAML-frontmatter;
  - обязательные поля: type, title, description, date, tags;
  - теги: нижний регистр, без пробелов;
  - имя файла: kebab-case.

Выводит отчёт об ошибках и статистику тегов. Код возврата 0 = чисто, 1 = есть ошибки.

Использование:
  python3 lint_wiki.py [путь-к-Wiki]
"""
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

REQUIRED = ("type", "title", "description", "date", "tags")
SERVICE_FILES = {"README.md", "index.md", "log.md"}
SKIP_DIRS = {"_templates", "raw", "assets"}


def parse_frontmatter(text: str) -> dict | None:
    """Возвращает dict из YAML-frontmatter или None, если его нет."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    if yaml is not None:
        try:
            data = yaml.safe_load(block)
            return data if isinstance(data, dict) else None
        except yaml.YAMLError as exc:
            print(f"  ⚠ YAML-ошибка в frontmatter: {exc}", file=sys.stderr)
            return None
    # fallback без yaml: только ключи верхнего уровня
    data = {}
    for line in block.splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            data[m.group(1)] = m.group(2)
    return data


def is_kebab(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*\.md", name))


def main() -> int:
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    else:
        from _compat import chulan_root
        root = chulan_root() / "Wiki"


    errors: list[str] = []
    posts: list[Path] = []
    tag_counter: Counter = Counter()

    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if path.name in SERVICE_FILES or rel.parts[0] in SKIP_DIRS:
            continue
        posts.append(path)
        text = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{rel}: нет YAML-frontmatter (начинается с '---' и закрыт '---')")
            continue
        for field in REQUIRED:
            value = fm.get(field)
            if value in (None, ""):
                errors.append(f"{rel}: отсутствует обязательное поле '{field}'")
        tags = fm.get("tags") or []
        if not isinstance(tags, list):
            errors.append(f"{rel}: 'tags' должен быть списком [a, b]")
            tags = []
        for tag in tags:
            tag = str(tag)
            if tag != tag.lower() or " " in tag:
                errors.append(f"{rel}: тег '{tag}' — нужен нижний регистр без пробелов")
            tag_counter[tag] += 1
        if not is_kebab(path.name):
            errors.append(f"{rel}: имя файла не kebab-case")

    print(f"Постов: {len(posts)}")
    if tag_counter:
        print("Теги: " + ", ".join(f"{t} ({n})" for t, n in tag_counter.most_common()))
    if errors:
        print(f"\nОшибок: {len(errors)}")
        for err in errors:
            print(f"  ✗ {err}")
        return 1
    print("Ошибок: 0 — библиотека в порядке")
    return 0


if __name__ == "__main__":
    sys.exit(main())
