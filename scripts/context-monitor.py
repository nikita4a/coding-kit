#!/usr/bin/env python3
"""context-monitor.py — Context overflow detection for AI agents.

Checks if the current conversation context is approaching limits
and suggests the user start a fresh chat. Designed to be called
periodically by the agent or at session end.

Usage:
    python scripts/context-monitor.py                    # check from env
    python scripts/context-monitor.py --turns 120        # check by turn count
    python scripts/context-monitor.py --tokens 800000    # check by token estimate
    python scripts/context-monitor.py --check            # quick check, exit 0=ok 1=warn

Environment variables (set by agent):
    CONTEXT_TURNS=120      - current turn count
    CONTEXT_TOKENS=500000  - estimated token usage
    CONTEXT_MAX=1000000    - context window size (default 1M)
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Thresholds — tuned for 1M token context windows (2026)
TURN_WARN = 100     # Suggest new chat after N turns
TURN_CRITICAL = 150 # Strongly recommend
TOKEN_WARN_RATIO = 0.80   # 80% of context window
TOKEN_CRITICAL_RATIO = 0.90  # 90% of context window


def check(turns: int = None, tokens: int = None, max_tokens: int = None) -> dict:
    """Check context health. Returns dict with status and recommendations."""
    result = {
        "timestamp": datetime.now().isoformat(),
        "status": "ok",
        "warnings": [],
        "recommendation": None,
    }

    # Turn-based check
    if turns is not None:
        if turns >= TURN_CRITICAL:
            result["status"] = "critical"
            result["warnings"].append(
                f"Turn count {turns} >= {TURN_CRITICAL}. "
                "Context is very large. Strongly recommend starting a new chat."
            )
        elif turns >= TURN_WARN:
            result["status"] = "warn"
            result["warnings"].append(
                f"Turn count {turns} >= {TURN_WARN}. "
                "Consider starting a new chat soon to preserve agent performance."
            )

    # Token-based check
    if tokens is not None and max_tokens is not None:
        ratio = tokens / max_tokens
        if ratio >= TOKEN_CRITICAL_RATIO:
            result["status"] = "critical"
            result["warnings"].append(
                f"Token usage {tokens}/{max_tokens} ({ratio:.0%}). "
                "Context near limit. Start a new chat NOW."
            )
        elif ratio >= TOKEN_WARN_RATIO:
            if result["status"] != "critical":
                result["status"] = "warn"
            result["warnings"].append(
                f"Token usage {tokens}/{max_tokens} ({ratio:.0%}). "
                "Context filling up. Plan to start a new chat."
            )

    # Build recommendation
    if result["status"] == "critical":
        result["recommendation"] = (
            "CONTEXT_OVERFLOW: Start a new chat immediately. "
            "Before switching:\n"
            "1. Run `python scripts/memory-warmup.py` to capture current context\n"
            "2. Note any open tasks/goals\n"
            "3. Start a fresh chat and say 'continue from previous session'\n"
            "4. The agent will load context from Wiki via memory-warmup"
        )
    elif result["status"] == "warn":
        result["recommendation"] = (
            "Context is getting large. Soon you should:\n"
            "1. Wrap up current task\n"
            "2. Run `python scripts/memory-warmup.py`\n"
            "3. Start a new chat"
        )

    return result


def dump_checkpoint() -> str:
    """Markdown block for a fresh-chat handoff: date, git state, task template."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        git = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=10,
        )
        changed = git.stdout.strip() or "(clean)"
    except Exception:
        changed = "(git unavailable)"
    return (
        f"## Session checkpoint — {now}\n\n"
        f"- Files touched:\n```\n{changed}\n```\n"
        "- Open tasks:\n  - [ ] \n\n"
        "- Verdict: continue / rollover to a new chat\n\n"
        "Save: `~/.memory/Wiki/log.md` → `python ~/.memory/db-tools/build.py` "
        "(portable) or project docs (project layer).\n"
    )


def main():
    import argparse


    p = argparse.ArgumentParser(description="Context overflow monitor")
    p.add_argument("--turns", type=int, help="Current turn count")
    p.add_argument("--tokens", type=int, help="Estimated token usage")
    p.add_argument("--max-tokens", type=int, default=1_000_000, help="Context window size")
    p.add_argument("--check", action="store_true", help="Quick check, exit 0=ok 1=warn")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--dump-checkpoint", action="store_true",
                   help="Print a markdown checkpoint block for a fresh chat")
    args = p.parse_args()

    if args.dump_checkpoint:
        print(dump_checkpoint())
        return

    # Read from env if not specified
    turns = args.turns or int(os.environ.get("CONTEXT_TURNS", 0)) or None
    tokens = args.tokens or int(os.environ.get("CONTEXT_TOKENS", 0)) or None
    max_tokens = args.max_tokens

    result = check(turns=turns, tokens=tokens, max_tokens=max_tokens)

    if args.json or not args.check:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.check:
        sys.exit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()