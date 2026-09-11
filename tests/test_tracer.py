import datetime as dt
import tempfile
import unittest
from pathlib import Path

from telescope import storage
from telescope.agents.llm import RuleBackend
from telescope.agents.tracer import EventTracer
from telescope.models import Citation, EventRelation

NOW = dt.datetime.now(dt.timezone.utc)
AGO = (NOW - dt.timedelta(days=5)).isoformat(timespec="seconds")
FUTURE = (NOW + dt.timedelta(days=2)).isoformat(timespec="seconds")
SPAN = "The US announced sanctions on Russia over the war."

ARTICLES = {
    11: {"id": 11, "title": "US imposes new sanctions on Russia",
         "url": "https://a.com/1", "source_id": "s1",
         "text": SPAN + " Markets reacted on Friday."},
    22: {"id": 22, "title": "Russia announces counter-measures",
         "url": "https://b.com/2", "source_id": "s2",
         "text": "Russia vowed retaliation against US sanctions on Friday."},
    33: {"id": 33, "title": "EU discusses energy security",
         "url": "https://c.com/3", "source_id": "s3",
         "text": "European officials met to discuss energy supplies."},
}

CANDS = [
    {"id": 1, "title": "US imposes new sanctions on Russia",
     "category": "diplomacy", "severity": 1.4, "first_seen": AGO,
     "entities": ["美国", "俄罗斯"], "articles": [ARTICLES[11]]},
    {"id": 2, "title": "EU discusses energy security", "category": "economy",
     "severity": 1.0, "first_seen": AGO, "entities": ["俄罗斯"],
     "articles": [ARTICLES[33]]},
    {"id": 3, "title": "White House news conference", "category": "politics",
     "severity": 1.0, "first_seen": FUTURE, "entities": ["美国"],
     "articles": [ARTICLES[11]]},
]

TARGET = {"id": 9, "title": "Russia announces counter-measures",
          "category": "diplomacy", "severity": 1.4,
          "first_seen": NOW.isoformat(timespec="seconds"),
          "entities": ["俄罗斯", "美国"], "articles": [ARTICLES[22]]}


class FakeBackend:
    name = "fake"

    def __init__(self, data):
        self.data = data

    def complete_json(self, prompt_name, context):
        return self.data


class TestEventTracerRule(unittest.TestCase):
    def test_rule_backend_relations(self):
        relations, meta = EventTracer(RuleBackend()).trace(TARGET, CANDS, ARTICLES)
        self.assertEqual(meta["mode"], "rule")
        self.assertFalse(meta["isolated"])
        by_id = {r.prior_event_id: r for r in relations}
        self.assertIn(1, by_id)
        rel = by_id[1]
        self.assertEqual(rel.type, "background")
        self.assertEqual(rel.confidence, 0.5)  # 2 shared entities
        self.assertEqual(rel.status, "review")
        self.assertEqual({c.article_id for c in rel.evidence}, {11, 22})
        self.assertIn("共享实体", rel.narrative)

    def test_rule_backend_isolated_when_no_candidates(self):
        relations, meta = EventTracer(RuleBackend()).trace(TARGET, [], ARTICLES)
        self.assertEqual(relations, [])
        self.assertTrue(meta["isolated"])


class TestEventTracerValidation(unittest.TestCase):
    def test_llm_output_validated(self):
        data = {"relations": [
            {"prior_event": 1, "type": "causal", "narrative": "制裁引发反制",
             "confidence": 0.85,
             "evidence": [{"article_id": 11, "quote_span": SPAN}]},
            {"prior_event": 2, "type": "background", "narrative": "坏证据",
             "confidence": 0.6,
             "evidence": [{"article_id": 33,
                           "quote_span": "THIS SPAN EXISTS NOWHERE AT ALL"}]},
            {"prior_event": 77, "type": "background", "narrative": "未知候选",
             "confidence": 0.6,
             "evidence": [{"article_id": 11, "quote_span": SPAN}]},
            {"prior_event": 3, "type": "causal", "narrative": "未来事件强加因果",
             "confidence": 0.7,
             "evidence": [{"article_id": 11, "quote_span": SPAN}]},
        ], "isolated": False}
        relations, meta = EventTracer(FakeBackend(data)).trace(TARGET, CANDS, ARTICLES)
        self.assertEqual(meta["mode"], "fake")
        ids = {r.prior_event_id for r in relations}
        self.assertEqual(ids, {1, 3})
        rel1 = next(r for r in relations if r.prior_event_id == 1)
        self.assertEqual(rel1.type, "causal")
        self.assertEqual(rel1.status, "auto")
        self.assertEqual(rel1.evidence[0].article_id, 11)
        rel3 = next(r for r in relations if r.prior_event_id == 3)
        self.assertEqual(rel3.type, "thematic_parallel")  # direction violated

    def test_relation_without_evidence_dropped(self):
        data = {"relations": [
            {"prior_event": 1, "type": "causal", "narrative": "无证据",
             "confidence": 0.9, "evidence": []},
        ], "isolated": False}
        relations, meta = EventTracer(FakeBackend(data)).trace(TARGET, CANDS, ARTICLES)
        self.assertEqual(relations, [])
        self.assertTrue(meta["isolated"])


class TestEventRelationsStorage(unittest.TestCase):
    def test_save_event_relations_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            conn = storage.connect(Path(td) / "t.db")
            rel = EventRelation(
                prior_event_id=1, target_event_id=9, type="causal",
                narrative="n", confidence=0.8,
                prior_title="t", prior_date="2026-09-01",
                evidence=[Citation(article_id=11, span=SPAN, url="u")])
            self.assertEqual(storage.save_event_relations(conn, [rel]), 1)
            row = conn.execute("SELECT * FROM event_relations").fetchone()
            self.assertEqual(row["prior_event_id"], 1)
            self.assertEqual(row["target_event_id"], 9)
            self.assertEqual(row["type"], "causal")
            self.assertEqual(row["status"], "auto")
            self.assertIn("article_id", row["evidence"])
            self.assertEqual(storage.stats(conn)["event_relations"], 1)
            conn.close()


if __name__ == "__main__":
    unittest.main()
