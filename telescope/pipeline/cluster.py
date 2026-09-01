"""Online greedy event clustering (entity/title Jaccard within time window)."""
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
    def __init__(self, window_hours: int = 72, threshold: float = 0.30) -> None:
        self.window = dt.timedelta(hours=window_hours)
        self.threshold = threshold
        self.events: list[dict[str, Any]] = []

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
            s = max(jaccard(ents, ev["ents"]), jaccard(toks, ev["toks"]))
            if s > best_s:
                best_s, best = s, ev
        if best is not None and best_s >= self.threshold:
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
