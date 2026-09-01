import unittest

from telescope.models import BriefItem
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


if __name__ == "__main__":
    unittest.main()
