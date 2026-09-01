"""Daily brief Markdown rendering with citation anchors [n]."""
from __future__ import annotations

from typing import Any

from ..models import BriefItem

TOPIC_ZH = {"military": "军事", "diplomacy": "外交", "economy": "经济",
            "tech": "科技", "politics": "政治", "society": "社会", "other": "综合"}


def _anchors(citation_ids: list[int], index: dict[int, int]) -> str:
    return "".join(f"[{index[cid]}]" for cid in citation_ids if cid in index)


def render_daily(date: str, items: list[BriefItem],
                 articles_by_id: dict[int, dict[str, Any]],
                 source_names: dict[str, str],
                 meta: dict[str, Any]) -> str:
    """Render items; citation index is assigned in order of first appearance."""
    index: dict[int, int] = {}
    refs: list[dict[str, Any]] = []

    def reg(cid: int) -> int:
        if cid not in index:
            index[cid] = len(refs) + 1
            refs.append({"n": len(refs) + 1, "article": articles_by_id.get(cid)})
        return index[cid]

    for it in items:
        for cid in it.citation_ids:
            if cid in articles_by_id:
                reg(cid)

    lines: list[str] = []
    lines.append(f"# TeleScope 每日国际新闻简报 · {date}")
    lines.append("")
    lines.append(f"> 生成时间：{meta.get('generated_at', '')} ｜ 模式：{meta.get('backend', 'rule')} ｜ "
                 f"文章：{meta.get('articles', 0)} ｜ 事件：{meta.get('events', 0)} ｜ "
                 f"来源：{meta.get('sources', 0)} 家")
    lines.append("")
    top = items[:3]
    rest = items[3:]
    if top:
        lines.append("## 头条要闻")
        lines.append("")
        for i, it in enumerate(top, 1):
            lines.append(f"### {i}. {it.headline} {_anchors(it.citation_ids, index)}")
            lines.append("")
            lines.append(f"- **分类**：{TOPIC_ZH.get(it.topic, it.topic)} ｜ "
                         f"**严重度**：{it.severity:.1f} ｜ **热度**：{it.score:.2f} ｜ "
                         f"**报道源**：{it.source_count} 家")
            for para in (it.summary or "").split("\n"):
                if para.strip():
                    lines.append(f"- {para.strip()}")
            if it.impact:
                lines.append(f"- **影响初判**：{it.impact}")
            lines.append("")
    if rest:
        lines.append("## 分类速览")
        lines.append("")
        for it in rest:
            lines.append(f"- **[{TOPIC_ZH.get(it.topic, it.topic)}]** {it.headline} "
                         f"{_anchors(it.citation_ids, index)}（{it.source_count} 源）")
        lines.append("")
    lines.append("## 引用来源")
    lines.append("")
    for ref in refs:
        a = ref["article"]
        if not a:
            continue
        src = source_names.get(str(a.get("source_id", "")), a.get("source_id", ""))
        lines.append(f"[{ref['n']}] {a.get('title', '')} — {src} — {a.get('url', '')}")
    lines.append("")
    lines.append("---")
    lines.append("*本简报由 TeleScope 自动生成，内容基于所列公开来源；"
                 "引用请以原文为准。分析结论仅供研究参考。*")
    return "\n".join(lines) + "\n"
