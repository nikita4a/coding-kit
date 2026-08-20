#!/usr/bin/env python3
"""scripts/tools/skills_search.py — skill catalog and symptom search.

Finds which kit skill fits a request WITHOUT a model: token-overlap
ranking of query words against each SKILL.md name + description. The
description is the trigger surface an agent sees before loading a skill,
so a strong hit here means "the right skill will fire".

Usage:
    python scripts/tools/skills_search.py "money promo" --top 5
    python scripts/tools/skills_search.py --list
    python scripts/tools/skills_search.py --skill yagni
    python scripts/tools/skills_search.py ... --dir /path/to/skills
    python scripts/tools/skills_search.py ... --json
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # scripts/tools/
KIT = HERE.parent.parent                        # kit root
DEFAULT_DIR = KIT / "skills"
DEFAULT_TOP = 8

FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9а-яё]+", text.lower()))


def parse_skill(path: Path) -> dict | None:
    """SKILL.md -> {name, description, path}. None if unparsable."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = FRONTMATTER.match(content)
    if not m:
        return None
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip().lower()] = v.strip().strip("'\"")
    name = fields.get("name")
    description = fields.get("description")
    if not name or not description:
        return None
    return {"name": name, "description": description, "path": path}


def catalog(skills_dir: Path) -> list[dict]:
    out = []
    for p in sorted(skills_dir.glob("*/SKILL.md")):
        parsed = parse_skill(p)
        if parsed:
            out.append(parsed)
    return out


def score(skill: dict, query: str) -> float:
    tokens = tokenize(query)
    if not tokens:
        return 0.0
    name_tokens = tokenize(skill["name"])
    desc_tokens = tokenize(skill["description"])
    s = 0.0
    for t in tokens:
        if t in name_tokens:
            s += 3.0
        if t in desc_tokens:
            s += 1.0
    return s / (1.0 + math.log1p(len(desc_tokens)))


def search(skills: list[dict], query: str, top: int) -> list[tuple[float, dict]]:
    ranked = sorted(((score(s, query), s) for s in skills),
                    key=lambda x: -x[0])
    return [(sc, s) for sc, s in ranked[:top] if sc > 0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?", help="search words; omitted with --list")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    ap.add_argument("--list", action="store_true", help="print the whole catalog")
    ap.add_argument("--skill", help="show one skill by name")
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR,
                    help=f"skills directory (default {DEFAULT_DIR})")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    skills = catalog(args.dir)
    if not skills:
        print(f"no skills found under {args.dir}", file=sys.stderr)
        return 2

    if args.skill:
        hit = next((s for s in skills if s["name"] == args.skill), None)
        if not hit:
            print(f"skill '{args.skill}' not found"); return 1
        if args.json:
            print(json.dumps(hit, indent=2, default=str))
        else:
            print(f"{hit['name']}\n  {hit['description']}\n  file: {hit['path']}")
        return 0

    if args.list or not args.query:
        if args.json:
            print(json.dumps([{"name": s["name"], "description": s["description"]}
                              for s in skills], indent=2, ensure_ascii=False))
        else:
            for s in skills:
                print(f"{s['name']:32s} {s['description'][:90]}")
        return 0

    hits = search(skills, args.query, args.top)
    if not hits:
        print(f"no skill matches '{args.query}' — fall back to the task-type "
              "ladder: describe the symptom differently, then web research")
        return 1
    if args.json:
        print(json.dumps([{"score": round(sc, 2), "name": s["name"],
                           "description": s["description"], "path": str(s["path"])}
                          for sc, s in hits], indent=2, ensure_ascii=False))
    else:
        for sc, s in hits:
            print(f"{s['name']:32s} score={sc:.2f}\n  {s['description'][:120]}\n  file: {s['path']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())