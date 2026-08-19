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


def link_engine(root: Path) -> None:
    target = root / "db-tools"
    if target.exists() or target.is_symlink():
        print(f"  db-tools link/source already at {target}")
        return
    if os.name == "nt":
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"New-Item -ItemType Junction -Path '{target}' "
             f"-Target '{ENGINE}' | Out-Null"],
            check=True,
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

    legacy = KIT.parent / "memory"
    if legacy.exists() and legacy.resolve() != root.resolve():
        # old layout: data next to the kit ("../memory") before the
        # ~/.memory convention — do not move user data silently
        print(f"  NOTE: legacy data found at {legacy}. Move its Wiki posts "
              f"into {root / 'Wiki'}/<type>/ or set MEMORY_ROOT={legacy}.")

    link_engine(root)
    build_indexes(root)

    smoke = subprocess.run(
        [sys.executable, str(ENGINE / "search_all.py"), "memory is a database"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    combined = (smoke.stdout or "") + (smoke.stderr or "")
    ok = "Traceback" not in combined and "Error" not in combined
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