import unittest

from telescope.models import BriefItem, Citation, EventRelation
from telescope.render.brief import render_daily


class TestRender(unittest.TestCase):
    def test_citations(self):
        items = [BriefItem(headline="Big event", summary="Summary text.",
                           impact="Watch closely.", citation_ids=[11, 12],
                           topic="military", severity=1.8, score=2.5, source_count=3),
                 BriefItem(headline="Other event", summary="S2.",
                           impact="", citation_ids=[13], topic="economy", score=1.2),
                 BriefItem(headline="Third event", summary="S3.", impact="",
                           citation_ids=[11], topic="diplomacy", score=1.0),
                 BriefItem(headline="Fourth event", summary="S4.", impact="",
                           citation_ids=[13], topic="society", score=0.8)]
        arts = {
            11: {"id": 11, "title": "A", "url": "https://a.com/1", "source_id": "src1"},
            12: {"id": 12, "title": "B", "url": "https://b.com/2", "source_id": "src2"},
            13: {"id": 13, "title": "C", "url": "https://c.com/3", "source_id": "src1"},
        }
        out = render_daily("2026-09-01", items, arts, {"src1": "Src1", "src2": "Src2"},
                           {"backend": "rule", "articles": 3, "events": 2, "sources": 2})
        self.assertIn("# TeleScope 每日国际新闻简报 · 2026-09-01", out)
        self.assertIn("### 1. Big event [1][2]", out)
        self.assertIn("## 引用来源", out)
        self.assertIn("[3] C", out)
        self.assertIn("- **[社会]** Fourth event [3]", out)

    def test_degradation_transparency(self):
        items = [BriefItem(headline="LLM item", summary="S.", impact="",
                           citation_ids=[1], mode="openai-compat"),
                 BriefItem(headline="Rule item", summary="S.", impact="",
                           citation_ids=[1], mode="rule")]
        arts = {1: {"id": 1, "title": "A", "url": "https://a.com/1", "source_id": "s"}}
        out = render_daily("2026-09-01", items, arts, {"s": "S"},
                           {"backend": "openai-compat", "llm_count": 1,
                            "item_count": 2, "articles": 2, "events": 2, "sources": 1})
        self.assertIn("模式：openai-compat（LLM 分析 1/2，规则降级 1）", out)
        self.assertIn("⚠️ 规则降级", out)

    def test_quote_anchors_and_validation_stats(self):
        items = [BriefItem(headline="Big event", summary="S.", impact="",
                           citation_ids=[11], key_quotes=["Lead sentence one."],
                           quote_citations=[11], confidence="high"),
                 BriefItem(headline="Low conf event", summary="S.", impact="",
                           citation_ids=[11], confidence="low")]
        arts = {11: {"id": 11, "title": "A", "url": "https://a.com/1", "source_id": "s"}}
        out = render_daily("2026-09-01", items, arts, {"s": "S"},
                           {"backend": "rule", "quotes_total": 1, "quotes_kept": 1,
                            "low_confidence": 1})
        self.assertIn("- **引文**：Lead sentence one. [1]", out)
        self.assertIn("引用校验：引文 1/1，低置信 1", out)
        self.assertIn("⚠️ 引用待核", out)

    def test_lineage_timeline_and_mermaid(self):
        rel = EventRelation(prior_event_id=12, target_event_id=45, type="causal",
                            narrative="制裁决议引发被制裁方反制", confidence=0.85,
                            prior_title="US imposes new sanctions on Russia",
                            prior_date="2026-09-01",
                            evidence=[Citation(article_id=11, span="quote text")])
        items = [BriefItem(headline="Russia retaliates", summary="S.", impact="",
                           citation_ids=[11], event_id=45, traced=True,
                           lineage=[rel])]
        arts = {11: {"id": 11, "title": "A", "url": "https://a.com/1", "source_id": "s"}}
        out = render_daily("2026-09-11", items, arts, {"s": "S"},
                           {"backend": "rule"})
        self.assertIn("- **事件溯源**：", out)
        self.assertIn("2026-09-01｜前因｜US imposes new sanctions on Russia"
                      "[1]（置信 0.85）", out)
        self.assertIn("    - 制裁决议引发被制裁方反制", out)
        self.assertIn("```mermaid", out)
        self.assertIn("graph TD", out)
        self.assertIn("-->|前因| T45", out)

    def test_lineage_low_confidence_flagged(self):
        rel = EventRelation(prior_event_id=12, target_event_id=45, type="background",
                            narrative="背景关联", confidence=0.5,
                            prior_title="Prior event title", prior_date="2026-09-01",
                            evidence=[Citation(article_id=11, span="quote text")])
        items = [BriefItem(headline="H", summary="S.", impact="",
                           citation_ids=[11], traced=True, lineage=[rel])]
        arts = {11: {"id": 11, "title": "A", "url": "https://a.com/1", "source_id": "s"}}
        out = render_daily("2026-09-11", items, arts, {"s": "S"}, {"backend": "rule"})
        self.assertIn("（置信 0.50，待复核）", out)

    def test_lineage_isolated(self):
        items = [BriefItem(headline="New event", summary="S.", impact="",
                           citation_ids=[11], traced=True, lineage=[])]
        arts = {11: {"id": 11, "title": "A", "url": "https://a.com/1", "source_id": "s"}}
        out = render_daily("2026-09-11", items, arts, {"s": "S"}, {"backend": "rule"})
        self.assertIn("- **事件溯源**：历史窗口内无关联事件（新发/孤立事件）", out)


if __name__ == "__main__":
    unittest.main()
