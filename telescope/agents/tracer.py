"""EventTracer agent (F2 Stage-2, M1/T2.2): judges target <-> prior
event relations from provided event cards only.

The LLM never generates new facts; deterministic post-validation enforces:
candidate membership, type whitelist, temporal direction for causal/
escalation (violations downgrade to thematic_parallel), and verbatim
evidence spans against article snapshots. Relations without surviving
evidence are dropped (anti-hallucination: never force a link).
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Any

from ..models import Citation, EventRelation
from ..pipeline.verify import span_exists
from .llm import RuleBackend

RELATION_TYPES = {"causal", "escalation", "de_escalation", "response",
                  "background", "same_actor", "thematic_parallel"}
DIRECTIONAL = {"causal", "escalation"}


def _parse_ts(s: str) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return dt.datetime.now(dt.timezone.utc)


class EventTracer:
    def __init__(self, backend: RuleBackend | Any) -> None:
        self.backend = backend
        self.last_error: str = ""

    @staticmethod
    def _card(event: dict[str, Any]) -> dict[str, Any]:
        arts = [{"id": a.get("id"), "title": str(a.get("title", ""))[:120],
                 "text": str(a.get("text", ""))[:300]}
                for a in event.get("articles", [])[:2]]
        return {"id": event.get("id"), "title": str(event.get("title", ""))[:160],
                "category": event.get("category", "other"),
                "severity": event.get("severity", 1.0),
                "first_seen": event.get("first_seen", ""),
                "entities": event.get("entities", []),
                "shared_entities": event.get("shared_entities", []),
                "recall_score": event.get("score", 0.0),
                "articles": arts}

    def trace(self, target: dict[str, Any], candidates: list[dict[str, Any]],
              article_map: dict[int, dict[str, Any]]
              ) -> tuple[list[EventRelation], dict[str, Any]]:
        try:
            data = self.backend.complete_json(
                "event_tracer",
                {"items_json": json.dumps(
                    {"target": self._card(target),
                     "candidates": [self._card(c) for c in candidates]},
                    ensure_ascii=False)})
            relations, isolated = self._validate(data, target, candidates, article_map)
        except Exception as e:  # fallback to rules (Factor 9)
            from . import rules

            self.last_error = f"{type(e).__name__}: {e}"[:200]
            data = rules.trace_rule(target, candidates)
            relations, isolated = self._validate(data, target, candidates, article_map)
        meta = {"mode": getattr(self.backend, "name", "rule"),
                "candidates": len(candidates), "relations": len(relations),
                "isolated": bool(isolated) or not relations,
                "error": self.last_error}
        return relations, meta

    def _validate(self, data: dict[str, Any], target: dict[str, Any],
                  candidates: list[dict[str, Any]],
                  article_map: dict[int, dict[str, Any]]
                  ) -> tuple[list[EventRelation], bool]:
        cand_by_id: dict[int, dict[str, Any]] = {}
        for c in candidates:
            try:
                cand_by_id[int(c["id"])] = c
            except (KeyError, TypeError, ValueError):
                continue
        try:
            target_id = int(target.get("id") or 0)
        except (TypeError, ValueError):
            target_id = 0
        target_ts = _parse_ts(str(target.get("first_seen", "")))
        out: list[EventRelation] = []
        for r in data.get("relations", []):
            try:
                pid = int(r.get("prior_event"))
            except (TypeError, ValueError):
                continue
            cand = cand_by_id.get(pid)
            if cand is None:
                continue
            rtype = str(r.get("type", "background"))
            if rtype not in RELATION_TYPES:
                rtype = "background"
            cand_ts = _parse_ts(str(cand.get("first_seen", "")))
            if rtype in DIRECTIONAL and cand_ts > target_ts + dt.timedelta(days=1):
                rtype = "thematic_parallel"  # direction violated -> downgrade
            evidence: list[Citation] = []
            for e in r.get("evidence", [])[:3]:
                aid = e.get("article_id")
                span = str(e.get("quote_span", ""))
                art = article_map.get(aid) if aid is not None else None
                if art is None or not span_exists(span, art):
                    continue
                evidence.append(Citation(article_id=int(aid), span=span,
                                         url=str(art.get("url", "")), verified=True))
            if not evidence:
                continue
            try:
                conf = float(r.get("confidence", 0.0))
            except (TypeError, ValueError):
                conf = 0.0
            conf = min(max(conf, 0.0), 1.0)
            out.append(EventRelation(
                prior_event_id=pid, target_event_id=target_id, type=rtype,
                narrative=str(r.get("narrative", ""))[:200],
                evidence=evidence[:2], confidence=conf,
                prior_title=str(cand.get("title", ""))[:100],
                prior_date=str(cand.get("first_seen", ""))[:10],
                status="auto" if conf >= 0.7 else "review"))
        out.sort(key=lambda x: x.confidence, reverse=True)
        return out[:3], bool(data.get("isolated", False))
