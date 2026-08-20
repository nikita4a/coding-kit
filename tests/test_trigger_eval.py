"""Contract tests for eval/trigger_eval.py — query validation, signal
detection, and threshold summary. No model calls."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
from trigger_eval import detect, summarize, validate


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


if __name__ == "__main__":
    unittest.main()