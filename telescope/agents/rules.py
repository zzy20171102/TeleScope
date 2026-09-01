"""Deterministic rule engine: offline implementations for screener/summarizer.

Used as the default backend and as automatic fallback when LLM calls fail
(Factor 9: errors compacted to error_card, pipeline continues).

v0.2 hardening (P0/T1.1):
- ASCII keywords match with word boundaries + plural/verb suffixes
  (no more substring hits like "war" inside "ward"/"warning");
- topic/severity require strong signal: a title hit OR >=2 distinct keyword
  hits in body (single weak hit in long aggregated text no longer qualifies);
- topic and severity rule groups evaluated independently.
"""
from __future__ import annotations

import re
from typing import Any


def _compile(kws: list[str]) -> list[re.Pattern[str]]:
    pats: list[re.Pattern[str]] = []
    for kw in kws:
        kw = kw.strip()
        if not kw:
            continue
        if kw.isascii():
            pats.append(re.compile(r"\b" + re.escape(kw) + r"(?:s|es|ed|ing)?\b",
                                   re.IGNORECASE))
        else:
            pats.append(re.compile(re.escape(kw)))
    return pats


# priority-ordered topic rules (first match wins)
TOPIC_RULES: list[tuple[str, list[str]]] = [
    ("military", ["war", "missile", "airstrike", "air strike", "troops", "military",
                  "attack", "drone strike", "nuclear", "军队", "战争", "导弹", "空袭",
                  "袭击", "军演", "部队", "核武", "无人机", "军方"]),
    ("diplomacy", ["summit", "diplomatic talks", "sanction", "ambassador", "treaty",
                   "diplomat", "foreign minister", "会谈", "峰会", "制裁", "大使",
                   "外交", "外长", "访问", "协议", "断交"]),
    ("economy", ["economy", "trade", "tariff", "market", "inflation", "oil price",
                 "energy", "chip", "semiconductor", "export", "import", "gdp",
                 "central bank", "经济", "贸易", "关税", "市场", "通胀", "石油",
                 "能源", "芯片", "半导体", "出口", "进口", "央行"]),
    ("tech", ["artificial intelligence", "technology", "satellite", "cyber",
              "quantum", "人工智能", "科技", "卫星", "网络攻击", "量子"]),
    ("politics", ["election", "president", "parliament", "government", "protest",
                  "prime minister", "coup", "选举", "总统", "议会", "政府", "抗议",
                  "总理", "政变", "执政"]),
    ("society", ["earthquake", "flood", "wildfire", "epidemic", "migrant crisis",
                 "学校", "健康", "气候", "地震", "洪水", "山火", "移民潮"]),
]

SEVERITY_RULES: list[tuple[list[str], float]] = [
    (["war", "invade", "missile strike", "nuclear", "coup", "killed", "dead",
      "战争", "入侵", "导弹袭击", "核", "政变", "遇难", "身亡"], 1.8),
    (["sanction", "state of emergency", "resign", "air strike", "attack",
      "export control", "制裁", "紧急状态", "辞职", "空袭", "袭击", "出口管制"], 1.4),
    (["summit", "election", "tariff", "protest", "trade deal",
      "峰会", "选举", "关税", "抗议", "贸易协议"], 1.15),
]

_TOPIC_COMPILED = [(t, _compile(kws)) for t, kws in TOPIC_RULES]
_SEVERITY_COMPILED = [(_compile(kws), bump) for kws, bump in SEVERITY_RULES]


def _hits(text: str, pats: list[re.Pattern[str]]) -> int:
    return sum(1 for p in pats if p.search(text))


def _strong(title: str, body: str, pats: list[re.Pattern[str]]) -> bool:
    """Title hit OR >=2 distinct keyword hits in body."""
    return _hits(title, pats) >= 1 or _hits(body, pats) >= 2


def _text_of(cards: list[dict[str, Any]]) -> tuple[str, str]:
    title = " ".join(str(c.get("title", "")) for c in cards)
    body = " ".join(str(c.get("text", ""))[:1200] for c in cards)
    return title, body


def screen_rule(cards: list[dict[str, Any]]) -> dict[str, Any]:
    title, body = _text_of(cards)
    topic = "other"
    for t, pats in _TOPIC_COMPILED:
        if _strong(title, body, pats):
            topic = t
            break
    severity = 1.0
    for pats, bump in _SEVERITY_COMPILED:
        if _strong(title, body, pats):
            severity = bump
            break
    relevant = topic != "other"
    reason = f"rule: topic={topic}, severity={severity}"
    return {"relevant": relevant, "topic": topic, "severity": severity, "reason": reason}


_SENT_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")


def _sentences(text: str, n: int = 2, max_len: int = 220) -> list[str]:
    sents = [s.strip() for s in _SENT_SPLIT.split((text or "").strip()) if s.strip()]
    return [s[:max_len] for s in sents[:n]]


def summarize_rule(event: dict[str, Any],
                   articles: list[dict[str, Any]]) -> dict[str, Any]:
    arts = sorted(articles, key=lambda a: float(a.get("weight", 1.0)), reverse=True)
    if not arts:
        return {"headline": event.get("title", ""),
                "summary": "", "impact": "", "key_quotes": [], "citations": []}
    top = arts[0]
    headline = str(top.get("title", ""))[:80]
    summary_parts: list[str] = []
    quotes: list[str] = []
    for a in arts[:2]:
        lead = _sentences(str(a.get("text", "")) or str(a.get("title", "")), 2)
        if lead:
            summary_parts.append(" ".join(lead))
            quotes.append(lead[0])
    summary = "\n".join(summary_parts) or headline
    sev = float(event.get("severity", 1.0))
    if sev >= 1.6:
        impact = "高重要性事件，建议持续跟踪后续发展与各方回应。"
    elif sev >= 1.3:
        impact = "重要性较高，关注事态走向与关联各方表态。"
    else:
        impact = "常规动态，纳入背景观察。"
    return {
        "headline": headline,
        "summary": summary,
        "impact": impact,
        "key_quotes": quotes[:3],
        "citations": [int(a["id"]) for a in arts[:4] if a.get("id") is not None],
    }


def dispatch(prompt_name: str, context: dict[str, Any]) -> dict[str, Any]:
    # unwrap the unified {"items_json": ...} context used by both backends
    if "items_json" in context and "cards" not in context:
        try:
            import json

            payload = json.loads(context["items_json"])
            if prompt_name == "screener" and isinstance(payload, list):
                context = {"cards": payload}
            elif prompt_name == "summarizer" and isinstance(payload, dict):
                context = payload
        except (ValueError, TypeError):
            pass
    if prompt_name == "screener":
        cards = context.get("cards", [])
        results = []
        for c in cards:
            r = screen_rule([c])
            results.append({"id": int(c.get("id", 0)), **r})
        return {"results": results}
    if prompt_name == "summarizer":
        return summarize_rule(context.get("event", {}), context.get("articles", []))
    raise ValueError(f"unknown prompt: {prompt_name}")
