#!/usr/bin/env python3
"""kitctl — one command for the kit's own lifecycle and gates.

Thin dispatcher: every subcommand delegates to the existing script with
its working directory at the kit root; no logic lives here (YAGNI — the
scripts ARE the logic, kitctl only removes the need to remember paths).

Usage:
    python scripts/kitctl.py install      # bootstrap/refresh ~/.memory
    python scripts/kitctl.py doctor       # 10 self-diagnostic checks
    python scripts/kitctl.py gate         # file-size gate (--ci)
    python scripts/kitctl.py eval         # trap-suite (dry-run validate)
    python scripts/kitctl.py triggers     # trigger queries validation
    python scripts/kitctl.py tests        # unit tests (unittest discover)
    python scripts/kitctl.py warmup       # cross-chat memory warmup
    python scripts/kitctl.py checkpoint   # markdown handoff block
    python scripts/kitctl.py context      # context overflow check
"""
import argparse
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]

COMMANDS = {  # name -> (argv tail, help)
    "install": (["scripts/install.py"], "bootstrap/refresh ~/.memory"),
    "doctor": (["scripts/doctor.py"], "self-diagnostic (10 checks)"),
    "gate": (["scripts/tools/check_file_sizes.py", "--ci"],
             "file-size gate"),
    "eval": (["eval/runner.py"], "trap-suite (dry-run validation)"),
    "triggers": (["eval/trigger_eval.py", "--queries",
                  "eval/trigger_queries.json"], "trigger queries validation"),
    "tests": (["-m", "unittest", "discover", "-s", "tests"],
              "unit tests"),
    "warmup": (["memory/scripts/memory-warmup.py"],
               "cross-chat memory warmup"),
    "checkpoint": (["scripts/context-monitor.py", "--dump-checkpoint"],
                   "markdown handoff block for a fresh chat"),
    "context": (["scripts/context-monitor.py", "--check"],
                "context overflow check (0=ok 1=warn 2=critical)"),
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="coding-kit lifecycle: one command, all gates")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, (_tail, help_text) in COMMANDS.items():
        sub.add_parser(name, help=help_text)
    args = ap.parse_args()

    tail = COMMANDS[args.cmd][0]
    argv = ([sys.executable, "-m", "unittest"] if tail[0] == "-m"
            else [sys.executable, str(KIT / tail[0])]) + tail[1:]
    return subprocess.run(argv, cwd=KIT).returncode


if __name__ == "__main__":
    sys.exit(main())
