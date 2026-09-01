"""Deduplication: exact URL hash + in-batch fuzzy title matching."""
from __future__ import annotations

import difflib

from ..models import Article


def titles_similar(a: str, b: str, threshold: float = 0.72) -> bool:
    return difflib.SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio() >= threshold


class InBatchDeduper:
    """Keeps the first occurrence of near-identical items within one fetch batch."""

    def __init__(self, threshold: float = 0.72) -> None:
        self.threshold = threshold
        self._seen_urls: set[str] = set()
        self._titles: list[tuple[str, str]] = []  # (lang, title)

    def is_duplicate(self, art: Article) -> bool:
        if art.url_hash in self._seen_urls:
            return True
        self._seen_urls.add(art.url_hash)
        for lang, title in self._titles:
            if lang == art.lang and titles_similar(title, art.title, self.threshold):
                return True
        self._titles.append((art.lang, art.title))
        return False
