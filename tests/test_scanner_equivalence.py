#!/usr/bin/env python3
"""tests/test_scanner_equivalence.py — Equivalence and isolation tests for file_scanner and build.py.

Verifies:
1. Re-export identity between build.py and file_scanner.py for all constants/functions.
2. Behavioral scanner unit tests on a deterministic temporary mixed fixture:
   - skip.local with UTF-8 BOM, comments, empty lines, and directory vs file partitioning.
   - .gitignore directory vs fnmatch pattern parsing and filtering.
   - Binary / artifact exclusion (service files, extensions, binary content).
   - Content hashing (SHA-256 authority, replacement on invalid UTF-8).
   - External extra file collection (real paths vs non-existent).
   - scan_files filtering equivalence with and without gitignore.
3. End-to-end build equivalence and database row snapshots (real entrypoint via subprocess):
   - Full build vs incremental build produces identical normalized rows on an unchanged fixture.
   - Normalized row snapshots for files, symbols, imports, calls, inherits, errors,
     FTS-visible content (files_fts, files_fts_trigram), and meta (schema definition).
   - Incremental build updates modified and added files while keeping unchanged rows identical.
   - Incremental build drops deleted files and binary flips (no stale FTS rows).
   - Touch updates (mtime change with identical content) do not rewrite content or FTS.

Run: python -m unittest discover -s tests -v
"""
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
DB_TOOLS = KIT / "memory" / "db-tools"
SCRIPTS = KIT / "memory" / "scripts"
BUILD_PY = DB_TOOLS / "build.py"

if str(DB_TOOLS) not in sys.path:
    sys.path.insert(0, str(DB_TOOLS))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# file_scanner has no import-time side effects (fnmatch/hashlib/os only).
import file_scanner


def _snapshot_db(db_path):
    """Capture normalized database row snapshots across all semantic tables and FTS.

    Deliberately excludes volatile columns (ids, mtime) so "unchanged" can be
    asserted as exact row equality across full and incremental builds.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    files = cur.execute(
        "SELECT rel_path, ext, size_bytes, lines, symbols_count, content_hash, content "
        "FROM files ORDER BY rel_path"
    ).fetchall()

    symbols = cur.execute(
        "SELECT rel_path, name, kind, line, signature "
        "FROM symbols ORDER BY rel_path, name, line"
    ).fetchall()

    imports = cur.execute(
        "SELECT rel_path, module, line FROM imports ORDER BY rel_path, module, line"
    ).fetchall()

    calls = cur.execute(
        "SELECT rel_path, callee, line FROM calls ORDER BY rel_path, callee, line"
    ).fetchall()

    inherits = cur.execute(
        "SELECT rel_path, child, base, line FROM inherits ORDER BY rel_path, child, base, line"
    ).fetchall()

    errors = cur.execute(
        "SELECT rel_path, line, message FROM errors ORDER BY rel_path, line"
    ).fetchall()

    fts = cur.execute(
        "SELECT rel_path, content FROM files_fts ORDER BY rel_path"
    ).fetchall()

    fts_trigram = cur.execute(
        "SELECT rel_path, content FROM files_fts_trigram ORDER BY rel_path"
    ).fetchall()

    meta = cur.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE type IN ('table', 'index', 'trigger') "
        "AND name NOT LIKE 'sqlite_%' "
        "AND name NOT LIKE 'files_fts_%' "
        "ORDER BY type, name"
    ).fetchall()

    con.close()
    return {
        "files": files,
        "symbols": symbols,
        "imports": imports,
        "calls": calls,
        "inherits": inherits,
        "errors": errors,
        "fts": fts,
        "fts_trigram": fts_trigram,
        "meta": meta,
    }


class _FakeRoot:
    """A disposable MEMORY_ROOT with the markers build.py's chulan_root validates."""

    def __init__(self, prefix):
        self.tmp = Path(tempfile.mkdtemp(prefix=prefix))
        self.root = self.tmp / "mem"
        (self.root / "db").mkdir(parents=True)
        (self.root / "VERSION").write_text("3.2\n", encoding="utf-8")
        (self.root / "db-tools").mkdir()
        (self.root / "scripts").mkdir()
        shutil.copy2(SCRIPTS / "_compat.py", self.root / "scripts" / "_compat.py")
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith("PYTHON")}
        self.env["MEMORY_ROOT"] = str(self.root)

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestScannerReExports(unittest.TestCase):
    """build.py must re-export file_scanner constants and functions as exact identities."""

    def _import_build(self):
        saved = os.environ.get("MEMORY_ROOT")
        os.environ["MEMORY_ROOT"] = str(self.fx.root)

        def _restore():
            if saved is None:
                os.environ.pop("MEMORY_ROOT", None)
            else:
                os.environ["MEMORY_ROOT"] = saved

        self.addCleanup(_restore)
        for mod in ("build", "_compat", "parsers"):
            sys.modules.pop(mod, None)
        import build  # noqa: F401 — resolves ROOT from MEMORY_ROOT env
        return build

    def setUp(self):
        self.fx = _FakeRoot("kit-scanner-reexport-")

    def tearDown(self):
        self.fx.close()

    def test_constant_identities(self):
        build = self._import_build()
        self.assertIs(build.DEFAULT_SKIP_DIRS, file_scanner.DEFAULT_SKIP_DIRS)
        self.assertIs(build.DEFAULT_SKIP_FILES, file_scanner.DEFAULT_SKIP_FILES)

    def test_function_identities(self):
        build = self._import_build()
        self.assertIs(build.collect_extra, file_scanner.collect_extra)
        self.assertIs(build.is_artifact, file_scanner.is_artifact)
        self.assertIs(build.load_gitignore, file_scanner.load_gitignore)
        self.assertIs(build.load_local_skip, file_scanner.load_local_skip)
        self.assertIs(build.read_hashed, file_scanner.read_hashed)
        self.assertIs(build.scan_files, file_scanner.scan_files)


