#!/usr/bin/env python3
"""githist.py parse + encoding regression tests (audit 2026-08-22, M3/m1).

Two closed-here defects:
- CHANGELOG v2.6 claims a '40-hex commit boundary' in the log parser; the
  code accepted ANY 'a|b|c|d' line as a commit header. A filename with
  3+ pipes would be misparsed as a commit.
- git output was decoded with the ANSI code page on Windows (text=True
  without encoding=): Cyrillic commit subjects became permanent mojibake
  in research.db. Fix: route through _compat.run (utf-8 + PYTHONUTF8).
- empty commits (no files) were dropped from history.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
GITHIST = KIT / "memory" / "db-tools" / "githist.py"

sys.path.insert(0, str(KIT / "memory" / "db-tools"))
import githist  # noqa: E402

H = "0123456789abcdef0123456789abcdef01234567"  # 40 hex chars
H2 = "fedcba9876543210fedcba9876543210fedcba98"


def _log_text(*commits):
    """Render 'git log --name-only --pretty=%H|%ai|%an|%s' style output."""
    out = []
    for header, files in commits:
        out.append(header)
        out.extend(files)
        out.append("")  # blank line terminates each commit block
    return "\n".join(out)


class ParseLogTest(unittest.TestCase):
    def test_real_headers_parsed_with_files(self):
        commits = githist._parse_log(_log_text(
            (f"{H}|2026-08-20 10:00:00 +0300|Oleg|init", ["a.py", "b.py"]),
            (f"{H2}|2026-08-21 11:00:00 +0300|Oleg|second", ["c.py"]),
        ))
        self.assertEqual([c[0] for c in commits], [H, H2])
        self.assertEqual(commits[0][4], ["a.py", "b.py"])

    def test_pipe_filename_is_not_a_header(self):
        commits = githist._parse_log(_log_text(
            (f"{H}|2026-08-20 10:00:00 +0300|Oleg|init",
             ["weird|file|name|x.md"]),
        ))
        self.assertEqual(len(commits), 1, "4-segment line must not "
                                          "become a bogus commit")
        self.assertIn("weird|file|name|x.md", commits[0][4])

    def test_empty_commit_preserved(self):
        commits = githist._parse_log(_log_text(
            (f"{H}|2026-08-20 10:00:00 +0300|Oleg|allow-empty commit", []),
            (f"{H2}|2026-08-21 11:00:00 +0300|Oleg|second", ["c.py"]),
        ))
        self.assertEqual(len(commits), 2, "empty commits must survive")


@unittest.skipUnless(os.name == "nt", "cp1251 decode bug is Windows-only")
class CyrillicEncodingTest(unittest.TestCase):
    """End-to-end: a Cyrillic commit subject must land in research.db
    verbatim even when PYTHONUTF8 is off (PowerShell default)."""

    def test_cyrillic_subject_survives(self):
        if not shutil.which("git"):
            self.skipTest("git not on PATH")
        tmp = Path(tempfile.mkdtemp(prefix="kit-githist-"))
        try:
            root = tmp / "mem"
            (root / "db").mkdir(parents=True)
            (root / "VERSION").write_text("2.7\n", encoding="utf-8")
            (root / "db-tools").mkdir()
            (root / "scripts").mkdir()
            shutil.copy2(KIT / "memory" / "scripts" / "_compat.py",
                         root / "scripts" / "_compat.py")
            repo = tmp / "mem" / "projects" / "repo"
            repo.mkdir(parents=True)
            def git(*a):
                subprocess.run(["git", "-C", str(repo)] + list(a),
                               check=True, capture_output=True)
            git("init", "-q")
            git("config", "user.email", "t@t")
            git("config", "user.name", "Oleg")
            (repo / "f.txt").write_text("x", encoding="utf-8")
            git("add", "-A")
            # -m reads argv: pass the literal UTF-8 bytes via a file to be
            # independent of the console code page
            msg = repo / "msg.txt"
            msg.write_text("фикс кодировки кириллицы", encoding="utf-8")
            git("commit", "-q", "--allow-empty", "-F", str(msg))
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith("PYTHON")}
            env["MEMORY_ROOT"] = str(root)
            r = subprocess.run(
                [sys.executable, str(GITHIST), "refresh"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env, timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            con = sqlite3.connect(root / "db" / "research.db")
            subjects = [row[0] for row in con.execute(
                "SELECT subject FROM commits")]
            con.close()
            self.assertIn("фикс кодировки кириллицы", subjects)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
