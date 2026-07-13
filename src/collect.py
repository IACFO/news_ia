"""Coleta itens das fontes configuradas (RSS, arXiv, Hacker News)."""
import time
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import feedparser
import httpx
from dateutil import parser as dateparser

USER_AGENT = "GCB-RadarIA/1.0 (+news bot)"
TIMEOUT = 20.0


def _within_window(published: datetime | None, lookback_hours: int) -> bool:
    if published is None:
        return True  # sem data confiável: deixa passar, o dedup evita repetição
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return published >= cutoff


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = dateparser.parse(value) if isinstance(value, str) else datetime(*value[:6])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def collect_rss(feeds: list[dict], lookback_hours: int) -> list[dict]:
    items = []
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"], agent=USER_AGENT)
        except Exception as exc:  # noqa: BLE001
            print(f"[rss] falha em {feed['name']}: {exc}")
            continue
        for entry in parsed.entries[:15]:
            published = _parse_date(
                entry.get("published") or entry.get("updated") or entry.get("published_parsed")
            )
            if not _within_window(published, lookback_hours):
                continue
            summary = (entry.get("summary") or "")[:600]
            items.append(
                {
                    "title": entry.get("title", "(sem título)").strip(),
                    "url": entry.get("link", ""),
                    "summary": summary,
                    "source": feed["name"],
                    "tag": feed.get("tag", "rss"),
                    "published": published.isoformat() if published else None,
                }
            )
    print(f"[rss] coletados {len(items)} itens")
    return items


def collect_arxiv(cfg: dict, lookback_hours: int) -> list[dict]:
    cats = "+OR+".join(f"cat:{c}" for c in cfg.get("categories", ["cs.AI"]))
    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={cats}&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={cfg.get('max_results', 25)}"
    )
    items = []
    try:
        resp = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.text)
        for entry in root.findall("a:entry", ns):
            published = _parse_date(entry.findtext("a:published", default="", namespaces=ns))
            if not _within_window(published, lookback_hours):
                continue
            title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
            summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()[:600]
            link = ""
            for lk in entry.findall("a:link", ns):
                if lk.get("rel") == "alternate":
                    link = lk.get("href", "")
            items.append(
                {
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "source": "arXiv",
                    "tag": "paper",
                    "published": published.isoformat() if published else None,
                }
            )
    except Exception as exc:  # noqa: BLE001
        print(f"[arxiv] falha: {exc}")
    print(f"[arxiv] coletados {len(items)} itens")
    return items


def collect_hackernews(cfg: dict, lookback_hours: int) -> list[dict]:
    since = int((datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp())
    url = (
        "https://hn.algolia.com/api/v1/search_by_date"
        f"?query={httpx.QueryParams({'q': cfg.get('query', 'AI')})['q']}"
        f"&tags=story&numericFilters=points>{cfg.get('min_points', 80)},created_at_i>{since}"
        f"&hitsPerPage={cfg.get('max_results', 20)}"
    )
    items = []
    try:
        resp = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        for hit in resp.json().get("hits", []):
            link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            items.append(
                {
                    "title": hit.get("title", "(sem título)"),
                    "url": link,
                    "summary": f"{hit.get('points', 0)} pontos, {hit.get('num_comments', 0)} comentários no Hacker News.",
                    "source": "Hacker News",
                    "tag": "comunidade",
                    "published": _parse_date(hit.get("created_at")).isoformat()
                    if hit.get("created_at")
                    else None,
                }
            )
    except Exception as exc:  # noqa: BLE001
        print(f"[hn] falha: {exc}")
    print(f"[hn] coletados {len(items)} itens")
    return items


def collect_all(sources: dict, lookback_hours: int) -> list[dict]:
    items: list[dict] = []
    if sources.get("rss"):
        items += collect_rss(sources["rss"], lookback_hours)
    if sources.get("arxiv"):
        items += collect_arxiv(sources["arxiv"], lookback_hours)
    if sources.get("hackernews"):
        items += collect_hackernews(sources["hackernews"], lookback_hours)
    print(f"[collect] total bruto: {len(items)} itens")
    return items
