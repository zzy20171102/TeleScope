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

    def test_word_boundary_blocks_substring(self):
        # "war" inside "ward/warning/toward" must NOT match
        r = rules.screen_rule([{"title": "Ward wins warning award",
                                "text": "forward toward hardware reward"}])
        self.assertEqual(r["topic"], "other")

    def test_plural_and_suffix_matching(self):
        r = rules.screen_rule([{"title": "Forces attack border outpost",
                                "text": ""}])
        self.assertEqual(r["topic"], "military")
        r2 = rules.screen_rule([{"title": "Town fair",
                                 "text": "missiles discussed; air strikes reported"}])
        self.assertEqual(r2["topic"], "military")  # 2 distinct body hits

    def test_single_weak_body_hit_insufficient(self):
        # only one keyword in a long body -> not enough (co-occurrence rule)
        r = rules.screen_rule([{"title": "Town fair opens",
                                "text": "the mayor attacked the budget proposal "
                                        "during a long speech about parks"}])
        self.assertEqual(r["topic"], "other")

    def test_severity_requires_strong_signal(self):
        r = rules.screen_rule([{"title": "Poultry slaughterhouses planned",
                                "text": "communities take on planned poultry "
                                        "slaughterhouses amid local debate"}])
        self.assertEqual(r["severity"], 1.0)
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

    def test_summarizer_rule_backend_mode(self):
        arts = [{"id": 7, "title": "Head", "text": "Something happened. More detail.",
                 "source_id": "s1", "weight": 1.0}]
        item = Summarizer(RuleBackend()).summarize(
            {"title": "Head", "category": "diplomacy", "severity": 1.5}, arts)
        self.assertTrue(item.headline)
        self.assertIn(7, item.citation_ids)
        self.assertEqual(item.mode, "rule")


if __name__ == "__main__":
    unittest.main()
