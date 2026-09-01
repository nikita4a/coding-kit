#!/usr/bin/env python3
"""Validate SKILL.md files in skills/ directory.

Checks:
  1. Directory exists under skills/
  2. SKILL.md file exists
  3. YAML frontmatter present with 'name' and 'description' (non-empty)
  4. 'name' is kebab-case (lowercase letters, digits, hyphens)
  5. Body is non-empty (content after frontmatter)
  6. Total file under 500 lines (hard limit for .md files)

Usage:
  python scripts/validate_skills.py           # scan all skills/*/SKILL.md
  python scripts/validate_skills.py --json    # JSON output
  python scripts/validate_skills.py --quiet   # only print errors
"""

import sys
import os
import json
from pathlib import Path
from collections import OrderedDict


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
HARD_LINE_LIMIT = 500
KEBAB_RE = r"^[a-z0-9]+(-[a-z0-9]+)*$"


def _find_skill_files():
    """Yield (skill_name, skill_md_path) for every skill directory with a SKILL.md."""
    if not SKILLS_DIR.is_dir():
        return
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        md = entry / "SKILL.md"
        if md.is_file():
            yield entry.name, md


def _parse_frontmatter(path):
    """Extract YAML frontmatter from a SKILL.md file.

    Returns (frontmatter_dict, body_start_line) or (None, None) on failure.
    Parses the subset of YAML used in coding-kit skills: only top-level
    string keys with quoted or unquoted single-line values.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None, None

    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, None

    fm = OrderedDict()
    body_start = None
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            body_start = i + 1  # line after closing ---
            break
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip()
        # unquote
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        fm[key] = val

    if body_start is None:
        return None, None
    return fm, body_start


def _check_kebab(name):
    """Validate kebab-case: lowercase letters, digits, hyphens only."""
    import re
    return bool(re.match(KEBAB_RE, name))


def validate_all():
    """Run all checks and return (errors, warnings)."""
    errors = []
    warnings = []

    if not SKILLS_DIR.is_dir():
        errors.append(f"skills/ directory not found at {SKILLS_DIR}")
        return errors, warnings

    for skill_name, md_path in _find_skill_files():
        prefix = f"skills/{skill_name}/SKILL.md"

        # Parse frontmatter
        fm, body_start = _parse_frontmatter(md_path)
        if fm is None:
            errors.append(f"{prefix}: missing or invalid YAML frontmatter")
            continue

        # Required fields
        for field in ("name", "description"):
            if field not in fm or not fm[field]:
                errors.append(f"{prefix}: missing or empty '{field}' in frontmatter")
            elif field == "name" and fm[field] != skill_name:
                errors.append(
                    f"{prefix}: frontmatter 'name' ({fm[field]}) "
                    f"does not match directory name ({skill_name})"
                )

        # Kebab-case check
        if "name" in fm and fm["name"]:
            if not _check_kebab(fm["name"]):
                errors.append(
                    f"{prefix}: name '{fm['name']}' is not kebab-case "
                    f"(lowercase letters, digits, hyphens only)"
                )

        # Body check
        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            errors.append(f"{prefix}: cannot read file")
            continue

        lines = text.split("\n")
        body = "\n".join(lines[body_start:]).strip() if body_start else ""
        if not body:
            errors.append(f"{prefix}: body is empty after frontmatter")

        # Line count
        if len(lines) > HARD_LINE_LIMIT:
            errors.append(
                f"{prefix}: {len(lines)} lines exceeds hard limit of {HARD_LINE_LIMIT}"
            )

        # Extra frontmatter fields (warning only)
        known_fields = {"name", "description"}
        extra = set(fm.keys()) - known_fields
        if extra:
            warnings.append(
                f"{prefix}: extra frontmatter fields: {', '.join(sorted(extra))}"
            )

    return errors, warnings


def main():
    quiet = "--quiet" in sys.argv
    json_out = "--json" in sys.argv

    errors, warnings = validate_all()

    if json_out:
        result = {
            "pass": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "skills_checked": len(list(_find_skill_files())),
        }
        print(json.dumps(result, indent=2))
    else:
        skill_count = len(list(_find_skill_files()))
        if not quiet:
            print(f"Validating {skill_count} skills in {SKILLS_DIR}...")
            print()

        for w in warnings:
            print(f"WARNING: {w}")
        for e in errors:
            print(f"ERROR: {e}")

        if not quiet:
            print()
            if errors:
                print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
            else:
                print(f"PASS: {skill_count} skills valid, {len(warnings)} warning(s)")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()