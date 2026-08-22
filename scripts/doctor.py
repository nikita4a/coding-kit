#!/usr/bin/env python3
"""doctor.py — kit self-diagnostic: one command, full health picture.

Checks:
  1.  manifest sync      profile.yml skill lists == skills/ dirs (both ways)
  2.  version sync       VERSION == profile.yml version
  3.  skill frontmatter  name/description present, description non-empty
  4.  file-size gate     scripts/tools/check_file_sizes.py --ci
  5.  memory             ~/.memory root + SQLite integrity of every db/*.db
  6.  adapters           every adapter file named in profile.yml exists
  7.  override           .override.md mode validity
  8.  engine sync        the two shipped _compat.py copies are identical
  9.  reflex commands    documented reflex commands actually produce output
 10.  encoding discipline no bare text=True subprocess calls (cp1251 class)

Usage:
    python scripts/doctor.py          # table + exit 1 on any failure
"""
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KIT = Path(__file__).resolve().parents[1]


def check_manifest() -> tuple[bool, str]:
    text = (KIT / "profile.yml").read_text(encoding="utf-8")
    sec = text.split("always_on:")[-1].split("adapters:")[0]
    declared = set(re.findall(r"^\s*-\s+([a-z0-9-]+)", sec, re.M))
    on_disk = {d.name for d in (KIT / "skills").iterdir() if d.is_dir()}
    missing = sorted(declared - on_disk)
    extra = sorted(on_disk - declared)
    if not missing and not extra:
        return (True, f"{len(on_disk)} skills in sync")
    return (False, " ".join(
        ([f"profile-no-dirs: {missing}"] if missing else [])
        + ([f"dirs-not-in-profile: {extra}"] if extra else [])))


def check_versions() -> tuple[bool, str]:
    ver = (KIT / "VERSION").read_text(encoding="utf-8").strip()
    m = re.search(r'^version:\s*"([^"]+)"', 
                  (KIT / "profile.yml").read_text(encoding="utf-8"), re.M)
    prof = m.group(1) if m else "?"
    ok = ver == prof
    return (ok, f"VERSION {ver} == profile {prof}" if ok
            else f"VERSION {ver} != profile {prof}")


def check_frontmatter() -> tuple[bool, str]:
    bad = []
    for sk in sorted((KIT / "skills").iterdir()):
        md = sk / "SKILL.md"
        if not md.is_file():
            bad.append(f"{sk.name}: no SKILL.md")
            continue
        head = md.read_text(encoding="utf-8", errors="replace").split("---")
        if len(head) < 3:
            bad.append(f"{sk.name}: no frontmatter")
            continue
        fm = head[1]
        if yaml is not None:
            try:
                fm_yaml = yaml.safe_load(fm)
            except Exception as exc:
                bad.append(f"{sk.name}: invalid yaml ({str(exc).splitlines()[0]})")
                continue
            if not isinstance(fm_yaml, dict) or not fm_yaml.get("name"):
                bad.append(f"{sk.name}: name missing")
            if not isinstance(fm_yaml, dict) or not fm_yaml.get("description"):
                bad.append(f"{sk.name}: description missing")
            continue
        if not re.search(r"^name:\s*\S+", fm, re.M):
            bad.append(f"{sk.name}: name missing")
        if not re.search(r"^description:\s*\S+", fm, re.M):
            bad.append(f"{sk.name}: description missing")
    return (not bad, f"{len(bad)} bad" if bad else "all present")


