#!/usr/bin/env python3
"""kitctl + install.py CLI-guard contract tests (v3.0).

- kitctl: one command dispatching the kit's own lifecycle/gates, thin
  (delegates to the existing scripts, no logic duplication);
- install.py must stop treating arbitrary argv as "yes, install":
  '--help' printed usage instead of running the installer.
"""
import subprocess
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
KITCTL = KIT / "scripts" / "kitctl.py"
INSTALL = KIT / "scripts" / "install.py"


def _run(script, args):
    return subprocess.run([sys.executable, str(script)] + args,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=180)


class KitctlTest(unittest.TestCase):
    def test_help_lists_commands(self):
        r = _run(KITCTL, ["--help"])
        self.assertEqual(r.returncode, 0)
        for cmd in ("install", "doctor", "gate", "eval", "triggers",
                    "tests", "warmup", "checkpoint", "context"):
            self.assertIn(cmd, r.stdout)

    def test_doctor_passes_through(self):
        r = _run(KITCTL, ["doctor"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("GREEN", r.stdout)

    def test_unknown_command_rejected(self):
        r = _run(KITCTL, ["nope"])
        self.assertNotEqual(r.returncode, 0)


class InstallCliGuardTest(unittest.TestCase):
    def test_help_prints_usage_and_does_not_install(self):
        r = _run(INSTALL, ["--help"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("usage", r.stdout.lower())
        self.assertNotIn("Install done", r.stdout)

    def test_unknown_arg_refused(self):
        r = _run(INSTALL, ["--frobnicate"])
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("Install done", r.stdout)


if __name__ == "__main__":
    unittest.main()
