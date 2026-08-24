import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from prompt_assembly import parse_frontmatter, skill_manifest, assemble_prompt


def write_skill(root, name, desc, body="BODY"):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: '{desc}'\n---\n\n# {name}\n\n{body}\n",
        encoding="utf-8", newline="\n")
    return d


def test_parse_frontmatter_extracts_name_and_desc():
    text = "---\nname: foo\ndescription: 'do the thing'\n---\n\nbody"
    fm = parse_frontmatter(text)
    assert fm["name"] == "foo" and fm["description"] == "do the thing"


def test_parse_frontmatter_malformed_returns_empty():
    assert parse_frontmatter("") == {}
    assert parse_frontmatter("no frontmatter here") == {}
    assert parse_frontmatter("---") == {}
    assert parse_frontmatter("not a\n--- delimited head") == {}


def test_skill_manifest_excludes_disabled(tmp_path):
    write_skill(tmp_path, "alpha", "first")
    write_skill(tmp_path, "beta", "second")
    names = [m["name"] for m in skill_manifest(tmp_path, disable=frozenset({"alpha"}))]
    assert names == ["beta"]


def test_skill_manifest_sorted_by_name(tmp_path):
    write_skill(tmp_path, "zeta", "z-desc")
    write_skill(tmp_path, "alpha", "a-desc")
    write_skill(tmp_path, "mike", "m-desc")
    names = [m["name"] for m in skill_manifest(tmp_path)]
    assert names == ["alpha", "mike", "zeta"]


def test_skill_manifest_skips_malformed_and_missing(tmp_path):
    write_skill(tmp_path, "zeta", "last", "Z BODY")
    # frontmatter present but no `name` -> not a usable skill
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\ndescription: 'no name here'\n---\n\nbody\n",
        encoding="utf-8", newline="\n")
    # directory with no SKILL.md at all
    empty = tmp_path / "empty"
    empty.mkdir()
    names = [m["name"] for m in skill_manifest(tmp_path)]
    assert names == ["zeta"]


def test_skill_manifest_skips_missing_or_empty_description(tmp_path):
    write_skill(tmp_path, "alpha", "first")
    # name present but no description -> malformed
    no_desc = tmp_path / "no_desc"
    no_desc.mkdir()
    (no_desc / "SKILL.md").write_text(
        "---\nname: no_desc\n---\n\n# x\n\nbody\n", encoding="utf-8", newline="\n")
    # name present but empty description -> malformed
    empty_desc = tmp_path / "empty_desc"
    empty_desc.mkdir()
    (empty_desc / "SKILL.md").write_text(
        "---\nname: empty_desc\ndescription: ''\n---\n\n# x\n\nbody\n",
        encoding="utf-8", newline="\n")
    names = [m["name"] for m in skill_manifest(tmp_path)]
    assert names == ["alpha"]


def test_assemble_prompt_inlines_active_body_only(tmp_path):
    write_skill(tmp_path, "alpha", "first", "ALPHA BODY")
    write_skill(tmp_path, "beta", "second", "BETA BODY")
    p = assemble_prompt("SCENARIO", tmp_path, active_skill="alpha")
    assert "ALPHA BODY" in p            # active skill: full body inlined
    assert "BETA BODY" not in p         # inactive skill: description only
    assert "second" in p and "SCENARIO" in p


def test_assemble_prompt_honors_disable(tmp_path):
    write_skill(tmp_path, "alpha", "first", "ALPHA BODY")
    p = assemble_prompt("X", tmp_path, active_skill="alpha", disable=frozenset({"alpha"}))
    assert "ALPHA BODY" not in p and "first" not in p


def test_assemble_prompt_preserves_body_verbatim(tmp_path):
    write_skill(tmp_path, "alpha", "first", "ALPHA BODY")
    body = "LINE ONE\nLINE @TWO{3}\nLINE THREE"
    p = assemble_prompt(body, tmp_path)
    assert p.endswith("\n\n" + body)
    assert body in p