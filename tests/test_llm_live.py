"""Live LLM test (opt-in, requires network + .env).

Run explicitly with:
    TELESCOPE_LLM_LIVE=1 python -X utf8 -m unittest tests.test_llm_live
"""
import os
import unittest


@unittest.skipUnless(os.environ.get("TELESCOPE_LLM_LIVE") == "1",
                     "live test disabled; set TELESCOPE_LLM_LIVE=1 to enable")
class TestLLMLive(unittest.TestCase):
    def test_screener_roundtrip(self):
        from telescope.agents.llm import OpenAICompatBackend, extract_json, get_backend

        backend = get_backend()
        self.assertIsInstance(backend, OpenAICompatBackend)
        cards = [{"id": 1, "title": "Russia launches missile strike on Kyiv",
                  "text": "Multiple explosions reported."},
                 {"id": 2, "title": "Local cake festival draws crowds",
                  "text": "A baking contest was held."}]
        import json

        out = backend.complete_json(
            "screener", {"items_json": json.dumps(cards, ensure_ascii=False)})
        results = {r["id"]: r for r in out["results"]}
        self.assertTrue(results[1]["relevant"])
        self.assertFalse(results[2]["relevant"])

    def test_extract_json_think_block(self):
        from telescope.agents.llm import extract_json

        raw = "<think>reasoning...</think>\n```json\n{\"a\": 1}\n```"
        self.assertEqual(extract_json(raw), {"a": 1})


if __name__ == "__main__":
    unittest.main()
