"""RSS 2.0 / Atom / RDF feed parsing + fetching (stdlib only)."""
from __future__ import annotations

import datetime as dt
import email.utils
import html as html_mod
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from typing import Callable

UA = "TeleScopeBot/0.2 (+https://github.com/zzy2011102/TeleScope; news monitoring research)"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _walk(node: ET.Element):
    for child in node:
        yield child
        yield from _walk(child)


def parse_feed(data: bytes) -> list[dict[str, str]]:
    """Unified extraction of item/entry records from RSS/Atom/RDF."""
    root = ET.fromstring(data)
    items: list[dict[str, str]] = []
    for node in _walk(root):
        if _local(node.tag) not in ("item", "entry"):
            continue
        rec: dict[str, str] = {}
        for f in node:
            t = _local(f.tag)
            if t == "link":
                href = f.get("href")
                rec.setdefault("link", (href or (f.text or "")).strip())
            elif t in ("description", "summary", "content", "encoded"):
                rec.setdefault("desc", (f.text or "").strip())
            elif t == "title":
                rec["title"] = (f.text or "").strip()
            elif t in ("pubdate", "date", "published", "updated"):
                rec.setdefault("date", (f.text or "").strip())
        if rec.get("link") and rec.get("title"):
            items.append(rec)
    return items


def parse_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        d = email.utils.parsedate_to_datetime(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            d = dt.datetime.strptime(s, fmt)
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return d.astimezone(dt.timezone.utc).isoformat(timespec="seconds")
        except ValueError:
            continue
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text)
    return html_mod.unescape(text).strip()


def fetch_url(url: str, timeout: int = 20, retries: int = 2,
              sleep: Callable[[float], None] = time.sleep) -> bytes:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": UA,
                         "Accept": "application/rss+xml, application/xml, text/xml, */*"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001 - collector must never crash pipeline
            last = e
            if attempt < retries:
                sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries + 1} attempts: {url} ({last})")
