"""F2 Stage-1 hybrid recall (DESIGN 4.3.1): deterministic, LLM-free.

Channels: entity overlap (weighted highest), lexical similarity, topic match
and a time-decay window. The design reserves a vector channel for event
embeddings; until M2 (pgvector) it is proxied by lexical token-set Jaccard.
Near-duplicate events (same story re-clustered by a later run, title
Jaccard >= 0.60) are skipped: they are not lineage, they are duplicates.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from .cluster import jaccard
from .normalize import token_set

NEAR_DUP_TOK = 0.60
MIN_REL = 0.15
W_ENTITY, W_LEX, W_TIME, W_TOPIC = 0.45, 0.25, 0.15, 0.15


def _parse_ts(s: str) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return dt.datetime.now(dt.timezone.utc)


def _days_between(a: dt.datetime, b: dt.datetime) -> float:
    return abs((a - b).total_seconds()) / 86400.0


def recall(target: dict[str, Any], history: list[dict[str, Any]],
           top_k: int = 6, window_days: int = 180
           ) -> list[dict[str, Any]]:
    """Return scored candidate cards for the EventTracer agent."""
    target_ents = set(target.get("entities", []))
    target_toks = token_set(str(target.get("title", "")))
    target_ts = _parse_ts(str(target.get("first_seen", "")))
    scored: list[tuple[float, dict[str, Any]]] = []
    for ev in history:
        cand_ts = _parse_ts(str(ev.get("first_seen", "")))
        # lineage edges point backwards in time (same-day allowed)
        if cand_ts > target_ts + dt.timedelta(days=1):
            continue
        delta_days = _days_between(target_ts, cand_ts)
        if delta_days > window_days:
            continue  # hard time-window filter (DESIGN 4.3.1)
        cand_ents = set(ev.get("entities", []))
        cand_toks = token_set(str(ev.get("title", "")))
        if jaccard(target_toks, cand_toks) >= NEAR_DUP_TOK:
            continue  # re-clustered same story, not a prior cause
        shared = target_ents & cand_ents
        ent_j = jaccard(target_ents, cand_ents)
        lex_j = jaccard(target_toks, cand_toks)
        time_decay = max(0.0, 1.0 - delta_days / max(window_days, 1))
        topic_match = 1.0 if (target.get("category") and
                              target.get("category") == ev.get("category")) else 0.0
        rel = (W_ENTITY * ent_j + W_LEX * lex_j +
               W_TIME * time_decay + W_TOPIC * topic_match)
        # recall channels: shared entity OR non-trivial lexical OR same topic
        if not shared and lex_j < 0.15 and not topic_match:
            continue
        if rel < MIN_REL:
            continue
        card = {k: v for k, v in ev.items() if k != "entities"}
        card["entities"] = sorted(cand_ents)[:12]
        card["shared_entities"] = sorted(shared)[:8]
        card["score"] = round(rel, 4)
        scored.append((rel, card))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [card for _, card in scored[:top_k]]
