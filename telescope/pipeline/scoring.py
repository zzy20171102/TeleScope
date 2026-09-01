"""Hot-score: source weight x spread x volume x severity x recency decay."""
from __future__ import annotations

import datetime as dt
import math
from typing import Optional

from ..models import Event


def hot_score(ev: Event, source_weights: dict[str, float],
              now: Optional[dt.datetime] = None) -> float:
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        last = dt.datetime.fromisoformat(ev.last_seen)
        if last.tzinfo is None:
            last = last.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        last = now
    age_h = max((now - last).total_seconds() / 3600.0, 0.0)
    w = max((source_weights.get(s, 1.0) for s in ev.source_ids), default=1.0)
    spread = 1.0 + 0.25 * (len(set(ev.source_ids)) - 1)
    vol = math.log1p(len(ev.article_ids) or 1)
    recency = math.exp(-age_h / 48.0)
    return round(w * spread * vol * max(ev.severity, 0.1) * recency, 4)
