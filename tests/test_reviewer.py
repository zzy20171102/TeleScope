import tempfile
import unittest
from pathlib import Path

from telescope import storage
from telescope.agents.reviewer import Reviewer
from telescope.models import BriefItem
from telescope.pipeline.verify import citations_for_item, review_item, review_items, span_exists


ARTS = {
    1: {"id": 1, "title": "US imposes new sanctions on Russia",
        "url": "https://a.com/1", "source_id": "s1",
        "text": "The US announced sanctions on Russia over the war."},
    2: {"id": 2, "title": "俄罗斯回应制裁", "url": "https://b.com/2",
        "source_id": "s2", "text": "俄方周五表示将采取报复措施。"},
    3: {"id": 3, "title": "Other story", "url": "https://c.com/3",
        "source_id": "s1", "text": "Something unrelated happened."},
}


class TestSpanVerification(unittest.TestCase):
    def test_exact_span(self):
        self.assertTrue(span_exists("The US announced sanctions", ARTS[1]))

    def test_normalized_span(self):
        # case / extra whitespace / CJK variants still match verbatim spans
        self.assertTrue(span_exists("the  US announced  sanctions", ARTS[1]))
        self.assertTrue(span_exists("俄方周五表示", ARTS[2]))

    def test_missing_and_short_spans(self):
        self.assertFalse(span_exists("this phrase is not in the article", ARTS[1]))
        self.assertFalse(span_exists("sanction", ARTS[1]))  # <12 ascii chars
        self.assertFalse(span_exists("制", ARTS[2]))  # <6 cjk chars
        self.assertFalse(span_exists("anything", None))


class TestReviewItem(unittest.TestCase):
    def test_valid_item_stays_high_confidence(self):
        item = BriefItem(impact="", headline="H", summary="S.", citation_ids=[1, 2],
                         key_quotes=["The US announced sanctions", "俄方周五表示"])
        out, issues = review_item(item, ARTS)
        self.assertEqual(issues, [])
        self.assertEqual(out.confidence, "high")
        self.assertEqual(out.key_quotes, ["The US announced sanctions", "俄方周五表示"])
        self.assertEqual(out.quote_citations, [1, 2])

    def test_unmatched_quote_stripped_and_downgraded(self):
        item = BriefItem(impact="", headline="H", summary="S.", citation_ids=[1],
                         key_quotes=["The US announced sanctions",
                                     "Invented quote that never appeared"])
        out, issues = review_item(item, ARTS)
        self.assertEqual(out.key_quotes, ["The US announced sanctions"])
        self.assertEqual(out.quote_citations, [1])
        self.assertEqual(out.confidence, "low")
        self.assertIn("quote_span_missing", out.issues)

    def test_unknown_citation_stripped(self):
        item = BriefItem(impact="", headline="H", summary="S.", citation_ids=[1, 99],
                         key_quotes=["The US announced sanctions"])
        out, issues = review_item(item, ARTS)
        self.assertEqual(out.citation_ids, [1])
        self.assertIn("citation_unknown", out.issues)
        self.assertEqual(out.confidence, "low")

    def test_no_citations_flags_item(self):
        item = BriefItem(impact="", headline="H", summary="S.", citation_ids=[42],
                         key_quotes=["x"])
        out, issues = review_item(item, ARTS)
        self.assertEqual(out.citation_ids, [])
        self.assertEqual(out.key_quotes, [])
        self.assertIn("citation_missing", out.issues)


class TestReviewerAgent(unittest.TestCase):
    def test_review_report_counts(self):
        items = [
            BriefItem(impact="", headline="A", summary="S.", citation_ids=[1],
                      key_quotes=["The US announced sanctions", "fabricated quote here"]),
            BriefItem(impact="", headline="B", summary="S.", citation_ids=[2],
                      key_quotes=["俄方周五表示"]),
        ]
        out, report = Reviewer().review(items, ARTS)
        self.assertEqual(len(out), 2)
        self.assertEqual(report["items"], 2)
        self.assertEqual(report["quotes_total"], 3)
        self.assertEqual(report["quotes_kept"], 2)
        self.assertEqual(report["quotes_stripped"], 1)
        self.assertEqual(report["low_confidence"], 1)

    def test_citations_for_item(self):
        item = BriefItem(impact="", headline="A", summary="S.", citation_ids=[1, 3],
                         key_quotes=["The US announced sanctions"],
                         quote_citations=[1])
        cits = citations_for_item(item, ARTS)
        self.assertEqual([(c.article_id, c.span) for c in cits],
                         [(1, "The US announced sanctions"), (3, "Other story")])
        self.assertTrue(all(c.verified for c in cits))
        self.assertEqual(cits[0].url, "https://a.com/1")


class TestCitationsStorage(unittest.TestCase):
    def test_save_citations_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            conn = storage.connect(Path(td) / "t.db")
            item = BriefItem(impact="", headline="A", summary="S.", citation_ids=[1],
                             key_quotes=["The US announced sanctions"],
                             quote_citations=[1], event_id=7)
            n = storage.save_citations(conn, 3, [item], ARTS)
            self.assertEqual(n, 1)
            row = conn.execute("SELECT * FROM citations").fetchone()
            self.assertEqual(row["brief_id"], 3)
            self.assertEqual(row["event_id"], 7)
            self.assertEqual(row["article_id"], 1)
            self.assertIn("announced sanctions", row["span"])
            self.assertEqual(row["verified"], 1)
            conn.close()


if __name__ == "__main__":
    unittest.main()
