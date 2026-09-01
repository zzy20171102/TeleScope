import datetime as dt
import unittest

from telescope.models import Article, Event
from telescope.pipeline.cluster import OnlineClusterer, jaccard
from telescope.pipeline.scoring import hot_score


NOW = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def mk(aid, title, ents, url, text=""):
    return Article(id=aid, source_id="s" + str(aid), url=url, url_hash="h" + url,
                   title=title, content_text=text, entities=ents, published_at=NOW)


class TestCluster(unittest.TestCase):
    def test_same_event_merges(self):
        c = OnlineClusterer()
        c.add(mk(1, "US imposes sanctions on Russia", ["美国", "俄罗斯"], "https://a.com/1"))
        c.add(mk(2, "Russia responds to US sanctions", ["俄罗斯", "美国"], "https://b.com/2"))
        c.add(mk(3, "Brazil election result announced", ["巴西"], "https://c.com/3"))
        events = c.to_events()
        self.assertEqual(len(events), 2)
        merged = [e for e in events if len(e.article_ids) == 2]
        self.assertEqual(len(merged), 1)

    def test_no_entity_chain_drift(self):
        """P0/T1.2: single-entity chaining must not pull unrelated stories in."""
        c = OnlineClusterer()
        c.add(mk(1, "Messi retires from international football",
                 ["阿根廷"], "https://a.com/1"))
        # disjoint entities + disjoint title tokens -> separate events
        c.add(mk(2, "Supreme Court lets construction continue",
                 ["美国"], "https://b.com/2"))
        c.add(mk(3, "Oil output deal structured",
                 ["美国"], "https://c.com/3"))
        self.assertEqual(len(c.to_events()), 3)

    def test_crosslingual_entity_merge(self):
        c = OnlineClusterer()
        c.add(mk(1, "US imposes sanctions on Russia",
                 ["美国", "俄罗斯"], "https://a.com/1"))
        c.add(mk(2, "美国对俄罗斯实施新制裁",
                 ["美国", "俄罗斯"], "https://b.com/2"))
        self.assertEqual(len(c.to_events()), 1)

    def test_jaccard(self):
        self.assertEqual(jaccard({"a", "b"}, {"a", "b"}), 1.0)
        self.assertEqual(jaccard(set(), {"a"}), 0.0)


class TestScoring(unittest.TestCase):
    def test_more_sources_higher_score(self):
        now = dt.datetime.now(dt.timezone.utc)
        e1 = Event(title="t", article_ids=[1], source_ids=["a"], last_seen=NOW)
        e2 = Event(title="t", article_ids=[1, 2], source_ids=["a", "b"], last_seen=NOW)
        w = {"a": 1.0, "b": 1.0}
        self.assertGreater(hot_score(e2, w, now=now), hot_score(e1, w, now=now))

    def test_recency_decay(self):
        now = dt.datetime.now(dt.timezone.utc)
        old = (now - dt.timedelta(hours=48)).isoformat(timespec="seconds")
        e_old = Event(title="t", article_ids=[1], source_ids=["a"], last_seen=old)
        e_new = Event(title="t", article_ids=[1], source_ids=["a"], last_seen=NOW)
        w = {"a": 1.0}
        self.assertGreater(hot_score(e_new, w, now=now), hot_score(e_old, w, now=now))


if __name__ == "__main__":
    unittest.main()
