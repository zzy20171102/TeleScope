import tempfile
import unittest
from pathlib import Path

from telescope import storage
from telescope.models import Article, Event


class TestStorage(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            conn = storage.connect(Path(td) / "t.db")
            a = Article(source_id="s1", url="https://a.com/1", url_hash="h1",
                        title="T", content_text="body", lang="en",
                        published_at="2026-09-01T00:00:00+00:00", entities=["中国"])
            aid = storage.upsert_article(conn, a)
            self.assertIsNotNone(aid)
            self.assertIsNone(storage.upsert_article(conn, a))  # idempotent
            arts = storage.articles_since(conn, hours=48)
            self.assertEqual(len(arts), 1)
            self.assertEqual(arts[0].entities, ["中国"])
            ev = Event(title="E", category="military", severity=1.5,
                       article_ids=[aid], source_ids=["s1"])
            eid = storage.save_event(conn, ev)
            self.assertGreater(eid, 0)
            rid = storage.start_run(conn, "daily", "test")
            storage.record_step(conn, rid, "collector", "digest", error_card="{}")
            storage.finish_run(conn, rid, "done", {"ok": True})
            s = storage.stats(conn)
            self.assertEqual(s["articles"], 1)
            self.assertEqual(s["runs"], 1)
            conn.close()


if __name__ == "__main__":
    unittest.main()
