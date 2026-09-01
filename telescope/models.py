"""Core domain models (stdlib dataclasses, Factor 4: structured I/O)."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Optional


def _now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


@dataclass
class Source:
    id: str
    name: str
    url: str
    type: str = "rss"
    language: str = "en"
    region: str = "global"
    perspective: str = "unlabeled"
    weight: float = 1.0
    fetch_interval_minutes: int = 60
    enabled: bool = True

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Source":
        return cls(
            id=str(d["id"]),
            name=str(d.get("name", d["id"])),
            url=str(d.get("url", "")),
            type=str(d.get("type", "rss")),
            language=str(d.get("language", "en")),
            region=str(d.get("region", "global")),
            perspective=str(d.get("perspective", "unlabeled")),
            weight=float(d.get("weight", 1.0)),
            fetch_interval_minutes=int(d.get("fetch_interval_minutes", 60)),
            enabled=bool(d.get("enabled", True)),
        )


@dataclass
class Article:
    source_id: str
    url: str
    url_hash: str
    title: str
    content_text: str = ""
    lang: str = "en"
    published_at: str = ""
    fetched_at: str = field(default_factory=_now)
    entities: list[str] = field(default_factory=list)
    topic: str = ""
    id: Optional[int] = None


@dataclass
class Event:
    title: str
    category: str = "other"
    severity: float = 1.0
    article_ids: list[int] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    score: float = 0.0
    id: Optional[int] = None


@dataclass
class ScreenResult:
    id: int
    relevant: bool
    topic: str
    severity: float
    reason: str = ""


@dataclass
class BriefItem:
    headline: str
    summary: str
    impact: str
    key_quotes: list[str] = field(default_factory=list)
    citation_ids: list[int] = field(default_factory=list)
    topic: str = "other"
    severity: float = 1.0
    score: float = 0.0
    source_count: int = 1


def to_dict(obj: Any) -> dict[str, Any]:
    return dataclasses.asdict(obj)
