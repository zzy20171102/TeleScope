import unittest

from telescope.models import Article
from telescope.pipeline.dedup import InBatchDeduper, titles_similar


def mk(url, title, lang="en"):
    return Article(source_id="s", url=url, url_hash="h" + url, title=title, lang=lang)


class TestDedup(unittest.TestCase):
    def test_exact_url(self):
        d = InBatchDeduper()
        self.assertFalse(d.is_duplicate(mk("https://a.com/1", "T1")))
        self.assertTrue(d.is_duplicate(mk("https://a.com/1", "T1 again")))

    def test_fuzzy_title_same_lang(self):
        d = InBatchDeduper()
        self.assertFalse(d.is_duplicate(mk("https://a.com/1", "US imposes new sanctions on Russia")))
        self.assertTrue(d.is_duplicate(mk("https://b.com/2", "US imposes new sanctions on Russia over")))

    def test_titles_similar(self):
        self.assertTrue(titles_similar("Japan chip export curbs", "Japan chip export controls"))
        self.assertFalse(titles_similar("Japan chip export curbs", "Brazil election results"))


if __name__ == "__main__":
    unittest.main()
