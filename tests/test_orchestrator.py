import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path

from telescope.models import Article
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


if __name__ == "__main__":
    unittest.main()
