#!/usr/bin/env python3
"""build.py regression tests for the defects that bit the kit live:

- a text file flipped to binary kept a stale FTS row forever
- 'build.py -r <project>' without -o destroyed wiki.db
- a BOM-prefixed skip.local silently disabled its first entry
- skip.local itself leaked into shared databases

Run: python -m unittest discover -s tests -v
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


def _run(args, env):
    return subprocess.run([sys.executable, str(BUILD)] + args,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kit-build-"))
        self.root = self.tmp / "mem"
        (self.root / "db").mkdir(parents=True)
        (self.root / "VERSION").write_text("2.7\n", encoding="utf-8")
        (self.root / "db-tools").mkdir()
        (self.root / "scripts").mkdir()
        shutil.copy2(KIT / "memory" / "scripts" / "_compat.py",
                     self.root / "scripts" / "_compat.py")
        self.env = dict(os.environ, MEMORY_ROOT=str(self.root))
        self.proj = self.tmp / "proj"
        self.proj.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _files(self, db):
        con = sqlite3.connect(db)
        rows = [r[0] for r in con.execute("SELECT rel_path FROM files")]
        con.close()
        return rows

    def test_binary_flip_drops_stale_row(self):
        (self.proj / "flip.txt").write_text("hello searchable text",
                                            encoding="utf-8")
        db = self.tmp / "p.db"
        self.assertEqual(_run(["-r", str(self.proj), "-o", str(db)],
                              self.env).returncode, 0)
        self.assertIn("flip.txt", self._files(db))
        (self.proj / "flip.txt").write_bytes(b"A" * 5000 + b"\x00" + b"B")
        self.assertEqual(_run(["-r", str(self.proj), "-o", str(db)],
                              self.env).returncode, 0)
        self.assertNotIn("flip.txt", self._files(db))

    def test_project_build_without_o_spares_wiki(self):
        (self.proj / "code.py").write_text("def f():\n    return 1\n",
                                           encoding="utf-8")
        self.assertEqual(_run(["-r", str(self.proj)], self.env).returncode, 0)
        self.assertTrue((self.root / "db" / "proj.db").is_file())
        self.assertFalse((self.root / "db" / "wiki.db").is_file())

    def test_bom_skip_local_still_skips(self):
        (self.proj / "secret").mkdir()
        (self.proj / "secret" / "p.md").write_text("private", encoding="utf-8")
        (self.proj / "skip.local").write_text("\ufeffsecret\n",
                                              encoding="utf-8")
        db = self.tmp / "p.db"
        self.assertEqual(_run(["-r", str(self.proj), "-o", str(db)],
                              self.env).returncode, 0)
        rows = self._files(db)
        self.assertFalse(any("secret" in r for r in rows))
        self.assertFalse(any("skip.local" in r for r in rows))


if __name__ == "__main__":
    unittest.main()
