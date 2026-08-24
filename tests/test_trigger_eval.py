"""Contract tests for eval/trigger_eval.py — query validation, signal
detection, and threshold summary. No model calls."""
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
from trigger_eval import detect, summarize, validate
import trigger_eval


class ValidateTest(unittest.TestCase):
    def test_ok_queries_pass(self):
        qs = [{"skill": "yagni", "should": True, "query": "add a cache?"},
              {"skill": "yagni", "should": False, "query": "two plus two"}]
        self.assertEqual(validate(qs), [])

    def test_missing_should_not_queries(self):
        qs = [{"skill": "yagni", "should": True, "query": "add a cache?"}]
        problems = validate(qs)
        self.assertTrue(any("no should-not" in p for p in problems))

    def test_should_not_must_not_name_its_skill(self):
        qs = [{"skill": "yagni", "should": True, "query": "add a cache?"},
              {"skill": "yagni", "should": False,
               "query": "should I use yagni here?"}]
        problems = validate(qs)
        self.assertTrue(any("near-miss must not" in p for p in problems))

    def test_duplicate_pairs_flagged(self):
        qs = [{"skill": "yagni", "should": True, "query": "add a cache?"},
              {"skill": "yagni", "should": False, "query": "two plus two"},
              {"skill": "yagni", "should": True, "query": "add a cache?"}]
        problems = validate(qs)
        self.assertTrue(any("duplicate" in p for p in problems))

    def test_empty_file_flag(self):
        self.assertTrue(validate([]))


class DetectTest(unittest.TestCase):
    def test_standalone_token(self):
        self.assertTrue(detect("yagni", "I loaded the yagni skill"))
        self.assertTrue(detect("yagni", "SKILLS LOADED: yagni"))
        self.assertTrue(detect("yagni", "YAGNI says cut it"))

    def test_word_boundaries(self):
        self.assertFalse(detect("yagni", "yagni2 is a fork"))
        self.assertFalse(detect("yagni", "ayagni appeared"))
        self.assertFalse(detect("yagni", "no skill was loaded"))

    def test_hyphenated_slug(self):
        self.assertTrue(detect("dev-wiki", "loaded dev-wiki"))
        self.assertFalse(detect("dev-wiki", "dev wiki is my friend"))


class SummarizeTest(unittest.TestCase):
    def test_below_threshold_flags_failed_queries(self):
        rows = {"yagni": [("q1", True, True), ("q2", True, False),
                          ("q3", True, False), ("q4", True, False),
                          ("n1", False, False), ("n2", False, False)]}
        problems, stats = summarize(rows)
        self.assertTrue(any("trigger rate" in p for p in problems))
        self.assertAlmostEqual(stats["yagni"]["trigger"], 0.25)
        self.assertEqual(stats["yagni"]["false"], 0.0)

    def test_false_rate_above_threshold(self):
        rows = {"yagni": [("q1", True, True), ("n1", False, True),
                          ("n2", False, True), ("n3", False, True)]}
        problems, _ = summarize(rows)
        self.assertTrue(any("false rate" in p for p in problems))


class TimeoutPassthroughTest(unittest.TestCase):
    """--timeout must reach run_prompt (audit 2026-08-22, M4: the flag was
    parsed and documented but never used — run_prompt hardcoded 600s)."""

    def test_run_query_passes_timeout(self):
        seen = {}

        def fake_run_prompt(cmd, prompt, timeout=None):
            seen["timeout"] = timeout
            return "SKILLS LOADED: yagni"

        orig = trigger_eval.run_prompt
        trigger_eval.run_prompt = fake_run_prompt
        try:
            _, passed = trigger_eval.run_query(
                ["x"], {"skill": "yagni", "query": "q"}, 1, timeout=42)
        finally:
            trigger_eval.run_prompt = orig
        self.assertTrue(passed)
        self.assertEqual(seen["timeout"], 42)


class LiveNoJsonCompletionTest(unittest.TestCase):
    def test_live_no_json_completes_without_saving(self):
        saved = []

        def fake_save(*args, **kwargs):
            saved.append((args, kwargs))

        def fake_run_prompt(cmd, prompt, timeout=None):
            if "USE THIS ONE" in prompt:
                return "SKILLS LOADED: yagni"
            return "SKILLS LOADED: none"

        with tempfile.TemporaryDirectory() as tmp:
            queries_file = Path(tmp) / "q.json"
            queries_file.write_text(json.dumps([
                {"skill": "yagni", "should": True, "query": "USE THIS ONE"},
                {"skill": "yagni", "should": False, "query": "OTHER TASK"},
            ]), encoding="utf-8")
            test_argv = [
                "trigger_eval.py",
                "--queries", str(queries_file),
                "--executor", "mock_cli",
            ]
            orig_argv = sys.argv
            orig_run = trigger_eval.run_prompt
            trigger_eval.run_prompt = fake_run_prompt
            try:
                sys.argv = test_argv
                with unittest.mock.patch("results_io.save_result", fake_save):
                    rc = trigger_eval.main()
            finally:
                sys.argv = orig_argv
                trigger_eval.run_prompt = orig_run
        self.assertEqual(rc, 0)
        self.assertEqual(len(saved), 0)


