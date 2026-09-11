import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from telescope import cli, config, storage
from telescope.models import Citation, EventRelation

RSS_OK = (b"<rss version=\"2.0\"><channel><title>t</title>"
          b"<item><title>a</title><link>https://x/1</link></item>"
          b"</channel></rss>")


class TestSourcesCli(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        self.yaml = self.tmp / "sources.yaml"
        shutil.copy(config.SOURCES_PATH, self.yaml)
        self._patch_src = mock.patch.object(config, "SOURCES_PATH", self.yaml)
        self._patch_src.start()
        self.addCleanup(self._patch_src.stop)

    def test_add_enable_disable_roundtrip(self):
        rc = cli.main(["sources", "add", "--id", "test-src",
                       "--name", "Test Source", "--url", "https://x.example/rss",
                       "--language", "zh", "--region", "asia",
                       "--perspective", "test", "--weight", "0.5"])
        self.assertEqual(rc, 0)
        srcs = config.load_sources()
        self.assertIn("test-src", [s.id for s in srcs])
        added = next(s for s in srcs if s.id == "test-src")
        self.assertEqual(added.name, "Test Source")
        self.assertEqual(added.weight, 0.5)
        self.assertTrue(added.enabled)
        # yaml roundtrip preserves the other sources
        self.assertIn("bbc-world", [s.id for s in srcs])
        # duplicate id rejected
        self.assertEqual(cli.main(["sources", "add", "--id", "test-src",
                                   "--name", "X", "--url", "https://x/2"]), 2)
        # disable / enable
        self.assertEqual(cli.main(["sources", "disable", "test-src"]), 0)
        self.assertFalse(next(s for s in config.load_sources()
                              if s.id == "test-src").enabled)
        self.assertEqual(cli.main(["sources", "enable", "test-src"]), 0)
        self.assertTrue(next(s for s in config.load_sources()
                             if s.id == "test-src").enabled)
        self.assertEqual(cli.main(["sources", "disable", "no-such-id"]), 2)
        self.assertEqual(cli.main(["sources"]), 0)

    def _minimal_yaml(self) -> None:
        self.yaml.write_text(
            "sources:\n"
            "  - id: mini\n"
            "    name: Mini\n"
            "    url: https://m.example/rss\n"
            "    type: rss\n"
            "    language: en\n"
            "    region: global\n"
            "    perspective: test\n"
            "    weight: 1.0\n"
            "    fetch_interval_minutes: 60\n"
            "    enabled: true\n",
            encoding="utf-8")

    def test_check_records_health(self):
        self._minimal_yaml()
        db = self.tmp / "t.db"
        with mock.patch.object(config, "DB_PATH", db), \
                mock.patch("telescope.collectors.rss.fetch_url",
                           return_value=RSS_OK):
            rc = cli.main(["sources", "check", "--timeout", "5"])
        self.assertEqual(rc, 0)
        conn = storage.connect(db)
        rows = {r["id"]: json.loads(r["health_json"])
                for r in conn.execute("SELECT * FROM sources")}
        self.assertTrue(rows)
        self.assertTrue(all(v.get("ok") for v in rows.values()))
        conn.close()

    def test_check_failure_exit_code(self):
        self._minimal_yaml()
        db = self.tmp / "t.db"
        with mock.patch.object(config, "DB_PATH", db), \
                mock.patch("telescope.collectors.rss.fetch_url",
                           side_effect=RuntimeError("boom")):
            rc = cli.main(["sources", "check"])
        self.assertEqual(rc, 1)


class TestFeedbackCli(unittest.TestCase):
    def test_add_and_list_with_relation_status(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "t.db"
            conn = storage.connect(db)
            storage.save_event_relations(conn, [EventRelation(
                prior_event_id=1, target_event_id=2, type="background",
                narrative="n", confidence=0.5,
                evidence=[Citation(article_id=1, span="some span text here")])])
            conn.close()
            with mock.patch.object(config, "DB_PATH", db):
                rc = cli.main(["feedback", "add", "--kind", "event_relation",
                               "--target", "1", "--rating", "reject",
                               "--note", "wrong link"])
                self.assertEqual(rc, 0)
                self.assertEqual(cli.main(["feedback", "list"]), 0)
                self.assertEqual(
                    cli.main(["feedback", "list", "--kind", "event_relation"]), 0)
            conn = storage.connect(db)
            rel = conn.execute("SELECT status FROM event_relations").fetchone()
            self.assertEqual(rel["status"], "rejected")
            fb = storage.list_feedback(conn, kind="event_relation")[0]
            self.assertEqual(fb["rating"], "reject")
            self.assertEqual(fb["note"], "wrong link")
            conn.close()

    def test_add_unknown_relation_target(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "t.db"
            with mock.patch.object(config, "DB_PATH", db):
                rc = cli.main(["feedback", "add", "--kind", "event_relation",
                               "--target", "99", "--rating", "confirm"])
            self.assertEqual(rc, 1)  # saved but not applied


if __name__ == "__main__":
    unittest.main()
