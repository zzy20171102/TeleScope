import unittest

from telescope.agents.llm import extract_json


class TestExtractJson(unittest.TestCase):
    def test_think_block(self):
        raw = "<think>reasoning</think>\n```json\n{\"a\": 1}\n```"
        self.assertEqual(extract_json(raw), {"a": 1})

    def test_strict_parse(self):
        self.assertEqual(extract_json('{"a": "b"}'), {"a": "b"})

    def test_repair_unescaped_quotes(self):
        raw = ('<think>x</think>{"headline": "He said "stop" loudly", '
               '"summary": "ok"}')
        out = extract_json(raw, repair=True)
        self.assertEqual(out["summary"], "ok")
        self.assertIn("stop", out["headline"])

    def test_repair_quotes_before_delimiters(self):
        raw = '{"a": "quote, then end", "b": 1}'
        out = extract_json(raw, repair=True)
        self.assertEqual(out["b"], 1)


if __name__ == "__main__":
    unittest.main()
