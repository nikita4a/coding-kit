#!/usr/bin/env python3
"""scan_secrets: repo-wide secret scanner for coding-kit.

Scans text files for hardcoded secrets (API keys, tokens, passwords).
SEVERE findings block the build (exit 1); WARN findings print for manual review.

Usage:
    python scripts/scan_secrets.py          # text output, exit 1 on SEVERE
    python scripts/scan_secrets.py --json   # JSON output
    python scripts/scan_secrets.py --ci     # alias for text + exit 1 on SEVERE
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

TEXT_EXTS: frozenset[str] = frozenset({
    ".py", ".md", ".json", ".toml", ".sh", ".yaml", ".yml", ".txt",
    ".cfg", ".ini", ".ps1", ".env", ".js", ".ts", ".tsx", ".jsx",
    ".css", ".html", ".sql", ".rb", ".go", ".rs", ".java", ".kt",
})

MAX_SECRET_FILE: int = 1_048_576  # 1 MiB — skip binary-sized files

EXCLUDE_DIRS: frozenset[str] = frozenset({
    ".git", "__pycache__", "node_modules", ".venv",
})

# SEVERE: high-signal patterns — blocks build if found
SECRET_PATTERNS_SEVERE: list[re.Pattern] = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|auth[_-]?token|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_-]{20,}['\"]"),
]

# WARN: generic suspicion — prints for manual review, does not block
SECRET_PATTERNS_WARN: list[re.Pattern] = [
    re.compile(r"(?i)(secret|password|token|passwd)\s*[:=]\s*['\"][A-Za-z0-9_-]{16,}['\"]"),
]

Finding = tuple[str, str, str]  # (path, pattern_snippet, match_snippet)


def _should_exclude_dir(dirpath: str) -> bool:
    """Check if any path component is an excluded directory."""
    parts = Path(dirpath).parts
    return any(p in EXCLUDE_DIRS for p in parts)


def collect_text_files(root: Path) -> list[Path]:
    """Walk root, collect text files, skip excluded dirs."""
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        if _should_exclude_dir(dirpath):
            dirnames[:] = []
            continue
        keep: list[str] = []
        for d in dirnames:
            if d not in EXCLUDE_DIRS:
                keep.append(d)
        dirnames[:] = keep
        for f in filenames:
            full = Path(dirpath) / f
            if not full.is_file():
                continue
            if full.suffix.lower() not in TEXT_EXTS:
                continue
            files.append(full)
    return sorted(files)


def scan_secrets(root: Path | None = None) -> tuple[list[Finding], list[Finding]]:
    """Scan repo for secrets. Returns (severe, warn) findings.

    Each finding is (relative_path, pattern_snippet, match_snippet).
    """
    root = root or ROOT
    files = collect_text_files(root)
    severe: list[Finding] = []
    warn: list[Finding] = []

    for f in files:
        try:
            if f.stat().st_size > MAX_SECRET_FILE:
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for level, patterns in (
            ("severe", SECRET_PATTERNS_SEVERE),
            ("warn", SECRET_PATTERNS_WARN),
        ):
            for pat in patterns:
                match = pat.search(text)
                if match:
                    rel = str(f.relative_to(root))
                    finding = (rel, pat.pattern[:48], match.group(0)[:32])
                    (severe if level == "severe" else warn).append(finding)
                    break  # one match per pattern per file

    return severe, warn


def _format_finding(kind: str, finding: Finding) -> str:
    """Format a single finding as a human-readable line."""
    path, pattern, match = finding
    if kind == "severe":
        return f"  SEVERE {path}: {pattern} … {match}"
    return f"  WARN  {path}: {pattern} … {match}"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Exit 1 if any SEVERE findings, 0 otherwise."""
    args = _parse_args(argv)
    root = args.root or ROOT
    severe, warn = scan_secrets(root)

    if args.json:
        output = {
            "root": str(root),
            "severe": [{"path": p, "pattern": pat, "match": m} for p, pat, m in severe],
            "warn": [{"path": p, "pattern": pat, "match": m} for p, pat, m in warn],
        }
        print(json.dumps(output, ensure_ascii=False, indent=1))
    else:
        for finding in severe:
            print(_format_finding("severe", finding), file=sys.stderr)
        for finding in warn:
            print(_format_finding("warn", finding))

    if severe:
        if not args.json:
            print(f"\n✗ {len(severe)} SEVERE secret(s) found — blocking", file=sys.stderr)
        return 1
    if not args.json:
        print(f"✓ scan complete: 0 severe, {len(warn)} warn")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    import argparse  # noqa: PLC0415 — lazy import to keep stdlib-only at top
    parser = argparse.ArgumentParser(
        prog="scan_secrets",
        description="Scan repo for hardcoded secrets (API keys, tokens, passwords).",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--ci", action="store_true",
        help="Run in CI mode (exit 1 on SEVERE findings, text output)",
    )
    parser.add_argument("--root", type=Path, default=None, help="Root directory to scan")
    parsed = parser.parse_args(argv)
    if parsed.ci:
        parsed.json = False
    return parsed


if __name__ == "__main__":
    sys.exit(main())