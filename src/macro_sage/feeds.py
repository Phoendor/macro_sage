from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
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


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    items: list[FeedItem]
    checked_at: datetime
    feed_url: str
    resolved_feed_url: str
    http_status: int | None
    feed_content_type: str | None
    feed_content_length: int
    redirect_chain: tuple[str, ...]
    parsed_entry_count: int
    filtered_entry_count: int
    invalid_date_count: int
    duplicate_count: int
    warnings: tuple[str, ...]


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    hostname = (parts.hostname or "").lower()
    port = parts.port
    if port and not (
        (parts.scheme.lower() == "https" and port == 443)
        or (parts.scheme.lower() == "http" and port == 80)
    ):
        hostname = f"{hostname}:{port}"
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in TRACKING_PARAMETERS
        )
    )
    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    return urlunsplit((parts.scheme.lower(), hostname, path, query, ""))


def _parsed_time(entry: feedparser.FeedParserDict, key: str) -> datetime | None:
    value = dict.get(entry, f"{key}_parsed")
    if not value:
        return None
    return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)


def _raw_time(entry: feedparser.FeedParserDict, key: str) -> str | None:
    value = dict.get(entry, key)
    return str(value).strip() if value else None


def _timestamps(
    entry: feedparser.FeedParserDict,
    source: SourceDefinition,
    *,
    checked_at: datetime,
    feed_last_modified: str | None,
) -> tuple[datetime | None, datetime | None, str | None, str | None, str | None]:
    published = _parsed_time(entry, "published")
    raw_published = _raw_time(entry, "published")
    updated = _parsed_time(entry, "updated")
    raw_updated = _raw_time(entry, "updated")
    warning: str | None = None
    if raw_published and published is None:
        warning = f"malformed published timestamp: {raw_published[:120]}"
    elif published is None and source.published_from_updated and updated is not None:
        published = updated
        warning = "publication time derived from updated time by source policy"
    elif (
        published is None
        and source.published_from_feed_last_modified
        and feed_last_modified
    ):
        try:
            published = parsedate_to_datetime(feed_last_modified).astimezone(timezone.utc)
            raw_published = feed_last_modified
            warning = "publication time derived from feed Last-Modified by source policy"
        except (TypeError, ValueError):
            warning = f"malformed feed Last-Modified: {feed_last_modified[:120]}"
    elif published is None:
        warning = "missing publication timestamp"
    if raw_updated and updated is None:
        extra = f"malformed updated timestamp: {raw_updated[:120]}"
        warning = f"{warning}; {extra}" if warning else extra
    if published and published > checked_at + timedelta(days=source.max_future_days):
        extra = f"implausible future publication timestamp: {published.isoformat()}"
        published = None
        warning = f"{warning}; {extra}" if warning else extra
    return published, updated, raw_published, raw_updated, warning


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


def _media_link(entry: feedparser.FeedParserDict) -> tuple[str | None, str | None]:
    for enclosure in entry.get("enclosures", []):
        media_type = str(enclosure.get("type", "")).lower()
        if media_type.startswith("audio/") and enclosure.get("href"):
            return str(enclosure["href"]), media_type
    return None, None


def _duration_seconds(entry: feedparser.FeedParserDict) -> int | None:
    raw = entry.get("itunes_duration")
    if raw is None:
        return None
    value = str(raw).strip()
    if value.isdigit():
        return int(value)
    parts = value.split(":")
    if not all(part.isdigit() for part in parts) or len(parts) not in {2, 3}:
        return None
    numbers = [int(part) for part in parts]
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def discover_with_diagnostics(
    source: SourceDefinition,
    client: HttpClient,
) -> DiscoveryResult:
    checked_at = datetime.now(timezone.utc)
    response = client.get(source.feed_url)
    parsed = feedparser.parse(response.content)
    if not parsed.entries:
        detail = str(getattr(parsed, "bozo_exception", "feed contains no entries"))
        raise FeedError(f"{source.id}: {detail}")

    items: list[FeedItem] = []
    filtered = 0
    invalid_dates = 0
    duplicates = 0
    warnings: list[str] = []
    seen_urls: set[str] = set()
    seen_guids: set[str] = set()
    feed_last_modified = getattr(response, "headers", {}).get("last-modified")
    for entry in parsed.entries:
        original_url = _article_link(entry)
        media_url, media_type = _media_link(entry)
        title = str(entry.get("title") or "Untitled").strip()
        if source.include_url_pattern and not re.search(
            source.include_url_pattern, original_url
        ):
            filtered += 1
            continue
        if source.exclude_title_pattern and re.search(
            source.exclude_title_pattern, title
        ):
            filtered += 1
            continue
        if source.kind is SourceKind.PODCAST and not media_url:
            filtered += 1
            continue
        if not original_url:
            filtered += 1
            continue
        url = canonicalize_url(original_url)
        guid = str(entry.get("id") or "").strip() or None
        if url in seen_urls or (guid is not None and guid in seen_guids):
            duplicates += 1
            continue
        seen_urls.add(url)
        if guid:
            seen_guids.add(guid)
        published, updated, raw_published, raw_updated, warning = _timestamps(
            entry,
            source,
            checked_at=checked_at,
            feed_last_modified=feed_last_modified,
        )
        if warning:
            warnings.append(f"{title}: {warning}")
        if published is None:
            invalid_dates += 1
        items.append(
            FeedItem(
                source=source,
                title=title,
                url=url,
                published_at=published,
                author=entry.get("author"),
                feed_text=_feed_text(entry),
                media_url=canonicalize_url(media_url) if media_url else None,
                media_type=media_type,
                duration_seconds=_duration_seconds(entry),
                updated_at=updated,
                raw_published=raw_published,
                raw_updated=raw_updated,
                guid=guid,
                publisher_id=str(entry.get("guid") or guid or "") or None,
                original_url=original_url,
                timestamp_warning=warning,
            )
        )

    items.sort(
        key=lambda item: item.published_at
        or item.updated_at
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    items = items[: source.scan_depth]
    history = tuple(
        str(getattr(value, "url", ""))
        for value in getattr(response, "history", ())
    )
    return DiscoveryResult(
        items=items,
        checked_at=checked_at,
        feed_url=source.feed_url,
        resolved_feed_url=str(getattr(response, "url", source.feed_url)),
        http_status=getattr(response, "status_code", None),
        feed_content_type=getattr(response, "headers", {}).get("content-type"),
        feed_content_length=len(response.content),
        redirect_chain=history,
        parsed_entry_count=len(parsed.entries),
        filtered_entry_count=filtered,
        invalid_date_count=invalid_dates,
        duplicate_count=duplicates,
        warnings=tuple(warnings),
    )


def discover(source: SourceDefinition, client: HttpClient) -> list[FeedItem]:
    return discover_with_diagnostics(source, client).items
