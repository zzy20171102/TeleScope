import unittest

from telescope.agents import rules
from telescope.agents.llm import RuleBackend
from telescope.agents.screener import Screener
from telescope.agents.summarizer import Summarizer


class TestRules(unittest.TestCase):
    def test_screen_military(self):
        r = rules.screen_rule([{"title": "Russia missile strike on city",
                                "text": "attack reported"}])
        self.assertTrue(r["relevant"])
        self.assertEqual(r["topic"], "military")
        self.assertGreaterEqual(r["severity"], 1.4)

    def test_screen_irrelevant(self):
        r = rules.screen_rule([{"title": "Local cake festival", "text": "baking"}])
        self.assertFalse(r["relevant"])
        self.assertEqual(r["topic"], "other")

    def test_summarize_rule(self):
        arts = [{"id": 1, "title": "T1", "text": "First sentence. Second one.",
                 "weight": 1.0},
                {"id": 2, "title": "T2", "text": "Another source report.",
                 "weight": 0.9}]
        r = rules.summarize_rule({"title": "T1", "severity": 1.8}, arts)
        self.assertIn("First sentence", r["summary"])
        self.assertIn(1, r["citations"])


class TestAgents(unittest.TestCase):
    def test_screener_rule_backend(self):
        cards = [{"id": 1, "title": "US sanctions on Russia", "text": "new measures"},
                 {"id": 2, "title": "Cake festival", "text": "baking"}]
        results = Screener(RuleBackend()).screen(cards)
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].relevant)
        self.assertFalse(results[1].relevant)

    def test_summarizer_rule_backend(self):
        arts = [{"id": 7, "title": "Head", "text": "Something happened. More detail.",
                 "source_id": "s1", "weight": 1.0}]
        item = Summarizer(RuleBackend()).summarize(
            {"title": "Head", "category": "diplomacy", "severity": 1.5}, arts)
        self.assertTrue(item.headline)
        self.assertIn(7, item.citation_ids)


if __name__ == "__main__":
    unittest.main()
