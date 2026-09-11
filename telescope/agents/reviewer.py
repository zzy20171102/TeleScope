"""Reviewer agent: deterministic citation QC gate (M1.1).

Small, focused, stateless (Factor 10/12). Verifies that every brief item
citation and key quote traces back to verbatim article snapshot text;
strips failed spans and downgrades item confidence. No LLM is involved:
span/numeric audits are computed in code per project business rules.
"""
from __future__ import annotations

from typing import Any

from ..models import BriefItem
from ..pipeline.verify import review_items


class Reviewer:
    name = "reviewer"

    def review(self, items: list[BriefItem],
               articles_by_id: dict[int, dict[str, Any]]
               ) -> tuple[list[BriefItem], dict[str, Any]]:
        return review_items(items, articles_by_id)
