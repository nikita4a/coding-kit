"""Controlled inlined-prompt assembly for the kit's eval executors.

`assemble_prompt` builds `<skill manifest>\n\n<task body>` so the kit itself
injects skill name/description lines plus one fully-inlined active skill into
a subprocess executor prompt. Ambient CLI skills (those already loaded by the
host harness) remain outside this module's purview.
"""
import re
from pathlib import Path

_FRONTMATTER = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """`{name, description, ...}` from a `---`-delimited SKILL.md head.

    Returns `{}` when the head is missing or malformed.
    """
    m = _FRONTMATTER.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        out[key] = val
    return out


def _read_skill(skills_root: Path, name: str) -> str | None:
    try:
        return (skills_root / name / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return None


def _body_of(text: str) -> str:
    m = _FRONTMATTER.match(text)
    return text[m.end():].strip() if m else text.strip()


def skill_manifest(skills_root: Path, *,
                   disable: frozenset = frozenset()) -> list[dict]:
    """`[{name, description}]` sorted by name, excluding `disable` names.

    Malformed or missing SKILL.md files are skipped, never raised.
    """
    try:
        dirs = [p for p in skills_root.iterdir() if p.is_dir()]
    except OSError:
        dirs = []
    entries: list[dict] = []
    for d in dirs:
        content = _read_skill(skills_root, d.name)
        if content is None:
            continue
        fm = parse_frontmatter(content)
        name = fm.get("name")
        description = fm.get("description", "")
        if not name or not description or name in disable:
            continue
        entries.append({"name": name, "description": description})
    entries.sort(key=lambda e: e["name"])
    return entries


def assemble_prompt(body: str, skills_root: Path, *,
                    active_skill: str | None = None,
                    disable: frozenset = frozenset()) -> str:
    """Manifest block + task `body`; only the enabled `active_skill` body is
    inlined (following its description line). A disabled active skill has
    neither descriptor nor body."""
    lines = ["Available skills:"]
    for item in skill_manifest(skills_root, disable=disable):
        lines.append(f"- {item['name']}: {item['description']}")
        if item["name"] == active_skill:
            active_text = _read_skill(skills_root, item["name"])
            if active_text is not None:
                lines.append(_body_of(active_text))
    return "\n".join(lines) + "\n\n" + body