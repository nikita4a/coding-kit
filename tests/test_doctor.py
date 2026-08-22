#!/usr/bin/env python3
"""doctor.py contract tests for the v2.8 self-verifying checks.

The audit (2026-08-22) showed doctor was 8/8 GREEN while 4 MAJOR defects
existed. The two new checks encode the missed classes:
- reflex commands that cannot fire (silent no-op --check)
- bare text=True subprocess calls (cp1251 mojibake class)
"""
import importlib.util
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "doctor", KIT / "scripts" / "doctor.py")
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class FindBareTextTrueTest(unittest.TestCase):
    def test_bare_text_true_flagged(self):
        src = "r = subprocess.run(cmd, capture_output=True, text=True)"
        self.assertEqual(doctor.find_bare_text_true(src), [1])

    def test_encoding_nearby_passes(self):
        src = ("r = subprocess.run(cmd, capture_output=True, text=True,\n"
               "    encoding='utf-8', errors='replace')")
        self.assertEqual(doctor.find_bare_text_true(src), [])

    def test_line_numbers_reported(self):
        src = ("a = 1\nb = 2\n"
               "subprocess.run(cmd, text=True)\n"
               "c = subprocess.run(cmd2, text=True, encoding='utf-8')\n"
               "subprocess.run(cmd3, text=True)\n")
        self.assertEqual(doctor.find_bare_text_true(src), [3, 5])


class DoctorChecksTest(unittest.TestCase):
    def test_encoding_discipline_green_on_tree(self):
        ok, detail = doctor.check_encoding_discipline()
        self.assertTrue(ok, detail)

    def test_reflex_commands_green_on_tree(self):
        ok, detail = doctor.check_reflex_commands()
        self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