class TestScannerBehavior(unittest.TestCase):
    """Behavioral unit tests for file_scanner functions on mixed fixtures."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kit-scanner-behavior-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_local_skip_bom_comments_and_partitioning(self):
        skip_file = self.tmp / "skip.local"
        # Mixed fixture: BOM header, comments, empty lines, directories and files
        skip_file.write_text(
            "\ufeff# Machine-specific exclusions\n"
            "local_secrets_dir\n"
            "custom_tools\n"
            "  # Indented comment\n"
            "secret_script.py\n"
            "local_doc.md\n"
            "temp_data.db\n"
            "notes.txt\n"
            "\n"
            "# Trailing comment\n",
            encoding="utf-8",
        )
        dirs, files = file_scanner.load_local_skip(str(self.tmp))
        self.assertEqual(dirs, {"local_secrets_dir", "custom_tools"})
        self.assertEqual(
            files,
            {"secret_script.py", "local_doc.md", "temp_data.db", "notes.txt"},
        )
        # BOM must not corrupt the first parsed entry
        self.assertNotIn("\ufefflocal_secrets_dir", dirs)
        self.assertIn("local_secrets_dir", dirs)

        # Missing skip.local returns empty sets without error
        missing_dirs, missing_files = file_scanner.load_local_skip(
            str(self.tmp / "nonexistent")
        )
        self.assertEqual(missing_dirs, set())
        self.assertEqual(missing_files, set())

    def test_load_gitignore_parsing(self):
        gi_file = self.tmp / ".gitignore"
        gi_file.write_text(
            "# Git ignore rules\n"
            "build_output\n"
            "/dist\n"
            "*.tmp\n"
            "cache_*\n"
            "test[0-9]\n"
            "!negated_rule\n"
            "\n",
            encoding="utf-8",
        )
        ignore_dirs, ignore_files = file_scanner.load_gitignore(str(self.tmp))
        self.assertEqual(ignore_dirs, {"build_output", "dist"})
        self.assertEqual(ignore_files, ["*.tmp", "cache_*", "test[0-9]"])

        # Missing .gitignore returns empty set and list
        empty_dirs, empty_files = file_scanner.load_gitignore(
            str(self.tmp / "nonexistent")
        )
        self.assertEqual(empty_dirs, set())
        self.assertEqual(empty_files, [])

    def test_is_artifact_classification(self):
        artifact_names = [
            "data.db", "data.db-shm", "data.db-wal", "data.db-journal",
            "source.py.bak", "main.py.orig",
            "image.png", "photo.jpg", "photo.jpeg", "anim.gif",
            "graphic.webp", "favicon.ico", "bitmap.bmp",
            "binary.exe", "library.dll", "module.so", "blob.bin",
            "document.pdf", "archive.zip", "bundle.tar", "archive.gz",
            "archive.7z", "package.rar", "lib.jar",
            "doc.docx", "sheet.xlsx", "slides.pptx",
            "UPPER.PNG", "UPPER.EXE",
        ]
        for name in artifact_names:
            self.assertTrue(
                file_scanner.is_artifact(name),
                f"Expected {name} to be classified as artifact",
            )

        source_names = [
            "main.py", "README.md", "script.sh", "config.json",
            "index.ts", "Component.jsx", "types.tsx", "notes.txt",
            "style.css", "schema.sql", "workflow.yml",
        ]
        for name in source_names:
            self.assertFalse(
                file_scanner.is_artifact(name),
                f"Expected {name} to be classified as source file",
            )

    def test_read_hashed_valid_and_binary_nul(self):
        # Valid UTF-8 text. Write exact bytes so the on-disk content is a
        # deterministic LF contract independent of host newline translation:
        # Path.write_text(..., encoding="utf-8") opens in text mode and would
        # translate "\n" to "\r\n" on Windows, changing the hashed bytes.
        text_file = self.tmp / "hello.txt"
        text_content = "Hello, world!\nLine 2 with utf-8: \u2713\n"
        text_bytes = text_content.encode("utf-8")
        text_file.write_bytes(text_bytes)
        h_text, content_text = file_scanner.read_hashed(str(text_file))
        # read_hashed is the SHA-256 authority over exact on-disk bytes.
        expected_hash = hashlib.sha256(text_bytes).hexdigest()
        self.assertEqual(h_text, expected_hash)
        self.assertEqual(content_text, text_content)

        # Binary content with NUL and invalid UTF-8 bytes
        bin_file = self.tmp / "binary.dat"
        bin_data = b"prefix\x00\xff\xfe\x80\x00suffix\n"
        bin_file.write_bytes(bin_data)
        h_bin, content_bin = file_scanner.read_hashed(str(bin_file))
        self.assertEqual(h_bin, hashlib.sha256(bin_data).hexdigest())
        self.assertIn("prefix\x00", content_bin)
        self.assertIn("\ufffd", content_bin)
        self.assertIn("suffix\n", content_bin)

    def test_collect_extra(self):
        extra1 = self.tmp / "extra1.md"
        extra2 = self.tmp / "extra2.txt"
        extra1.write_text("extra 1", encoding="utf-8")
        extra2.write_text("extra 2", encoding="utf-8")
        missing = self.tmp / "missing.txt"

        collected = file_scanner.collect_extra(
            [str(extra1), str(extra2), str(missing)]
        )
        self.assertEqual(
            set(collected.keys()),
            {os.path.abspath(str(extra1)), os.path.abspath(str(extra2))},
        )
        self.assertEqual(collected[os.path.abspath(str(extra1))][1], len("extra 1"))
        self.assertEqual(collected[os.path.abspath(str(extra2))][1], len("extra 2"))

        self.assertEqual(file_scanner.collect_extra(None), {})
        self.assertEqual(file_scanner.collect_extra([]), {})

    def test_scan_files_filtering_and_gitignore(self):
        root = self.tmp / "project"
        root.mkdir()

        (root / ".git").mkdir()
        (root / ".git" / "config").write_text("git config", encoding="utf-8")
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "cached.pyc").write_text("pyc", encoding="utf-8")
        (root / ".env").write_text("SECRET=1", encoding="utf-8")
        (root / "wiki.db").write_text("sqlite format", encoding="utf-8")
        (root / "skip.local").write_text("local", encoding="utf-8")

        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
        (root / "src" / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (root / "docs").mkdir()
        (root / "docs" / "guide.md").write_text("# Guide", encoding="utf-8")

        (root / "custom_skip_dir").mkdir()
        (root / "custom_skip_dir" / "file.txt").write_text("skip", encoding="utf-8")
        (root / "custom_skip.py").write_text("skip", encoding="utf-8")

        (root / "gi_dir").mkdir()
        (root / "gi_dir" / "nested.py").write_text("gi", encoding="utf-8")
        (root / "temp.tmp").write_text("temp", encoding="utf-8")

        (root / ".gitignore").write_text("gi_dir\n*.tmp\n", encoding="utf-8")

        # Without gitignore: directory/file skips + artifacts only
        scanned_no_gi = file_scanner.scan_files(
            str(root),
            skip_dirs=file_scanner.DEFAULT_SKIP_DIRS | {"custom_skip_dir"},
            skip_files=file_scanner.DEFAULT_SKIP_FILES | {"custom_skip.py"},
            use_gitignore=False,
        )
        expected_no_gi = {
            os.path.join("src", "main.py"),
            os.path.join("docs", "guide.md"),
            os.path.join("gi_dir", "nested.py"),
            "temp.tmp",
            ".gitignore",
        }
        self.assertEqual(set(scanned_no_gi.keys()), expected_no_gi)

        # With gitignore: gi_dir pruned as a directory, *.tmp pruned as a pattern
        scanned_gi = file_scanner.scan_files(
            str(root),
            skip_dirs=file_scanner.DEFAULT_SKIP_DIRS | {"custom_skip_dir"},
            skip_files=file_scanner.DEFAULT_SKIP_FILES | {"custom_skip.py"},
            use_gitignore=True,
        )
        expected_gi = {
            os.path.join("src", "main.py"),
            os.path.join("docs", "guide.md"),
            ".gitignore",
        }
        self.assertEqual(set(scanned_gi.keys()), expected_gi)


class TestBuildEquivalenceAndSnapshots(unittest.TestCase):
    """Equivalence tests invoking the real build entrypoint and snapshotting database rows."""

    def setUp(self):
        self.fx = _FakeRoot("kit-build-equivalence-")
        self.env = self.fx.env
        self.proj = self.fx.tmp / "sample_project"
        self.proj.mkdir()
        self.db = self.fx.tmp / "sample.db"
        self._create_fixture()

    def tearDown(self):
        self.fx.close()

    def _create_fixture(self):
        (self.proj / "src").mkdir(parents=True, exist_ok=True)
        (self.proj / "docs").mkdir(parents=True, exist_ok=True)
        (self.proj / "ignored_local_dir").mkdir(parents=True, exist_ok=True)

        (self.proj / "src" / "app.py").write_text(
            "import os\n"
            "import sys\n"
            "from math import sqrt\n\n"
            "class MathEngine:\n"
            "    def compute(self, x):\n"
            "        return sqrt(x)\n\n"
            "def calculate(val):\n"
            "    engine = MathEngine()\n"
            "    return engine.compute(val)\n",
            encoding="utf-8",
        )

        (self.proj / "docs" / "manual.md").write_text(
            "# System Manual\n\n"
            "Search keywords: token_alpha token_beta token_gamma.\n",
            encoding="utf-8",
        )

        # Artifact / service files that must never be indexed
        (self.proj / "src" / "asset.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (self.proj / "src" / "data.db-wal").write_bytes(b"wal data")
        (self.proj / "ignored_local_dir" / "secret.py").write_text(
            "SECRET_TOKEN = 'hidden'", encoding="utf-8"
        )
        (self.proj / "ignored_local.py").write_text(
            "LOCAL_KEY = 'ignored'", encoding="utf-8"
        )

        # BOM-prefixed skip.local (directory + file exclusions)
        (self.proj / "skip.local").write_text(
            "\ufeff# skip.local with BOM\n"
            "ignored_local_dir\n"
            "ignored_local.py\n",
            encoding="utf-8",
        )

    def _run_build(self, *extra_args):
        cmd = [
            sys.executable,
            str(BUILD_PY),
            "-r",
            str(self.proj),
            "-o",
            str(self.db),
        ]
        cmd.extend(extra_args)
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self.env,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"build.py failed with exit code {proc.returncode}:\n"
            f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}",
        )
        return proc

    def test_full_then_incremental_equivalence_on_unchanged_fixture(self):
        self._run_build("--full")
        snap_full = _snapshot_db(self.db)

        # Expected files indexed; skipped/artifact/binary files excluded
        indexed_paths = [r[0] for r in snap_full["files"]]
        self.assertIn(os.path.join("src", "app.py"), indexed_paths)
        self.assertIn(os.path.join("docs", "manual.md"), indexed_paths)
        self.assertFalse(any("ignored_local" in p for p in indexed_paths))
        self.assertFalse(any("asset.png" in p for p in indexed_paths))
        self.assertFalse(any("data.db-wal" in p for p in indexed_paths))
        self.assertFalse(any("skip.local" in p for p in indexed_paths))

        # FTS is populated with expected tokens
        con = sqlite3.connect(self.db)
        fts_match = con.execute(
            "SELECT rel_path FROM files_fts WHERE files_fts MATCH ?",
            ("token_alpha",),
        ).fetchall()
        con.close()
        self.assertEqual(len(fts_match), 1)
        self.assertEqual(fts_match[0][0], os.path.join("docs", "manual.md"))

        # Incremental build on the identical fixture
        self._run_build()
        snap_incr = _snapshot_db(self.db)

        # Exact snapshot equivalence across all semantic tables and FTS
        for key in ("files", "symbols", "imports", "calls", "inherits",
                    "errors", "fts", "fts_trigram", "meta"):
            self.assertEqual(
                snap_full[key],
                snap_incr[key],
                f"{key} must be identical between full and incremental build",
            )

    def test_incremental_change_add_delete_and_stale_fts_cleanup(self):
        self._run_build("--full")

        # 1. Modify src/app.py (add a new function)
        (self.proj / "src" / "app.py").write_text(
            "import os\n"
            "import sys\n"
            "from math import sqrt\n\n"
            "class MathEngine:\n"
            "    def compute(self, x):\n"
            "        return sqrt(x)\n\n"
            "def calculate(val):\n"
            "    engine = MathEngine()\n"
            "    return engine.compute(val)\n\n"
            "def multiply(a, b):\n"
            "    return a * b\n",
            encoding="utf-8",
        )

        # 2. Add a new file
        (self.proj / "src" / "extra.py").write_text(
            "def xylophone_extra():\n    return 'xylophone'\n",
            encoding="utf-8",
        )

        # 3. Delete docs/manual.md
        (self.proj / "docs" / "manual.md").unlink()

        self._run_build()
        snap_after = _snapshot_db(self.db)

        # Deleted file is gone from files + FTS (stale rows cleaned)
        deleted_rel = os.path.join("docs", "manual.md")
        self.assertNotIn(deleted_rel, [r[0] for r in snap_after["files"]])
        self.assertNotIn(deleted_rel, [r[0] for r in snap_after["fts"]])
        self.assertNotIn(deleted_rel, [r[0] for r in snap_after["fts_trigram"]])

        con = sqlite3.connect(self.db)
        stale_search = con.execute(
            "SELECT rel_path FROM files_fts WHERE files_fts MATCH ?",
            ("token_alpha",),
        ).fetchall()
        added_search = con.execute(
            "SELECT rel_path FROM files_fts WHERE files_fts MATCH ?",
            ("xylophone",),
        ).fetchall()
        con.close()

        self.assertEqual(
            stale_search, [],
            "Deleted file must not remain reachable in FTS index",
        )

        # Added file is indexed and reachable in FTS
        added_rel = os.path.join("src", "extra.py")
        self.assertIn(added_rel, [r[0] for r in snap_after["files"]])
        self.assertEqual(added_search, [(added_rel,)])

        # Modified file has updated symbols (old retained + new added)
        app_rel = os.path.join("src", "app.py")
        app_symbols = [r[1] for r in snap_after["symbols"] if r[0] == app_rel]
        self.assertIn("multiply", app_symbols)
        self.assertIn("MathEngine", app_symbols)
        self.assertIn("calculate", app_symbols)

    def test_binary_flip_drops_row_and_fts_cleanly(self):
        flip_file = self.proj / "src" / "flip_target.py"
        flip_file.write_text(
            "def unique_flip_symbol():\n    return 42\n",
            encoding="utf-8",
        )
        self._run_build()

        flip_rel = os.path.join("src", "flip_target.py")
        snap = _snapshot_db(self.db)
        self.assertIn(flip_rel, [r[0] for r in snap["files"]])

        con = sqlite3.connect(self.db)
        hits = con.execute(
            "SELECT rel_path FROM files_fts WHERE files_fts MATCH ?",
            ("unique_flip_symbol",),
        ).fetchall()
        con.close()
        self.assertEqual(hits, [(flip_rel,)])

        # Flip the file to binary (NUL bytes) — must drop the row and FTS entry
        flip_file.write_bytes(b"\x00\xff\x84" * 5000)
        self._run_build()

        snap_flipped = _snapshot_db(self.db)
        self.assertNotIn(
            flip_rel,
            [r[0] for r in snap_flipped["files"]],
            "Binary-flipped file must be dropped from files table",
        )

        con = sqlite3.connect(self.db)
        hits_after = con.execute(
            "SELECT rel_path FROM files_fts WHERE files_fts MATCH ?",
            ("unique_flip_symbol",),
        ).fetchall()
        con.close()
        self.assertEqual(
            hits_after, [],
            "Binary-flipped file must be purged from FTS (no stale FTS rows)",
        )

    def test_touch_update_keeps_content_and_fts_identical(self):
        self._run_build("--full")
        snap_before = _snapshot_db(self.db)

        # Bump mtime only (content unchanged) -> touch path, not content rewrite
        target = self.proj / "src" / "app.py"
        mtime = os.path.getmtime(target)
        os.utime(target, (mtime + 60, mtime + 60))

        self._run_build()
        snap_after = _snapshot_db(self.db)

        # mtime is normalized out of every snapshot -> rows must be identical,
        # proving a touch did not rewrite content or FTS.
        for key in ("files", "symbols", "fts", "fts_trigram"):
            self.assertEqual(
                snap_before[key],
                snap_after[key],
                f"{key} must be unchanged by a touch-only mtime bump",
            )


if __name__ == "__main__":
    unittest.main()