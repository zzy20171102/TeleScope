import unittest

from telescope.pipeline.normalize import (detect_lang, extract_entities,
                                          token_set, url_hash, url_normalize)


class TestNormalize(unittest.TestCase):
    def test_url_normalize_strips_tracking(self):
        a = url_normalize("http://Example.com/a/?utm_source=rss&id=7&fbclid=x#top")
        self.assertEqual(a, "https://example.com/a?id=7")
        self.assertEqual(url_hash("https://x.com/p?utm_campaign=c"),
                         url_hash("https://x.com/p"))

    def test_detect_lang(self):
        self.assertEqual(detect_lang("中国外交部发言人发表谈话"), "zh")
        self.assertEqual(detect_lang("US president holds talks"), "en")
        self.assertEqual(detect_lang("Вопрос к президенту"), "ru")

    def test_extract_entities(self):
        ents = extract_entities("United States and China hold trade talks in Beijing")
        self.assertIn("美国", ents)
        self.assertIn("中国", ents)
        ents_zh = extract_entities("俄罗斯对乌克兰发动导弹袭击")
        self.assertIn("俄罗斯", ents_zh)
        self.assertIn("乌克兰", ents_zh)

    def test_token_set(self):
        self.assertIn("trade", token_set("Trade talks on trade"))
        self.assertNotIn("the", token_set("the the the"))


if __name__ == "__main__":
    unittest.main()
