"""Citation/span verification core (M1.1).

Business rule: every analytical claim must carry a citation
(article_id + verbatim span + URL). Span existence is checked against the
article snapshot (title + content_text) deterministically in code; failed
spans are stripped and the item confidence is downgraded. The LLM never
audits its own output (Factor 8: orchestration/QC is deterministic code).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from typing import Any, Optional

from ..models import BriefItem, Citation

_WS = re.compile(r"\s+")
# Punctuation variants LLMs commonly normalize; unify before containment.
_TRANS = {ord("“"): chr(34), ord("”"): chr(34),
          ord("‘"): chr(39), ord("’"): chr(39),
          ord("–"): "-", ord("—"): "-", ord("…"): "..."}


def normalize_text(s: str) -> str:
    """NFKC + quote/dash unification + whitespace collapse + casefold;
    CJK text is unaffected by casefold and matches verbatim spans safely."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).translate(_TRANS)
    return _WS.sub(" ", s).casefold().strip()


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def span_exists(span: str, article: Optional[dict[str, Any]]) -> bool:
    """True when the normalized span occurs in the article snapshot.
    Very short spans are unverifiable (they match almost anywhere)."""
    if not article or not span:
        return False
    norm = normalize_text(span)
    min_len = 6 if _has_cjk(norm) else 12
    if len(norm) < min_len:
        return False
    haystack = normalize_text(
        f"{article.get("title", str())} "
        f"{article.get("text", str())}"
    )
    return norm in haystack


def _bind_quote(quote: str,
                cited_articles: list[dict[str, Any]]) -> Optional[int]:
    for art in cited_articles:
        if span_exists(quote, art) and art.get("id") is not None:
            return int(art["id"])
    return None


def review_item(item: BriefItem,
                articles_by_id: dict[int, dict[str, Any]]
                ) -> tuple[BriefItem, list[dict[str, Any]]]:
    """Validate one brief item; returns a sanitized copy + compact issues."""
    issues: list[dict[str, Any]] = []
    known = [articles_by_id[c] for c in item.citation_ids if c in articles_by_id]
    unknown = [c for c in item.citation_ids if c not in articles_by_id]
    if unknown:
        issues.append({"code": "citation_unknown", "article_ids": unknown})
    if not known:
        issues.append({"code": "citation_missing"})

    kept_quotes: list[str] = []
    kept_ids: list[Optional[int]] = []
    for q in item.key_quotes:
        aid = _bind_quote(q, known) if known else None
        if aid is not None:
            kept_quotes.append(q)
            kept_ids.append(aid)
        else:
            issues.append({"code": "quote_span_missing", "span": q[:80]})

    if not (item.summary or "").strip():
        issues.append({"code": "summary_empty"})

    confidence = "low" if issues else "high"
    new_item = replace(
        item,
        citation_ids=[c for c in item.citation_ids if c in articles_by_id],
        key_quotes=kept_quotes,
        quote_citations=kept_ids,
        confidence=confidence,
        issues=[i["code"] for i in issues],
    )
    return new_item, issues


def review_items(items: list[BriefItem],
                 articles_by_id: dict[int, dict[str, Any]]
                 ) -> tuple[list[BriefItem], dict[str, Any]]:
    """QC gate for a whole brief; returns sanitized items + audit report."""
    out: list[BriefItem] = []
    all_issues: list[dict[str, Any]] = []
    quotes_total = quotes_kept = cits_stripped = 0
    for it in items:
        new_it, issues = review_item(it, articles_by_id)
        out.append(new_it)
        quotes_total += len(it.key_quotes)
        quotes_kept += len(new_it.key_quotes)
        for i in issues:
            if i["code"] == "citation_unknown":
                cits_stripped += len(i["article_ids"])
            all_issues.append({"item": (it.headline or "")[:40], **i})
    report = {
        "items": len(items),
        "quotes_total": quotes_total,
        "quotes_kept": quotes_kept,
        "quotes_stripped": quotes_total - quotes_kept,
        "citations_stripped": cits_stripped,
        "low_confidence": sum(1 for i in out if i.confidence == "low"),
        "issues": all_issues,
    }
    return out, report


def citations_for_item(item: BriefItem,
                       articles_by_id: dict[int, dict[str, Any]]
                       ) -> list[Citation]:
    """Materialize storage-ready citations: verified quote spans first,
    then remaining citation_ids represented by their verbatim titles."""
    out: list[Citation] = []
    seen: set[int] = set()
    for q, aid in zip(item.key_quotes, item.quote_citations):
        art = articles_by_id.get(aid) if aid is not None else None
        if art is None:
            continue
        out.append(Citation(article_id=int(art["id"]), span=q,
                            url=str(art.get("url", "")), verified=True))
        seen.add(int(art["id"]))
    for cid in item.citation_ids:
        if cid in seen:
            continue
        art = articles_by_id.get(cid)
        if art is None:
            continue
        span = str(art.get("title", ""))
        # the title IS part of the article snapshot by construction
        out.append(Citation(article_id=cid, span=span,
                            url=str(art.get("url", "")), verified=bool(span)))
        seen.add(cid)
    return out
