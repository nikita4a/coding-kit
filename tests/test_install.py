#!/usr/bin/env python3
"""install.py contract tests (stdlib unittest, no deps).

Covers the silent-failure class that bit the kit three times:
layout creation, idempotent re-run, engine link re-pointing,
real-dir preservation, smoke exit-code propagation.

Run: python -m unittest discover -s tests -v
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "install_under_test", KIT / "scripts" / "install.py")
install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install)

PROBE = "memory is a database"  # smoke query; indexed so search returns 0

def _make_foreign_link(target: Path, dest: Path) -> None:
    """Create a link (junction on NT, symlink elsewhere) target -> dest."""
    if os.name == "nt":
        env = dict(os.environ, KIT_LINK_PATH=str(target),
                   KIT_LINK_TARGET=str(dest))
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "New-Item -ItemType Junction -Path $env:KIT_LINK_PATH "
             "-Target $env:KIT_LINK_TARGET | Out-Null"],
            check=True, env=env)
    else:
        target.symlink_to(dest, target_is_directory=True)


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kit-install-"))
        self.root = self.tmp / "mem"
        # a probe post makes the post-install smoke search succeed
        (self.root / "Wiki" / "reference").mkdir(parents=True)
        (self.root / "Wiki" / "reference" / "probe.md").write_text(
            "---\ntype: reference\ntitle: probe\n---\n"
            "memory is a database, not a conversation\n", encoding="utf-8")
        self._env = os.environ.get("MEMORY_ROOT")
        os.environ["MEMORY_ROOT"] = str(self.root)

    def tearDown(self):
        if self._env is None:
            os.environ.pop("MEMORY_ROOT", None)
        else:
            os.environ["MEMORY_ROOT"] = self._env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_fresh_install_creates_layout(self):
        self.assertEqual(install.main(), 0)
        self.assertTrue((self.root / "VERSION").is_file())
        for t in install.WIKI_TYPES:
            self.assertTrue((self.root / "Wiki" / t).is_dir(), t)
        self.assertTrue((self.root / "db").is_dir())
        self.assertTrue((self.root / "scripts" / "memory-warmup.py").is_file())
        self.assertTrue((self.root / "scripts" / "_compat.py").is_file())
        link = self.root / "db-tools"
        self.assertTrue(install._is_link(link))
        self.assertEqual(link.resolve(), install.ENGINE.resolve())

    def test_rerun_is_idempotent(self):
        self.assertEqual(install.main(), 0)
        self.assertEqual(install.main(), 0)

    def test_foreign_link_is_repointed(self):
        foreign = self.tmp / "other-engine"
        foreign.mkdir()
        _make_foreign_link(self.root / "db-tools", foreign)
        self.assertEqual(install.main(), 0)
        self.assertEqual((self.root / "db-tools").resolve(),
                         install.ENGINE.resolve())

    def test_real_dir_is_preserved(self):
        real = self.root / "db-tools"
        real.mkdir(parents=True)
        (real / "precious.txt").write_text("data", encoding="utf-8")
        self.assertEqual(install.main(), 0)
        self.assertTrue((real / "precious.txt").is_file())
        self.assertFalse(install._is_link(real))

    def test_smoke_failure_fails_install(self):
        real_run = subprocess.run

        def fake_run(cmd, **kw):
            if "search_all.py" in str(cmd[1]):
                return subprocess.CompletedProcess(cmd, 1, "", "boom")
            return real_run(cmd, **kw)

        with mock.patch.object(install.subprocess, "run", side_effect=fake_run):
            self.assertEqual(install.main(), 1)


if __name__ == "__main__":
    unittest.main()