class ModelExecutorSeparationTest(unittest.TestCase):
    def test_explicit_model_and_executor_passed_to_save_result(self):
        calls = []
        def fake_save_result(kind, model, payload, path=None, *, executor_spec=None, results_dir=None):
            calls.append({"kind": kind, "model": model, "payload": payload, "path": path, "executor_spec": executor_spec})
            return Path("mock_path.json")

        class Args:
            json = "auto"
            executor = "my-custom-cli --token secret"
            model = "gemini-2.5-pro"

        with unittest.mock.patch("results_io.save_result", fake_save_result):
            trigger_eval._emit_json(Args(), mode="live", total=10, passed=10, fired=10, misses=[], rows=[])

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["kind"], "trigger")
        self.assertEqual(calls[0]["model"], "gemini-2.5-pro")
        self.assertEqual(calls[0]["executor_spec"], "my-custom-cli --token secret")
        self.assertEqual(calls[0]["payload"]["passed"], 10)
        self.assertEqual(calls[0]["payload"]["fired"], 10)

    def test_missing_model_defaults_to_unspecified(self):
        calls = []
        def fake_save_result(kind, model, payload, path=None, *, executor_spec=None, results_dir=None):
            calls.append({"kind": kind, "model": model, "payload": payload, "path": path, "executor_spec": executor_spec})
            return Path("mock_path.json")

        class Args:
            json = "auto"
            executor = "my-cli"
            model = None

        with unittest.mock.patch("results_io.save_result", fake_save_result):
            trigger_eval._emit_json(Args(), mode="live", total=10, passed=10, fired=10, misses=[], rows=[])

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["model"], "unspecified")
        self.assertEqual(calls[0]["executor_spec"], "my-cli")
        self.assertEqual(calls[0]["payload"]["passed"], 10)
        self.assertEqual(calls[0]["payload"]["fired"], 10)


class RowAttemptEvidenceTest(unittest.TestCase):
    def test_run_query_detailed_records_attempts_and_verdict(self):
        def fake_run_prompt(cmd, prompt, timeout=None):
            return "SKILLS LOADED: yagni"

        orig = trigger_eval.run_prompt
        trigger_eval.run_prompt = fake_run_prompt
        try:
            row = trigger_eval.run_query_detailed(
                ["mock"], {"skill": "yagni", "should": True, "query": "write simple code"}, runs=3, timeout=50
            )
        finally:
            trigger_eval.run_prompt = orig

        self.assertEqual(row["query"], "write simple code")
        self.assertEqual(row["skill"], "yagni")
        self.assertTrue(row["expected"])
        self.assertTrue(row["fired"])
        self.assertEqual(row["verdict"], "PASS")
        self.assertIsInstance(row["duration_s"], float)
        self.assertEqual(len(row["attempts"]), 3)
        for att in row["attempts"]:
            self.assertTrue(att["fired"])
            self.assertIsInstance(att["duration_s"], float)
            self.assertNotIn("error", att)

    def test_majority_vote_detection(self):
        call_count = 0
        def alternating_prompt(cmd, prompt, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "no skill loaded"
            return "SKILLS LOADED: yagni"

        orig = trigger_eval.run_prompt
        trigger_eval.run_prompt = alternating_prompt
        try:
            row = trigger_eval.run_query_detailed(
                ["mock"], {"skill": "yagni", "should": True, "query": "yagni query"}, runs=3
            )
        finally:
            trigger_eval.run_prompt = orig

        self.assertTrue(row["fired"])
        self.assertEqual(row["verdict"], "PASS")
        self.assertEqual(len(row["attempts"]), 3)
        self.assertFalse(row["attempts"][0]["fired"])
        self.assertTrue(row["attempts"][1]["fired"])
        self.assertTrue(row["attempts"][2]["fired"])


class ErrorCaptureTest(unittest.TestCase):
    def test_executor_exception_captured_as_attempt_error(self):
        def failing_prompt(cmd, prompt, timeout=None):
            raise RuntimeError("network down or model crashed")

        orig = trigger_eval.run_prompt
        trigger_eval.run_prompt = failing_prompt
        try:
            row = trigger_eval.run_query_detailed(
                ["mock"], {"skill": "yagni", "should": True, "query": "query"}, runs=2
            )
        finally:
            trigger_eval.run_prompt = orig

        self.assertFalse(row["fired"])
        self.assertEqual(row["verdict"], "FAIL")
        self.assertEqual(len(row["attempts"]), 2)
        for att in row["attempts"]:
            self.assertFalse(att["fired"])
            self.assertIn("RuntimeError", att.get("error", ""))

    def test_timeout_expired_captured_with_trace_tail(self):
        import subprocess
        def timeout_prompt(cmd, prompt, timeout=None):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout or 300, stderr="stderr trace from subprocess")

        orig = trigger_eval.run_prompt
        trigger_eval.run_prompt = timeout_prompt
        try:
            row = trigger_eval.run_query_detailed(
                ["mock"], {"skill": "yagni", "should": True, "query": "query"}, runs=1, timeout=25
            )
        finally:
            trigger_eval.run_prompt = orig

        self.assertFalse(row["fired"])
        self.assertEqual(row["verdict"], "FAIL")
        att = row["attempts"][0]
        self.assertIn("TimeoutExpired", att.get("error", ""))
        self.assertEqual(att.get("trace_tail"), "stderr trace from subprocess")



