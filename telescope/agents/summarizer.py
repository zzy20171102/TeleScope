"""Summarizer agent: produces citation-bearing brief items."""
from __future__ import annotations

import json
from typing import Any

from ..models import BriefItem
from .llm import RuleBackend


class Summarizer:
    def __init__(self, backend: RuleBackend | Any) -> None:
        self.backend = backend

    def summarize(self, event: dict[str, Any],
                  articles: list[dict[str, Any]]) -> BriefItem:
        try:
            data = self.backend.complete_json(
                "summarizer",
                {"items_json": json.dumps({"event": event, "articles": articles},
                                          ensure_ascii=False)},
            )
            headline = str(data.get("headline", event.get("title", "")))[:120]
            summary = str(data.get("summary", ""))
            impact = str(data.get("impact", ""))
            quotes = [str(q)[:300] for q in data.get("key_quotes", [])][:3]
            cits = [int(c) for c in data.get("citations", []) if isinstance(c, int)]
        except Exception:  # fallback to rules
            from . import rules

            data = rules.summarize_rule(event, articles)
            headline = str(data["headline"])[:120]
            summary = data["summary"]
            impact = data["impact"]
            quotes = data["key_quotes"]
            cits = data["citations"]
        valid_ids = {int(a["id"]) for a in articles if a.get("id") is not None}
        cits = [c for c in cits if c in valid_ids] or \
            [int(a["id"]) for a in articles[:1] if a.get("id") is not None]
        return BriefItem(
            headline=headline,
            summary=summary,
            impact=impact,
            key_quotes=quotes,
            citation_ids=cits,
            topic=str(event.get("category", "other")),
            severity=float(event.get("severity", 1.0)),
            score=float(event.get("score", 0.0)),
            source_count=len({a.get("source_id") for a in articles}),
        )
