import unittest

from telescope import yamlmini


class TestYamlMini(unittest.TestCase):
    def test_sources_schema(self):
        text = """# comment
sources:
  - id: bbc-world
    name: BBC World
    url: https://example.com/rss.xml
    weight: 1.0
    enabled: true
  - id: chinanews-scroll
    name: 中新网
    url: https://example.com/cn.xml
    weight: 0.9
    enabled: false
"""
        data = yamlmini.loads(text)
        srcs = data["sources"]
        self.assertEqual(len(srcs), 2)
        self.assertEqual(srcs[0]["id"], "bbc-world")
        self.assertEqual(srcs[0]["weight"], 1.0)
        self.assertTrue(srcs[0]["enabled"])
        self.assertEqual(srcs[1]["name"], "中新网")
        self.assertFalse(srcs[1]["enabled"])


if __name__ == "__main__":
    unittest.main()
