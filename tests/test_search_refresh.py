#!/usr/bin/env python3
"""search.py --refresh guard regression tests (audit 2026-08-22, M1).

The same defect class as the closed v2.6 'build -r X without -o destroyed
wiki.db': --refresh runs build.py with whatever (-r, -b) pair it was given.
A mismatched pair silently rebuilds one root into another root's index.

Contract after the fix: --refresh allows only the (root, db) pair that
build.py itself would derive for that root; anything else needs
--force-refresh.
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
BUILD = KIT / "memory" / "db-tools" / "build.py"
SEARCH = KIT / "memory" / "db-tools" / "search.py"


def _run(script, args, env):
    return subprocess.run([sys.executable, str(script)] + args,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


class _FakeMemory:
    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kit-refresh-"))
        self.root = self.tmp / "mem"
        (self.root / "db").mkdir(parents=True)
        (self.root / "VERSION").write_text("2.7\n", encoding="utf-8")
        (self.root / "db-tools").mkdir()
        (self.root / "scripts").mkdir()
        shutil.copy2(KIT / "memory" / "scripts" / "_compat.py",
                     self.root / "scripts" / "_compat.py")
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith("PYTHON")}
        self.env["MEMORY_ROOT"] = str(self.root)
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        (self.proj / "code.py").write_text("hello project text\n",
                                           encoding="utf-8")

    def paths(self):
        wiki = self.root / "db" / "wiki.db"
        proj_db = self.root / "db" / "proj.db"
        return wiki, proj_db

    def rows(self, db):
        con = sqlite3.connect(db)
        rows = [r[0] for r in con.execute("SELECT rel_path FROM files")]
        con.close()
        return rows

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class RefreshGuardTest(unittest.TestCase):
    def setUp(self):
        self.fx = _FakeMemory()

    def tearDown(self):
        self.fx.close()

    def test_refresh_project_into_wiki_refused(self):
        fx = self.fx
        (fx.root / "Wiki").mkdir()
        (fx.root / "Wiki" / "post.md").write_text("hello wiki text",
                                                  encoding="utf-8")
        self.assertEqual(_run(BUILD, [], fx.env).returncode, 0)  # wiki.db
        wiki, _ = fx.paths()
        r = _run(SEARCH, ["--refresh", "-r", str(fx.proj), "hello"], fx.env)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("wiki", (r.stdout + r.stderr).lower())
        self.assertTrue(any("post.md" in p for p in fx.rows(wiki)),
                        "wiki.db must keep its own content")

    def test_refresh_root_into_project_db_refused(self):
        fx = self.fx
        self.assertEqual(
            _run(BUILD, ["-r", str(fx.proj)], fx.env).returncode, 0)  # proj.db
        _, proj_db = fx.paths()
        r = _run(SEARCH, ["-b", str(proj_db), "--refresh", "hello"], fx.env)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertTrue(any("code.py" in p for p in fx.rows(proj_db)),
                        "project index must keep its own content")

    def test_consistent_pair_allowed(self):
        fx = self.fx
        _, proj_db = fx.paths()
        r = _run(SEARCH, ["--refresh", "-r", str(fx.proj), "-b", str(proj_db),
                          "hello"], fx.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("code.py", r.stdout)

    def test_force_refresh_overrides_guard(self):
        fx = self.fx
        r = _run(SEARCH, ["--refresh", "-r", str(fx.proj), "--force-refresh",
                          "hello"], fx.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wiki, _ = fx.paths()
        self.assertTrue(any("code.py" in p for p in fx.rows(wiki)))


if __name__ == "__main__":
    unittest.main()
