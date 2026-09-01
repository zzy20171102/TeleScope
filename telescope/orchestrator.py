"""Deterministic DAG orchestrator (Factor 8): collect -> dedup -> store ->
cluster -> score -> screen -> summarize -> render -> publish."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable, Optional

from . import storage
from .agents.llm import get_backend
from .agents.screener import Screener
from .agents.summarizer import Summarizer
from .collectors import rss
from .config import BRIEF_DIR, DB_PATH, load_sources
from .models import Article
from .pipeline.cluster import OnlineClusterer
from .pipeline.dedup import InBatchDeduper
from .pipeline.normalize import detect_lang, extract_entities, url_hash
from .pipeline.scoring import hot_score
from .render.brief import render_daily


def _mk_article(source, rec: dict[str, str]) -> Article:
    title = rss.strip_html(rec.get("title", ""))
    desc = rss.strip_html(rec.get("desc", ""))
    text = f"{title}. {desc}" if desc else title
    return Article(
        source_id=source.id,
        url=rec.get("link", ""),
        url_hash=url_hash(rec.get("link", "")),
        title=title,
        content_text=desc or title,
        lang=detect_lang(text),
        published_at=rss.parse_date(rec.get("date", "")),
        entities=extract_entities(text, limit=12),
    )


def collect_all(sources, fetch_fn: Callable[[str], bytes] = rss.fetch_url,
                on_error: Optional[Callable[[str, Exception], None]] = None):
    arts: list[Article] = []
    errors: list[dict[str, str]] = []
    for src in sources:
        try:
            data = fetch_fn(src.url)
            recs = rss.parse_feed(data)
            arts.extend(_mk_article(src, r) for r in recs)
        except Exception as e:  # noqa: BLE001
            errors.append({"source": src.id, "error": str(e)[:300]})
            if on_error:
                on_error(src.id, e)
    return arts, errors


def run_daily(hours: int = 24, top_n: int = 6,
              inject_articles: Optional[list[Article]] = None,
              db_path: "Path | str | None" = None,
              brief_dir: "Path | str | None" = None,
              trigger: str = "manual") -> Path:
    db_path = Path(db_path) if db_path else DB_PATH
    brief_dir = Path(brief_dir) if brief_dir else BRIEF_DIR
    brief_dir.mkdir(parents=True, exist_ok=True)
    conn = storage.connect(db_path)
    backend = get_backend()
    now = dt.datetime.now(dt.timezone.utc)
    date = now.date().isoformat()
    run_id = storage.start_run(conn, "daily", trigger)

    sources = load_sources(enabled_only=True)
    for s in sources:
        storage.upsert_source(conn, s)
    source_weights = {s.id: s.weight for s in sources}
    source_names = {s.id: s.name for s in sources}

    # 1. collect (or inject for tests)
    if inject_articles is not None:
        raw: list[Article] = list(inject_articles)
        errors: list[dict[str, str]] = []
    else:
        raw, errors = collect_all(sources)
    for e in errors:
        storage.record_step(conn, run_id, "collector", e["source"],
                            error_card=json.dumps(e, ensure_ascii=False))

    # 2. in-batch dedup + idempotent store
    deduper = InBatchDeduper()
    stored: list[Article] = []
    dup_count = 0
    for a in raw:
        if deduper.is_duplicate(a):
            dup_count += 1
            continue
        aid = storage.upsert_article(conn, a)
        if aid is not None:
            a.id = aid
            stored.append(a)

    # 3. load window from db (covers previous fetches too)
    window_arts = storage.articles_since(conn, hours=hours)
    if not window_arts:
        window_arts = stored

    # 4. cluster into events
    clusterer = OnlineClusterer()
    for a in sorted(window_arts, key=lambda x: x.published_at):
        clusterer.add(a)
    events = clusterer.to_events()

    # 5. screen (per event, rule/LLM) and attach topic/severity
    screener = Screener(backend)
    arts_by_id = {a.id: a for a in window_arts}
    cards = []
    for i, ev in enumerate(events, 1):
        ev.id = i
        card_arts = [arts_by_id[aid] for aid in ev.article_ids if aid in arts_by_id]
        text = " ".join(f"{a.title}. {a.content_text[:300]}" for a in card_arts)
        cards.append({"id": i, "title": ev.title, "text": text,
                      "article_ids": ev.article_ids})
    screen_results = {r.id: r for r in screener.screen(cards)}
    for ev in events:
        r = screen_results.get(ev.id)
        if r:
            ev.category = r.topic
            ev.severity = max(ev.severity, r.severity)
        ev.score = hot_score(ev, source_weights, now=now)
    events = [e for e in events
              if screen_results.get(e.id) is None or screen_results[e.id].relevant]
    events.sort(key=lambda e: e.score, reverse=True)

    # 6. summarize top events
    summarizer = Summarizer(backend)
    items = []
    for ev in events[:top_n]:
        card_arts = [arts_by_id[aid] for aid in ev.article_ids if aid in arts_by_id]
        payload_arts = [{"id": a.id, "title": a.title, "text": a.content_text,
                         "source_id": a.source_id, "lang": a.lang,
                         "weight": source_weights.get(a.source_id, 1.0)}
                        for a in card_arts]
        item = summarizer.summarize(
            {"id": ev.id, "title": ev.title, "category": ev.category,
             "severity": ev.severity, "score": ev.score},
            payload_arts,
        )
        items.append(item)
        storage.save_event(conn, ev)

    # 7. render + publish
    articles_by_id = {
        a.id: {"id": a.id, "title": a.title, "url": a.url, "source_id": a.source_id}
        for a in window_arts
    }
    meta = {"generated_at": now.isoformat(timespec="seconds"),
            "backend": backend.name, "articles": len(window_arts),
            "events": len(events), "sources": len({a.source_id for a in window_arts})}
    body = render_daily(date, items, articles_by_id, source_names, meta)
    out_path = brief_dir / f"{date}.md"
    out_path.write_text(body, encoding="utf-8")
    storage.save_brief(conn, date, "daily", f"TeleScope 每日简报 {date}", body)
    storage.finish_run(conn, run_id, "done", {
        "fetched": len(raw), "stored": len(stored), "duplicates": dup_count,
        "events": len(events), "brief": str(out_path), "errors": len(errors),
    })
    conn.close()
    return out_path
