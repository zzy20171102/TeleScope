import datetime as dt
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from telescope import storage
from telescope.models import Article, Event
from telescope.orchestrator import run_daily
from telescope.pipeline.normalize import extract_entities, url_hash

NOW = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def mk(source_id, url, title, text):
    return Article(source_id=source_id, url=url, url_hash=url_hash(url),
                   title=title, content_text=text,
                   published_at=NOW, entities=extract_entities(title + " " + text))


INJECT = [
    mk("bbc-world", "https://a.com/1", "US imposes new sanctions on Russia",
       "The US announced sanctions on Russia over the war. Markets reacted."),
    mk("guardian-world", "https://b.com/2", "Russia responds to US sanctions",
       "Russia vowed retaliation against US sanctions on Friday."),
    mk("nikkei-asia", "https://c.com/3", "Japan expands chip export controls",
       "Japan announced tighter semiconductor export rules affecting China."),
    mk("bbc-world", "https://d.com/4", "Local cake festival draws crowds",
       "A baking contest was held downtown."),
]


def seed_prior_event(db_path: Path) -> int:
    """Seed one historical event (5 days ago) sharing an entity with the
    sanctions story, so the F2 lineage engine has something to recall."""
    conn = storage.connect(db_path)
    title = "Congress debates new Russia sanctions bill"
    text = "Congress debated a new bill targeting Russia. Analysts expect a vote."
    ago = (dt.datetime.now(dt.timezone.utc)
           - dt.timedelta(days=5)).isoformat(timespec="seconds")
    a = Article(source_id="reuters-world",
                url="https://h.com/prior/1", url_hash=url_hash("https://h.com/prior/1"),
                title=title, content_text=text,
                entities=extract_entities(title + " " + text), published_at=ago)
    aid = storage.upsert_article(conn, a)
    ev = Event(title=title, category="diplomacy", severity=1.2,
               article_ids=[aid], source_ids=["reuters-world"],
               first_seen=ago, last_seen=ago)
    eid = storage.save_event(conn, ev)
    conn.close()
    return eid


class TestOrchestrator(unittest.TestCase):
    def _force_rule_backend(self):
        """Hermetic offline test: env vars take precedence over .env,
        and an empty key selects the deterministic RuleBackend."""
        old = os.environ.get("TELESCOPE_LLM_API_KEY")
        os.environ["TELESCOPE_LLM_API_KEY"] = ""
        self.addCleanup(self._restore_key, old)

    def _restore_key(self, old):
        if old is None:
            os.environ.pop("TELESCOPE_LLM_API_KEY", None)
        else:
            os.environ["TELESCOPE_LLM_API_KEY"] = old

    def test_end_to_end_injected(self):
        self._force_rule_backend()
        with tempfile.TemporaryDirectory() as td:
            out = run_daily(inject_articles=INJECT, db_path=Path(td) / "t.db",
                            brief_dir=Path(td) / "briefs", top_n=6, trigger="test")
            self.assertTrue(out.exists())
            body = out.read_text(encoding="utf-8")
            self.assertIn("模式：rule", body)
            self.assertIn("[1]", body)
            self.assertIn("引用来源", body)
            # irrelevant cake item should not appear as headline
            self.assertNotIn("cake festival", body)
            db = Path(td) / "t.db"
            self.assertTrue(db.exists())
            # M1.1: reviewer gate ran, citation validation stats rendered
            self.assertIn("引用校验", body)
            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            self.assertTrue(conn.execute(
                "SELECT COUNT(*) c FROM citations").fetchone()["c"] > 0)
            reviewer = conn.execute(
                "SELECT COUNT(*) c FROM steps WHERE agent=?", ("reviewer",)
            ).fetchone()["c"]
            self.assertEqual(reviewer, 1)
            run_row = conn.execute(
                "SELECT checkpoint FROM runs ORDER BY id DESC").fetchone()
            self.assertIn("quotes_kept", run_row["checkpoint"])
            conn.close()

    def test_end_to_end_lineage(self):
        self._force_rule_backend()
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "t.db"
            prior_id = seed_prior_event(db)
            out = run_daily(inject_articles=INJECT, db_path=db,
                            brief_dir=Path(td) / "briefs", top_n=6,
                            trace_n=3, trigger="test-lineage")
            body = out.read_text(encoding="utf-8")
            self.assertIn("事件溯源", body)
            self.assertIn("Congress debates", body)  # prior event recalled
            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            rels = conn.execute(
                "SELECT * FROM event_relations WHERE prior_event_id=?",
                (prior_id,)).fetchall()
            self.assertTrue(rels)
            self.assertEqual(rels[0]["target_event_id"] > 0, True)
            self.assertIn("article_id", rels[0]["evidence"])
            traced = conn.execute(
                "SELECT COUNT(*) c FROM steps WHERE agent=?", ("tracer",)
            ).fetchone()["c"]
            self.assertGreaterEqual(traced, 1)
            ck = json.loads(conn.execute(
                "SELECT checkpoint FROM runs ORDER BY id DESC").fetchone()["checkpoint"])
            self.assertGreaterEqual(ck["traced_items"], 1)
            self.assertGreaterEqual(ck["lineage_relations"], 1)
            conn.close()


if __name__ == "__main__":
    unittest.main()
