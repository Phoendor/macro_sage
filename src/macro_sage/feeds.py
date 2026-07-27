from __future__ import annotations

import calendar
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
from bs4 import BeautifulSoup

from macro_sage.http import HttpClient
from macro_sage.models import FeedItem, SourceDefinition, SourceKind

TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


class FeedError(RuntimeError):
    pass


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(
        [(key, value) for key, value in parse_qsl(parts.query) if key not in TRACKING_PARAMETERS]
    )
    path = re.sub(r"/{2,}", "/", parts.path)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def _published_at(entry: feedparser.FeedParserDict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)
    return None


def _feed_text(entry: feedparser.FeedParserDict) -> str:
    candidates = entry.get("content") or []
    raw = candidates[0].get("value", "") if candidates else entry.get("summary", "")
    if "<" not in raw:
        return unescape(raw).strip()
    return unescape(BeautifulSoup(raw, "html.parser").get_text(" ", strip=True))


def _article_link(entry: feedparser.FeedParserDict) -> str:
    for link in entry.get("links", []):
        if link.get("rel", "alternate") == "alternate" and link.get("href"):
            return str(link["href"])
    return str(entry.get("link") or entry.get("id") or "")


def _media_link(entry: feedparser.FeedParserDict) -> str | None:
    for enclosure in entry.get("enclosures", []):
        media_type = enclosure.get("type", "")
        if media_type.startswith("audio/") and enclosure.get("href"):
            return str(enclosure["href"])
    return None


def discover(source: SourceDefinition, client: HttpClient) -> list[FeedItem]:
    response = client.get(source.feed_url)
    parsed = feedparser.parse(response.content)
    if not parsed.entries:
        detail = str(getattr(parsed, "bozo_exception", "feed contains no entries"))
        raise FeedError(f"{source.id}: {detail}")

    items: list[FeedItem] = []
    for entry in parsed.entries:
        url = _article_link(entry)
        media_url = _media_link(entry)
        title = str(entry.get("title") or "Untitled")
        if source.include_url_pattern and not re.search(source.include_url_pattern, url):
            continue
        if source.exclude_title_pattern and re.search(
            source.exclude_title_pattern, title
        ):
            continue
        if source.kind is SourceKind.PODCAST and not media_url:
            continue
        if not url:
            continue
        items.append(
            FeedItem(
                source=source,
                title=title,
                url=canonicalize_url(url),
                published_at=_published_at(entry),
                author=entry.get("author"),
                feed_text=_feed_text(entry),
                media_url=media_url,
            )
        )
        if len(items) >= source.max_items:
            break
    return items
