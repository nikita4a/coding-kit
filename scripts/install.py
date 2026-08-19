#!/usr/bin/env python3
"""install.py — coding-kit bootstrap: private memory layout + engine link.

One clone -> one command -> a working kit with its own cross-chat memory.

Creates (idempotent, nothing personal is ever written by this script):
    ~/.memory/Wiki/<reference|howto|errors|decisions|ideas>/
    ~/.memory/db/                      (empty indexed DBs)
    ~/.memory/scripts/                 (memory-warmup.py + _compat.py)
    ~/.memory/VERSION                  (engine marker, schema 2.7)
    ~/.memory/db-tools  ->  <kit>/memory/db-tools   (junction on Windows,
                                                      symlink elsewhere)

Then builds empty indexes and smoke-tests the search. Safe to re-run.

Usage:
    python scripts/install.py           # default root ~/.memory
    MEMORY_ROOT=/x/y python scripts/install.py   # custom root
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KIT = Path(__file__).resolve().parents[1]
ENGINE = KIT / "memory" / "db-tools"
WIKI_TYPES = ("reference", "howto", "errors", "decisions", "ideas")
ENGINE_VERSION = "2.7"


def memory_root() -> Path:
    env = os.environ.get("MEMORY_ROOT")
    return Path(env).expanduser() if env else Path.home() / ".memory"


def _is_link(p: Path) -> bool:
    """True for symlinks and Windows junctions (is_symlink() misses the
    latter; Path.is_junction() needs py3.12, the kit supports 3.8+)."""
    if p.is_symlink():
        return True
    try:
        os.readlink(p)
        return True
    except OSError:
        return False


def link_engine(root: Path) -> None:
    """Point <root>/db-tools at this kit's engine (the link follows the
    last installer). A pre-existing link is re-pointed; a real directory
    is left alone (never destroy what may be data)."""
    target = root / "db-tools"
    if _is_link(target):
        if target.resolve() == ENGINE.resolve():
            print("  db-tools already linked to this kit")
            return
        os.rmdir(target)  # removes the link, not its target
    elif target.exists():
        print(f"  NOTE: {target} is a real directory; replace it manually "
              f"to use this kit's engine.")
        return
    if os.name == "nt":
        # paths travel via env, not -Command text: no injection, and
        # $args is unavailable in -Command mode (script-only)
        env = dict(os.environ, KIT_LINK_PATH=str(target),
                   KIT_LINK_TARGET=str(ENGINE))
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "New-Item -ItemType Junction -Path $env:KIT_LINK_PATH "
             "-Target $env:KIT_LINK_TARGET | Out-Null"],
            check=True, env=env,
        )
    else:
        target.symlink_to(ENGINE, target_is_directory=True)
    print(f"  linked {target} -> {ENGINE}")


def build_indexes(root: Path) -> None:
    build = subprocess.run(
        [sys.executable, str(ENGINE / "build.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if build.returncode != 0:
        print("  build.py WARN:\n" + (build.stderr or build.stdout)[:500])


def main() -> int:
    root = memory_root()
    print(f"coding-kit install -> {root}")
    for d in [root / "db", root / "scripts"] + [
            root / "Wiki" / t for t in WIKI_TYPES]:
        d.mkdir(parents=True, exist_ok=True)
    (root / "VERSION").write_text(
        ENGINE_VERSION + "\n", encoding="utf-8", newline="\n")

    for name in ("memory-warmup.py", "_compat.py"):
        src = KIT / "memory" / "scripts" / name
        if src.exists():
            shutil.copy2(src, root / "scripts" / name)
    legacy = KIT.parent / "memory"
    if legacy.exists() and legacy.resolve() != root.resolve():
        # old layout: data next to the kit ("../memory") before the
        # ~/.memory convention — do not move user data silently
        print(f"  NOTE: legacy data found at {legacy}. Move its Wiki posts "
              f"into {root / 'Wiki'}/<type>/ or set MEMORY_ROOT={legacy}.")

    link_engine(root)
    build_indexes(root)

    smoke = subprocess.run(
        # probe token from the root's own scripts (memory-warmup.py):
        # indexed on every OS, unlike engine-link traversal
        [sys.executable, str(ENGINE / "search_all.py"), "warmup"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    ok = smoke.returncode == 0 and bool(smoke.stdout.strip())
    print("\n---")
    print("Install done. Layout:")
    print(f"  Wiki/: {root / 'Wiki'} (your knowledge — personal, never committed)")
    print(f"  db/  : {root / 'db'} (indexes, gitignored)")
    print(f"  engine: {root / 'db-tools'} (linked to the kit)")
    print(f"  search smoke: {'OK' if ok else smoke.stderr[:300]}")
    print("\nNow follow README.md -> Install section for your environment "
          "(rules file + skills).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())