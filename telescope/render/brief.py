"""Daily brief Markdown rendering with citation anchors [n].

P0/T1.3: header shows LLM/rule ratio; items degraded to rule mode are marked.
M1.1: header shows citation validation stats; verified key quotes are
rendered with [n] anchors bound to the article the span was found in;
items that failed span validation are flagged as low confidence.
"""
from __future__ import annotations

from typing import Any

from ..models import BriefItem

TOPIC_ZH = {"military": "军事", "diplomacy": "外交", "economy": "经济",
            "tech": "科技", "politics": "政治", "society": "社会", "other": "综合"}
TYPE_ZH = {"causal": "前因", "escalation": "升级", "de_escalation": "缓和",
           "response": "回应", "background": "背景", "same_actor": "同一行为体",
           "thematic_parallel": "同题平行"}


def _mq(s: str) -> str:
    return s.replace(chr(34), chr(39)).replace("|", "/")[:60]


def _mermaid(item: BriefItem) -> list[str]:
    if not item.lineage:
        return []
    tid = f"T{item.event_id or 0}"
    out = ["```mermaid", "graph TD",
           f"  {tid}[{_mq(item.headline)}]"]
    for rel in item.lineage:
        pid = f"P{rel.prior_event_id}"
        out.append(f"  {pid}[{_mq(rel.prior_date + chr(32) + rel.prior_title)}]")
        out.append(f"  {pid} -->|{TYPE_ZH.get(rel.type, rel.type)}| {tid}")
    out.append("```")
    return out


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
        for rel in it.lineage:
            for c in rel.evidence:
                if c.article_id in articles_by_id:
                    reg(c.article_id)

    backend = str(meta.get("backend", "rule"))
    degraded = backend != "rule"
    generated_at = str(meta.get("generated_at", ""))
    llm_count = int(meta.get("llm_count", 0) or 0)
    item_count = int(meta.get("item_count", len(items)))
    articles_n = int(meta.get("articles", 0) or 0)
    events_n = int(meta.get("events", 0) or 0)
    sources_n = int(meta.get("sources", 0) or 0)
    quotes_total = int(meta.get("quotes_total", 0) or 0)
    quotes_kept = int(meta.get("quotes_kept", 0) or 0)
    low_conf = int(meta.get("low_confidence", 0) or 0)

    lines: list[str] = []
    lines.append(f"# TeleScope 每日国际新闻简报 · {date}")
    lines.append("")
    header = f"> 生成时间：{generated_at} ｜ 模式：{backend}"
    if degraded:
        header += f"（LLM 分析 {llm_count}/{item_count}，规则降级 {len(items) - llm_count}）"
    header += f" ｜ 文章：{articles_n} ｜ 事件：{events_n} ｜ 来源：{sources_n} 家"
    if quotes_total:
        header += f" ｜ 引用校验：引文 {quotes_kept}/{quotes_total}"
        if low_conf:
            header += f"，低置信 {low_conf}"
    lines.append(header)
    lines.append("")
    top = items[:3]
    rest = items[3:]
    if top:
        lines.append("## 头条要闻")
        lines.append("")
        for i, it in enumerate(top, 1):
            lines.append(f"### {i}. {it.headline} {_anchors(it.citation_ids, index)}")
            lines.append("")
            flag = " ｜ ⚠️ 规则降级" if (degraded and it.mode == "rule") else ""
            if it.confidence == "low":
                flag += " ｜ ⚠️ 引用待核"
            lines.append(f"- **分类**：{TOPIC_ZH.get(it.topic, it.topic)} ｜ "
                         f"**严重度**：{it.severity:.1f} ｜ **热度**：{it.score:.2f} ｜ "
                         f"**报道源**：{it.source_count} 家{flag}")
            for para in (it.summary or "").split("\n"):
                if para.strip():
                    lines.append(f"- {para.strip()}")
            for q, aid in zip(it.key_quotes, it.quote_citations):
                anchor = f" [{index[aid]}]" if aid is not None and aid in index else ""
                lines.append(f"- **引文**：{q}{anchor}")
            if it.impact:
                lines.append(f"- **影响初判**：{it.impact}")
            if it.traced:
                if it.lineage:
                    lines.append("- **事件溯源**：")
                    for rel in it.lineage:
                        anchors = "".join(f"[{index[c.article_id]}]"
                                          for c in rel.evidence
                                          if c.article_id in index)
                        flag = "" if rel.confidence >= 0.7 else "，待复核"
                        lines.append(f"  - {rel.prior_date}｜"
                                     f"{TYPE_ZH.get(rel.type, rel.type)}｜"
                                     f"{rel.prior_title}{anchors}"
                                     f"（置信 {rel.confidence:.2f}{flag}）")
                        if rel.narrative:
                            lines.append(f"    - {rel.narrative}")
                    if i == 1:
                        block = _mermaid(it)
                        if block:
                            lines.append("")
                            lines.extend(block)
                else:
                    lines.append("- **事件溯源**：历史窗口内无关联事件（新发/孤立事件）")
            lines.append("")
    if rest:
        lines.append("## 分类速览")
        lines.append("")
        for it in rest:
            flag = " ⚠️" if (degraded and it.mode == "rule") else ""
            if it.confidence == "low":
                flag += " ⚠️引用待核"
            lines.append(f"- **[{TOPIC_ZH.get(it.topic, it.topic)}]** {it.headline} "
                         f"{_anchors(it.citation_ids, index)}（{it.source_count} 源）{flag}")
        lines.append("")
    lines.append("## 引用来源")
    lines.append("")
    for ref in refs:
        a = ref["article"]
        if not a:
            continue
        num = ref["n"]
        src = source_names.get(str(a.get("source_id", "")), a.get("source_id", ""))
        title = str(a.get("title", ""))
        url = str(a.get("url", ""))
        lines.append(f"[{num}] {title} — {src} — {url}")
    lines.append("")
    lines.append("---")
    lines.append("*本简报由 TeleScope 自动生成，内容基于所列公开来源；"
                 "引用请以原文为准。分析结论仅供研究参考。*")
    return "\n".join(lines) + "\n"