class TopLevelFiredVsPassedSemanticsTest(unittest.TestCase):
    def test_correct_should_not_query_passed_not_fired(self):
        saved = []
        def fake_save_result(kind, model, payload, path=None, *, executor_spec=None, results_dir=None):
            saved.append(payload)
            return Path("mock.json")

        def fake_run_prompt(cmd, prompt, timeout=None):
            return "SKILLS LOADED: none"

        with tempfile.TemporaryDirectory() as tmp:
            queries_file = Path(tmp) / "q.json"
            queries_file.write_text(json.dumps([
                {"skill": "yagni", "should": True, "query": "should I add an unused abstraction?"},
                {"skill": "yagni", "should": False, "query": "calculate fibonacci"},
            ]), encoding="utf-8")
            test_argv = [
                "trigger_eval.py",
                "--queries", str(queries_file),
                "--executor", "mock_cli",
                "--json", "auto",
            ]
            orig_argv = sys.argv
            orig_run = trigger_eval.run_prompt
            trigger_eval.run_prompt = fake_run_prompt
            try:
                sys.argv = test_argv
                with unittest.mock.patch("results_io.save_result", fake_save_result):
                    trigger_eval.main()
            finally:
                sys.argv = orig_argv
                trigger_eval.run_prompt = orig_run

        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["total"], 2)
        self.assertEqual(saved[0]["passed"], 1)
        self.assertEqual(saved[0]["fired"], 0)
        should_not = next(row for row in saved[0]["rows"] if not row["expected"])
        self.assertEqual(should_not["verdict"], "PASS")
        self.assertFalse(should_not["fired"])

    def test_never_fire_model_mixed_corpus(self):
        saved = []
        def fake_save_result(kind, model, payload, path=None, *, executor_spec=None, results_dir=None):
            saved.append(payload)
            return Path("mock.json")

        def fake_run_prompt(cmd, prompt, timeout=None):
            return "SKILLS LOADED: none"

        with tempfile.TemporaryDirectory() as tmp:
            queries_file = Path(tmp) / "q.json"
            queries_file.write_text(json.dumps([
                {"skill": "yagni", "should": True, "query": "should I add an unused abstraction?"},
                {"skill": "yagni", "should": True, "query": "speculative generalization query"},
                {"skill": "yagni", "should": False, "query": "calculate fibonacci"},
                {"skill": "yagni", "should": False, "query": "what is 2 + 2"},
            ]), encoding="utf-8")
            test_argv = [
                "trigger_eval.py",
                "--queries", str(queries_file),
                "--executor", "mock_cli",
                "--json", "auto",
            ]
            orig_argv = sys.argv
            orig_run = trigger_eval.run_prompt
            trigger_eval.run_prompt = fake_run_prompt
            try:
                sys.argv = test_argv
                with unittest.mock.patch("results_io.save_result", fake_save_result):
                    trigger_eval.main()
            finally:
                sys.argv = orig_argv
                trigger_eval.run_prompt = orig_run

        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["total"], 4)
        self.assertEqual(saved[0]["passed"], 2)
        self.assertEqual(saved[0]["fired"], 0)

    def test_perfect_mixed_corpus(self):
        saved = []
        def fake_save_result(kind, model, payload, path=None, *, executor_spec=None, results_dir=None):
            saved.append(payload)
            return Path("mock.json")

        def fake_run_prompt(cmd, prompt, timeout=None):
            if "add an unused abstraction" in prompt or "generalization" in prompt:
                return "SKILLS LOADED: yagni"
            return "SKILLS LOADED: none"

        with tempfile.TemporaryDirectory() as tmp:
            queries_file = Path(tmp) / "q.json"
            queries_file.write_text(json.dumps([
                {"skill": "yagni", "should": True, "query": "add an unused abstraction?"},
                {"skill": "yagni", "should": True, "query": "generalization query"},
                {"skill": "yagni", "should": False, "query": "calculate fibonacci"},
                {"skill": "yagni", "should": False, "query": "what is 2 + 2"},
            ]), encoding="utf-8")
            test_argv = [
                "trigger_eval.py",
                "--queries", str(queries_file),
                "--executor", "mock_cli",
                "--json", "auto",
            ]
            orig_argv = sys.argv
            orig_run = trigger_eval.run_prompt
            trigger_eval.run_prompt = fake_run_prompt
            try:
                sys.argv = test_argv
                with unittest.mock.patch("results_io.save_result", fake_save_result):
                    trigger_eval.main()
            finally:
                sys.argv = orig_argv
                trigger_eval.run_prompt = orig_run

        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["total"], 4)
        self.assertEqual(saved[0]["passed"], 4)
        self.assertEqual(saved[0]["fired"], 2)
if __name__ == "__main__":
    unittest.main()