"""Screener agent: small, focused, stateless (Factor 10/12)."""
from __future__ import annotations

import json
from typing import Any

from ..models import ScreenResult
from .llm import RuleBackend


class Screener:
    def __init__(self, backend: RuleBackend | Any) -> None:
        self.backend = backend

    def screen(self, cards: list[dict[str, Any]]) -> list[ScreenResult]:
        if not cards:
            return []
        try:
            data = self.backend.complete_json(
                "screener", {"items_json": json.dumps(cards, ensure_ascii=False)})
            results = []
            for r in data.get("results", []):
                results.append(ScreenResult(
                    id=int(r["id"]),
                    relevant=bool(r.get("relevant", False)),
                    topic=str(r.get("topic", "other")),
                    severity=float(r.get("severity", 1.0)),
                    reason=str(r.get("reason", "")),
                ))
            if len(results) == len(cards):
                return results
            raise ValueError("screener result count mismatch")
        except Exception:  # fallback to rules (Factor 9)
            from . import rules

            out = []
            for c in cards:
                r = rules.screen_rule([c])
                out.append(ScreenResult(id=int(c.get("id", 0)), **r))
            return out
