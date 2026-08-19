#!/usr/bin/env python3
"""_compat.chulan_root / _validate_root contract tests.

The root resolver must never guess silently: explicit env wins,
relative env dies, marker-less roots die loudly.

Run: python -m unittest discover -s tests -v
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "compat_under_test", KIT / "memory" / "scripts" / "_compat.py")
compat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compat)


def _seed(root: Path) -> None:
    (root / "db-tools").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "_compat.py").write_text("# marker", encoding="utf-8")
    (root / "VERSION").write_text("2.7\n", encoding="utf-8")


class ChulanRootTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kit-root-"))
        self._env = os.environ.get("MEMORY_ROOT")

    def tearDown(self):
        if self._env is None:
            os.environ.pop("MEMORY_ROOT", None)
        else:
            os.environ["MEMORY_ROOT"] = self._env
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_env_root_wins(self):
        _seed(self.tmp)
        os.environ["MEMORY_ROOT"] = str(self.tmp)
        self.assertEqual(compat.chulan_root().resolve(), self.tmp.resolve())

    def test_relative_env_dies(self):
        os.environ["MEMORY_ROOT"] = "relative/path"
        with self.assertRaises(RuntimeError):
            compat.chulan_root()

    def test_markerless_env_root_dies(self):
        os.environ["MEMORY_ROOT"] = str(self.tmp)
        with self.assertRaises(RuntimeError) as ctx:
            compat.chulan_root()
        self.assertIn("VERSION", str(ctx.exception))

    def test_file_fallback_needs_markers(self):
        # no MEMORY_ROOT, no ~/.memory on a clean box -> __file__ fallback
        # must validate the kit's memory/ dir, which lacks VERSION markers
        os.environ.pop("MEMORY_ROOT", None)
        home = Path.home() / ".memory"
        if home.exists():
            self.skipTest("~/.memory present on this machine")
        with self.assertRaises(RuntimeError):
            compat.chulan_root()


if __name__ == "__main__":
    unittest.main()