def check_gate() -> tuple[bool, str]:
    r = subprocess.run(
        [sys.executable,
         str(KIT / "scripts" / "tools" / "check_file_sizes.py"), "--ci"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    last = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-1] \
        if (r.stdout or r.stderr) else f"rc={r.returncode}"
    return (r.returncode == 0, last)


def check_memory() -> tuple[bool, str]:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_compat", KIT / "memory" / "db-tools" / "_compat.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        root = m.chulan_root()
    except Exception as e:
        return (False, f"memory root: {e}")
    dbs = sorted((root / "db").glob("*.db"))
    for db in dbs:
        try:
            con = sqlite3.connect(db)
            row = con.execute("PRAGMA integrity_check").fetchone()
            con.close()
            if row and row[0] != "ok":
                return (False, f"{db.name}: {row[0]}")
        except sqlite3.Error as e:
            return (False, f"{db.name}: {e}")
    return (True, f"{root} ok, {len(dbs)} db healthy")


def check_adapters() -> tuple[bool, str]:
    missing = [
        f"adapters/{m.group(1)}" for m in re.finditer(
            r"adapters/([\w./-]+\.md)",
            (KIT / "profile.yml").read_text(encoding="utf-8"))
        if not (KIT / "adapters" / m.group(1)).exists()]
    return (not missing, "all targets exist" if not missing
            else "; ".join(missing))

def check_override() -> tuple[bool, str]:
    ov = KIT / ".override.md"
    if not ov.exists():
        return (True, "no .override.md")
    m = re.search(r"^\s*MODE:\s*(\S+)",
                  ov.read_text(encoding="utf-8"), re.M)
    if not m:
        return (False, ".override.md present but no MODE: line")
    mode = m.group(1).strip()
    if mode in ("EXPLORATORY_PROTOTYPE", "STRICT_AUDIT"):
        return (True, f"{mode} (valid)")
    return (False, f"unknown mode {mode!r} — allowed: "
                   "EXPLORATORY_PROTOTYPE, STRICT_AUDIT. Typo?")


def check_engine_sync() -> tuple[bool, str]:
    """The kit ships _compat.py twice (db-tools/ imports it, scripts/ is
    copied to ~/.memory); drift between the copies bit the v2.5 review."""
    a = KIT / "memory" / "db-tools" / "_compat.py"
    b = KIT / "memory" / "scripts" / "_compat.py"
    if a.read_bytes() == b.read_bytes():
        return (True, "_compat copies identical")
    return (False, "memory/db-tools/_compat.py != memory/scripts/_compat.py")


def find_bare_text_true(source: str) -> list[int]:
    """Line numbers of subprocess.* calls whose text=True keyword has no
    encoding= sibling. The v2.4 BUG-1/4 class: text=True decodes child
    output with the ANSI code page on Windows (cp1251) — mojibake or
    UnicodeDecodeError on Cyrillic (audit 2026-08-22 M3). AST-based:
    docstrings/strings mentioning the pattern never match."""
    try:
        import ast
        tree = ast.parse(source)
    except SyntaxError:
        return []  # unparsable files are another gate's problem
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", "")
        if name not in ("run", "Popen", "check_output", "check_call"):
            continue
        has_text_true = any(
            k.arg == "text" and getattr(k.value, "value", None) is True
            for k in node.keywords)
        has_encoding = any(k.arg == "encoding" for k in node.keywords)
        if has_text_true and not has_encoding:
            hits.append(node.lineno)
    return sorted(hits)


def check_encoding_discipline() -> tuple[bool, str]:
    """No bare text=True subprocess calls in engine/script code — each one
    is a latent cp1251 mojibake bug on Windows (use _compat.run, or pass
    encoding='utf-8', errors='replace')."""
    bad = []
    patterns = ("memory/db-tools/*.py", "memory/scripts/*.py",
                "scripts/*.py", "scripts/tools/*.py", "eval/*.py")
    for pattern in patterns:
        for p in sorted(KIT.glob(pattern)):
            for ln in find_bare_text_true(
                    p.read_text(encoding="utf-8", errors="replace")):
                bad.append(f"{p.relative_to(KIT).as_posix()}:{ln}")
    return (not bad, "no bare text=True" if not bad else "; ".join(bad[:5]))


def check_reflex_commands() -> tuple[bool, str]:
    """A documented reflex command must actually speak: run
    context-monitor --check with a clean CONTEXT_* env and require exit 0
    + non-empty stdout (before v2.7.4 it was a silent no-op — the OPS §7
    reflex could never fire; audit 2026-08-22 M2)."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("CONTEXT_")}
    try:
        r = subprocess.run(
            [sys.executable,
             str(KIT / "scripts" / "context-monitor.py"), "--check"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return (False, f"context-monitor --check failed to run: {e}")
    if r.returncode != 0 or not r.stdout.strip():
        return (False, f"context-monitor --check: rc={r.returncode}, "
                       "stdout empty (reflex commands must print status)")
    return (True, "context-monitor --check speaks (exit 0 + status line)")


def main() -> int:
    checks = [
        ("manifest", check_manifest()),
        ("versions", check_versions()),
        ("frontmatter", check_frontmatter()),
        ("file-size gate", check_gate()),
        ("memory+db", check_memory()),
        ("adapters", check_adapters()),
        ("override", check_override()),
        ("engine sync", check_engine_sync()),
        ("reflex commands", check_reflex_commands()),
        ("encoding discipline", check_encoding_discipline()),
    ]
    fails = 0
    print(f"{'CHECK':<16} {'RESULT':<6} DETAIL")
    for name, (ok, detail) in checks:
        fails += 0 if ok else 1
        print(f"{name:<16} {'OK' if ok else 'FAIL':<6} {detail}")
    print(f"\n== {'All systems GREEN' if not fails else str(fails) + ' FAILURES'}"
          f" ({len(checks)} checks) ==")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())