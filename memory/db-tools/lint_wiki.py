#!/usr/bin/env python3
"""lint_wiki.py — checks the integrity of the Wiki library (Karpathy LLM Wiki pattern).

For each post (all *.md except service files):
  - YAML frontmatter presence;
  - required fields: type, title, description, date, tags;
  - tags: lowercase, no spaces;
  - file name: kebab-case.

Prints an error report and tag statistics. Exit code 0 = clean, 1 = errors found.

Usage:
  python3 lint_wiki.py [path-to-Wiki]
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
    """Return a dict from the YAML frontmatter, or None if absent."""
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
            print(f"  ⚠ YAML error in frontmatter: {exc}", file=sys.stderr)
            return None
    # fallback without yaml: top-level keys only
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
            errors.append(f"{rel}: no YAML frontmatter (starts with '---' and closed by '---')")
            continue
        for field in REQUIRED:
            value = fm.get(field)
            if value in (None, ""):
                errors.append(f"{rel}: missing required field '{field}'")
        tags = fm.get("tags") or []
        if not isinstance(tags, list):
            errors.append(f"{rel}: 'tags' must be a list [a, b]")
            tags = []
        for tag in tags:
            tag = str(tag)
            if tag != tag.lower() or " " in tag:
                errors.append(f"{rel}: tag '{tag}' — must be lowercase without spaces")
            tag_counter[tag] += 1
        if not is_kebab(path.name):
            errors.append(f"{rel}: file name is not kebab-case")

    print(f"Posts: {len(posts)}")
    if tag_counter:
        print("Tags: " + ", ".join(f"{t} ({n})" for t, n in tag_counter.most_common()))
    if errors:
        print(f"\nErrors: {len(errors)}")
        for err in errors:
            print(f"  ✗ {err}")
        return 1
    print("Errors: 0 — library clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
