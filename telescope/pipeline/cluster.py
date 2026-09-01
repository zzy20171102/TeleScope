"""Online greedy event clustering with anti-drift scoring (P0/T1.2).

v0.2 anti-drift rules:
- lexical: title/body token jaccard >= strong_tok merges directly;
- entity: jaccard >= strong_ent AND >= 2 shared entities (blocks two
  different stories that merely share one country, keeps cross-lingual
  same-event merging alive);
- combined: ent >= 0.5 and tok >= 0.15 (weak but corroborated signal).
Matching uses both the event's SEED (first article) and accumulated
representation to resist cluster drift.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from ..models import Article, Event
from .normalize import token_set


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _parse_ts(s: str) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return dt.datetime.now(dt.timezone.utc)


class OnlineClusterer:
    def __init__(self, window_hours: int = 72,
                 strong_tok: float = 0.35, strong_ent: float = 0.67) -> None:
        self.window = dt.timedelta(hours=window_hours)
        self.strong_tok = strong_tok
        self.strong_ent = strong_ent
        self.events: list[dict[str, Any]] = []

    def _score(self, ents: set[str], toks: set[str], ev: dict[str, Any]) -> float:
        ent_j = max(jaccard(ents, ev["seed_ents"]), jaccard(ents, ev["ents"]))
        tok_j = max(jaccard(toks, ev["seed_toks"]), jaccard(toks, ev["toks"]))
        shared_ents = max(len(ents & ev["seed_ents"]), len(ents & ev["ents"]))
        if tok_j >= self.strong_tok:
            return tok_j
        if ent_j >= self.strong_ent and shared_ents >= 2:
            return ent_j
        if ent_j >= 0.5 and tok_j >= 0.15:
            return 0.5 * ent_j + 0.5 * tok_j
        return 0.0

    def add(self, art: Article) -> int:
        ents = set(art.entities)
        toks = token_set(art.title + " " + art.content_text[:500])
        ts = _parse_ts(art.published_at)
        best: Optional[dict[str, Any]] = None
        best_s = 0.0
        for ev in self.events:
            age = ts - ev["last_ts"]
            if age > self.window or age < -self.window:
                continue
            s = self._score(ents, toks, ev)
            if s > best_s:
                best_s, best = s, ev
        if best is not None and best_s >= 0.30:
            best["article_ids"].append(art.id)
            best["source_ids"].append(art.source_id)
            best["ents"] |= ents
            best["toks"] |= toks
            if ts > best["last_ts"]:
                best["last_ts"] = ts
            if ts < best["first_ts"]:
                best["first_ts"] = ts
            return best["_id"]
        ev = {
            "_id": len(self.events) + 1,
            "title": art.title,
            "article_ids": [art.id],
            "source_ids": [art.source_id],
            "ents": set(ents),
            "toks": set(toks),
            "seed_ents": set(ents),
            "seed_toks": set(toks),
            "first_ts": ts,
            "last_ts": ts,
        }
        self.events.append(ev)
        return ev["_id"]

    def to_events(self, topic_of: Optional[dict[int, str]] = None,
                  severity_of: Optional[dict[int, float]] = None) -> list[Event]:
        topic_of = topic_of or {}
        severity_of = severity_of or {}
        out: list[Event] = []
        for ev in self.events:
            aids = [a for a in ev["article_ids"] if a is not None]
            if not aids:
                continue
            out.append(Event(
                title=ev["title"],
                category=topic_of.get(ev["_id"], "other"),
                severity=max([severity_of.get(a, 1.0) for a in aids] or [1.0]),
                article_ids=aids,
                source_ids=list(dict.fromkeys(ev["source_ids"])),
                first_seen=ev["first_ts"].isoformat(timespec="seconds"),
                last_seen=ev["last_ts"].isoformat(timespec="seconds"),
            ))
        return out
