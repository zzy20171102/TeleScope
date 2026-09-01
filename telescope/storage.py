"""SQLite storage: business data + execution audit (Factor 5: unified state)."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from .models import Article

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
  id TEXT PRIMARY KEY, name TEXT, url TEXT, type TEXT, language TEXT,
  region TEXT, perspective TEXT, weight REAL, fetch_interval_minutes INTEGER,
  enabled INTEGER, health_json TEXT);
CREATE TABLE IF NOT EXISTS articles(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT, url TEXT, url_hash TEXT UNIQUE, title TEXT,
  content_text TEXT, lang TEXT, published_at TEXT, fetched_at TEXT,
  entities TEXT, topic TEXT);
CREATE INDEX IF NOT EXISTS idx_articles_pub ON articles(published_at);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT,
  severity REAL, first_seen TEXT, last_seen TEXT,
  article_count INTEGER, source_count INTEGER, score REAL, status TEXT);
CREATE TABLE IF NOT EXISTS event_articles(
  event_id INTEGER, article_id INTEGER,
  relation TEXT DEFAULT 'origin',
  PRIMARY KEY(event_id, article_id));
CREATE TABLE IF NOT EXISTS entities(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT, canonical_name TEXT UNIQUE, aliases TEXT);
CREATE TABLE IF NOT EXISTS event_entities(
  event_id INTEGER, entity_id INTEGER, role TEXT,
  PRIMARY KEY(event_id, entity_id));
CREATE TABLE IF NOT EXISTS briefs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, kind TEXT,
  title TEXT, body_md TEXT, published_at TEXT);
CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, trigger TEXT,
  status TEXT, created_at TEXT, checkpoint TEXT);
CREATE TABLE IF NOT EXISTS steps(
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, agent TEXT,
  input_digest TEXT, output_ref TEXT, error_card TEXT,
  started_at TEXT, ended_at TEXT);
"""


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def connect(db_path: Path | str) -> sqlite3.Connection:
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_source(conn: sqlite3.Connection, src) -> None:
    conn.execute(
        "INSERT INTO sources(id,name,url,type,language,region,perspective,weight,"
        "fetch_interval_minutes,enabled,health_json) VALUES(?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name,url=excluded.url,"
        "type=excluded.type,language=excluded.language,region=excluded.region,"
        "perspective=excluded.perspective,weight=excluded.weight,"
        "fetch_interval_minutes=excluded.fetch_interval_minutes,enabled=excluded.enabled",
        (src.id, src.name, src.url, src.type, src.language, src.region,
         src.perspective, src.weight, src.fetch_interval_minutes, int(src.enabled),
         json.dumps({"ok": True}, ensure_ascii=False)),
    )
    conn.commit()


def upsert_article(conn: sqlite3.Connection, a: Article) -> Optional[int]:
    """Idempotent insert by url_hash; returns row id or None when duplicate."""
    try:
        cur = conn.execute(
            "INSERT INTO articles(source_id,url,url_hash,title,content_text,lang,"
            "published_at,fetched_at,entities,topic) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (a.source_id, a.url, a.url_hash, a.title, a.content_text, a.lang,
             a.published_at, a.fetched_at, json.dumps(a.entities, ensure_ascii=False), a.topic),
        )
        conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return None


def articles_since(conn: sqlite3.Connection, hours: int) -> list[Article]:
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours + 24)).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT * FROM articles WHERE published_at >= ? ORDER BY published_at", (cutoff,)
    ).fetchall()
    out: list[Article] = []
    for r in rows:
        out.append(Article(
            id=r["id"], source_id=r["source_id"], url=r["url"], url_hash=r["url_hash"],
            title=r["title"], content_text=r["content_text"], lang=r["lang"],
            published_at=r["published_at"], fetched_at=r["fetched_at"],
            entities=json.loads(r["entities"] or "[]"), topic=r["topic"] or "",
        ))
    return out


def save_event(conn: sqlite3.Connection, ev) -> int:
    cur = conn.execute(
        "INSERT INTO events(title,category,severity,first_seen,last_seen,article_count,"
        "source_count,score,status) VALUES(?,?,?,?,?,?,?,?,?)",
        (ev.title, ev.category, ev.severity, ev.first_seen, ev.last_seen,
         len(ev.article_ids), len(set(ev.source_ids)), ev.score, "open"),
    )
    eid = int(cur.lastrowid)
    conn.executemany(
        "INSERT OR IGNORE INTO event_articles(event_id,article_id,relation) VALUES(?,?,?)",
        [(eid, aid, "origin") for aid in ev.article_ids],
    )
    conn.commit()
    return eid


def save_brief(conn: sqlite3.Connection, date: str, kind: str, title: str, body_md: str) -> int:
    cur = conn.execute(
        "INSERT INTO briefs(date,kind,title,body_md,published_at) VALUES(?,?,?,?,?)",
        (date, kind, title, body_md, _now()),
    )
    conn.commit()
    return int(cur.lastrowid)


def start_run(conn: sqlite3.Connection, kind: str, trigger: str) -> int:
    cur = conn.execute(
        "INSERT INTO runs(kind,trigger,status,created_at,checkpoint) VALUES(?,?,?,?,?)",
        (kind, trigger, "running", _now(), "{}"),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_run(conn: sqlite3.Connection, run_id: int, status: str, checkpoint: dict[str, Any]) -> None:
    conn.execute("UPDATE runs SET status=?, checkpoint=? WHERE id=?",
                 (status, json.dumps(checkpoint, ensure_ascii=False), run_id))
    conn.commit()


def record_step(conn: sqlite3.Connection, run_id: int, agent: str, input_digest: str,
                output_ref: str = "", error_card: str = "") -> None:
    conn.execute(
        "INSERT INTO steps(run_id,agent,input_digest,output_ref,error_card,started_at,ended_at)"
        " VALUES(?,?,?,?,?,?,?)",
        (run_id, agent, input_digest, output_ref, error_card, _now(), _now()),
    )
    conn.commit()


def stats(conn: sqlite3.Connection) -> dict[str, Any]:
    def count(table: str) -> int:
        return int(conn.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"])

    return {t: count(t) for t in ("sources", "articles", "events", "briefs", "runs")}
