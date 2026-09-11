import datetime as dt
import tempfile
import unittest
from pathlib import Path

from telescope import storage
from telescope.models import Article, Event
from telescope.pipeline.normalize import url_hash
from telescope.pipeline.recall import recall

NOW = dt.datetime.now(dt.timezone.utc)


def days_ago(n: int) -> str:
    return (NOW - dt.timedelta(days=n)).isoformat(timespec="seconds")


def ev(eid, title, first_seen, entities, category="diplomacy", severity=1.4):
    return {"id": eid, "title": title, "category": category, "severity": severity,
            "first_seen": first_seen, "last_seen": first_seen,
            "entities": entities, "articles": []}


class TestRecall(unittest.TestCase):
    def setUp(self):
        self.target = {"id": 99, "title": "Russia announces counter-sanctions package",
                       "category": "diplomacy", "severity": 1.4,
                       "first_seen": NOW.isoformat(timespec="seconds"),
                       "entities": ["俄罗斯", "美国"]}
        self.history = [
            ev(1, "US imposes new sanctions on Russia", days_ago(5),
               ["美国", "俄罗斯"]),
            ev(2, "Russia announces counter-sanctions package", days_ago(4),
               ["俄罗斯"]),  # near-duplicate of target -> must be skipped
            ev(3, "Local sports final decides city cup", days_ago(2), [],
               category="society"),
            ev(4, "Future unrelated summit held", days_ago(-3), ["俄罗斯"]),
        ]

    def test_entity_recall_and_ranking(self):
        cands = recall(self.target, self.history, top_k=6)
        self.assertEqual([c["id"] for c in cands], [1])
        self.assertIn("俄罗斯", cands[0]["shared_entities"])
        self.assertGreater(cands[0]["score"], 0.15)

    def test_topic_channel_recalls_without_entities(self):
        hist = [ev(5, "Europe discusses diplomatic sanctions framework",
                   days_ago(3), [])]
        cands = recall(self.target, hist)
        self.assertEqual([c["id"] for c in cands], [5])

    def test_window_filters_old_events(self):
        hist = [ev(6, "Old Russia sanctions story", days_ago(400),
                   ["俄罗斯"])]
        self.assertEqual(recall(self.target, hist, window_days=180), [])


class TestHistoryLoader(unittest.TestCase):
    def test_history_events_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            conn = storage.connect(Path(td) / "t.db")
            a = Article(source_id="s1", url="https://h.com/1",
                        url_hash=url_hash("https://h.com/1"),
                        title="Congress debates new Russia sanctions bill",
                        content_text="Congress debated a new bill targeting Russia.",
                        entities=["俄罗斯"], published_at=days_ago(5))
            aid = storage.upsert_article(conn, a)
            e = Event(title="Congress debates new Russia sanctions bill",
                      category="diplomacy", severity=1.2,
                      article_ids=[aid], source_ids=["s1"],
                      first_seen=days_ago(5), last_seen=days_ago(5))
            eid = storage.save_event(conn, e)
            hist = storage.history_events(conn, days=180, exclude_ids=(999,))
            self.assertEqual(len(hist), 1)
            self.assertEqual(hist[0]["id"], eid)
            self.assertIn("俄罗斯", hist[0]["entities"])
            self.assertEqual(hist[0]["articles"][0]["id"], aid)
            self.assertEqual(
                storage.history_events(conn, days=180, exclude_ids=(eid,)), [])
            conn.close()


if __name__ == "__main__":
    unittest.main()
