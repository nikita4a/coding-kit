#!/usr/bin/env python3
"""context-monitor.py contract tests (audit 2026-08-22, M2).

Before the fix --check printed NOTHING (JSON suppressed, no summary) and
warn/critical were indistinguishable (both exit 1) — the OPS/AGENTS reflex
'run --check every ~10 turns' could never actually fire.

Contract after the fix:
    --check always prints a one-line status (+ warnings, recommendation)
    exit codes: 0 = ok, 1 = warn, 2 = critical
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
MONITOR = KIT / "scripts" / "context-monitor.py"


def _run(args, env=None):
    e = {k: v for k, v in os.environ.items()
         if not k.startswith("CONTEXT_")}
    if env:
        e.update(env)
    return subprocess.run([sys.executable, str(MONITOR)] + args,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=e, timeout=30)


class CheckOutputTest(unittest.TestCase):
    def test_ok_check_prints_status_and_exits_zero(self):
        r = _run(["--check"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("ok", r.stdout.lower())

    def test_warn_check_prints_and_exits_one(self):
        r = _run(["--check", "--turns", "120"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("warn", r.stdout.lower())
        self.assertTrue(r.stdout.strip(), "--check must not be silent")

    def test_critical_check_prints_and_exits_two(self):
        r = _run(["--check", "--turns", "160"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("critical", r.stdout.lower())

    def test_json_output_unchanged(self):
        import json
        r = _run(["--json", "--turns", "130"])
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["status"], "warn")


if __name__ == "__main__":
    unittest.main()
