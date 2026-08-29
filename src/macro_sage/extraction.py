from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from difflib import SequenceMatcher
from io import BytesIO
from urllib.parse import urljoin, urlsplit

import trafilatura
from bs4 import BeautifulSoup
from pypdf import PdfReader

from macro_sage.feeds import canonicalize_url
from macro_sage.http import HttpClient
from macro_sage.models import AcquisitionMode, Document, FeedItem
from macro_sage.versions import EXTRACTOR_VERSION


class ExtractionError(RuntimeError):
    pass


BLOCK_PAGE_MARKERS = (
    "access denied",
    "verify you are human",
    "enable javascript and cookies",
    "temporarily unavailable",
    "request unsuccessful",
    "subscription required",
    "sign in to continue",
    "login to continue",
)
ENGLISH_MARKERS = {
    "the",
    "and",
    "of",
    "to",
    "in",
    "that",
    "for",
    "is",
    "on",
    "with",
    "as",
    "by",
    "from",
    "at",
}


def _normalized_words(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _title_similarity(expected: str, actual: str) -> float:
    return SequenceMatcher(
        None, _normalized_words(expected), _normalized_words(actual)
    ).ratio()


def _deduplicate_paragraphs(body: str) -> tuple[str, bool]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", body)]
    seen: set[str] = set()
    output: list[str] = []
    repeated = False
    for paragraph in paragraphs:
        key = re.sub(r"\s+", " ", paragraph).strip().lower()
        if not key:
            continue
        if key in seen:
            repeated = True
            continue
        seen.add(key)
        output.append(paragraph)
    return "\n\n".join(output), repeated


def _looks_english(body: str) -> bool:
    words = re.findall(r"[a-z]+", body.lower())[:2_000]
    if len(words) < 50:
        return True
    return sum(word in ENGLISH_MARKERS for word in words) / len(words) >= 0.025


def _title_is_represented(title: str, body: str) -> bool:
    title_words = {
        word
        for word in _normalized_words(title).split()
        if len(word) >= 4 and word not in ENGLISH_MARKERS
    }
    if not title_words:
        return True
    body_words = set(_normalized_words(body[:3_000]).split())
    return len(title_words & body_words) / len(title_words) >= 0.25


def _boilerplate_extraction_is_suspicious(
    *, body_chars: int, visible_chars: int, title_represented: bool
) -> bool:
    if visible_chars < 5_000 or body_chars >= 500 or title_represented:
        return False
    return body_chars / visible_chars < 0.04


def _pdf_reading_order_is_suspicious(lines: list[str]) -> bool:
    if len(lines) < 50:
        return False
    fragmented = sum(len(line.split()) <= 2 for line in lines)
    return fragmented / len(lines) > 0.65


def _pdf_text(content: bytes) -> tuple[str, int]:
    reader = PdfReader(BytesIO(content))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    if len(pages) >= 3:
        line_counts = Counter(
            line.strip()
            for page in pages
            for line in page.splitlines()
            if 3 < len(line.strip()) < 160
        )
        repeated = {
            line for line, count in line_counts.items() if count >= len(pages) * 0.6
        }
        pages = [
            "\n".join(line for line in page.splitlines() if line.strip() not in repeated)
            for page in pages
        ]
    return "\n\n".join(page for page in pages if page), len(reader.pages)


def _preferred_pdf_url(
    html: str,
    base_url: str,
    pattern: str | None = None,
) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    matcher = re.compile(
        pattern or r"(?i)(download|full[- ]?report|paper|bulletin|minutes|report)"
    )
    candidates: list[tuple[int, str]] = []
    for link in soup.select("a[href]"):
        href = str(link.get("href") or "")
        if ".pdf" not in href.lower():
            continue
        label = f"{link.get_text(' ', strip=True)} {href}"
        match = matcher.search(label)
        if not match:
            continue
        candidates.append((len(match.group(0)), urljoin(base_url, href)))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def _canonical_html_url(html: str, response_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one("link[rel~=canonical][href]")
    if link:
        candidate = urljoin(response_url, str(link.get("href") or ""))
        if urlsplit(candidate).scheme in {"http", "https"}:
            return canonicalize_url(candidate)
    return canonicalize_url(response_url)


def _get(
    client: HttpClient,
    url: str,
    headers: dict[str, str] | None = None,
):
    return client.get(url, headers=headers) if headers else client.get(url)


def extract(
    item: FeedItem,
    client: HttpClient,
    *,
    minimum_chars: int = 250,
    cached: Document | None = None,
) -> Document:
    request_headers: dict[str, str] = {}
    validators_are_safe = bool(
        cached
        and cached.extractor_version == EXTRACTOR_VERSION
        and not cached.quality_flags
        and not (
            item.updated_at
            and cached.updated_at
            and item.updated_at > cached.updated_at
        )
    )
    if validators_are_safe and cached and cached.etag:
        request_headers["If-None-Match"] = cached.etag
    if validators_are_safe and cached and cached.last_modified:
        request_headers["If-Modified-Since"] = cached.last_modified
    response = _get(client, item.url, request_headers or None)
    fetched_at = datetime.now(timezone.utc)
    if getattr(response, "status_code", None) == 304 and cached:
        return replace(
            cached,
            fetched_at=fetched_at,
            discovery_source_ids=tuple(
                dict.fromkeys((*cached.discovery_source_ids, item.source.id))
            ),
        )

    landing_url = canonicalize_url(str(getattr(response, "url", item.url)))
    content_type = str(response.headers.get("content-type", "")).lower()
    is_pdf = "application/pdf" in content_type or landing_url.lower().endswith(".pdf")
    if item.source.acquisition_mode is AcquisitionMode.FULL_PDF and not is_pdf:
        pdf_url = _preferred_pdf_url(
            response.text,
            str(getattr(response, "url", item.url)),
            item.source.pdf_link_pattern,
        )
        if not pdf_url:
            raise ExtractionError(f"{item.source.id}: configured PDF link was not found")
        response = _get(client, pdf_url)
        content_type = str(response.headers.get("content-type", "")).lower()
        resolved = str(getattr(response, "url", pdf_url))
        is_pdf = "application/pdf" in content_type or resolved.lower().endswith(".pdf")
        if not is_pdf:
            raise ExtractionError(f"{item.source.id}: configured link is not a PDF")

    quality_flags: list[str] = []
    page_count: int | None = None
    if is_pdf:
        body, page_count = _pdf_text(response.content)
        if not page_count:
            raise ExtractionError(f"{item.source.id}: PDF has no pages")
        if len(body) / page_count < 80:
            raise ExtractionError(
                f"{item.source.id}: PDF text density is too low; it may be scanned"
            )
        if body.count("�") > max(5, len(body) // 10_000) or body.count("\x00") > 2:
            quality_flags.append("pdf_text_corruption")
        nonempty_lines = [line for line in body.splitlines() if line.strip()]
        if _pdf_reading_order_is_suspicious(nonempty_lines):
            quality_flags.append("pdf_reading_order_warning")
        if not _title_is_represented(item.title, body):
            quality_flags.append("title_mismatch")
        selected_url = str(getattr(response, "url", item.url)).lower()
        if re.search(r"(?:appendix|slides?|presentation)", selected_url) and not re.search(
            r"(?:appendix|slides?|presentation)", item.title.lower()
        ):
            raise ExtractionError(
                f"{item.source.id}: selected PDF appears to be an appendix or slides"
            )
        acquisition_method = AcquisitionMode.FULL_PDF
        media_type = "application/pdf"
        canonical_url = canonicalize_url(landing_url)
    else:
        html = response.text
        lowered = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).lower()
        if any(marker in lowered[:5_000] for marker in BLOCK_PAGE_MARKERS):
            raise ExtractionError(f"{item.source.id}: access-control or error page detected")
        soup = BeautifulSoup(html, "html.parser")
        page_title = (soup.title.get_text(" ", strip=True) if soup.title else "")
        if page_title and _title_similarity(item.title, page_title) < 0.2:
            quality_flags.append("title_mismatch")
        body = trafilatura.extract(
            html,
            url=str(getattr(response, "url", item.url)),
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        ) or ""
        body, repeated = _deduplicate_paragraphs(body)
        if repeated:
            quality_flags.append("repeated_paragraphs_removed")
        acquisition_method = AcquisitionMode.FULL_HTML
        media_type = "text/html"
        visible_chars = len(soup.get_text(" ", strip=True))
        title_represented = _title_is_represented(item.title, body) if body else False
        if _boilerplate_extraction_is_suspicious(
            body_chars=len(body),
            visible_chars=visible_chars,
            title_represented=title_represented,
        ):
            quality_flags.append("high_boilerplate_ratio")
        if body and not title_represented:
            quality_flags.append("low_title_relevance")
        canonical_url = _canonical_html_url(
            html, str(getattr(response, "url", item.url))
        )

    body = body.strip()
    if len(body) < minimum_chars and len(item.feed_text) >= minimum_chars:
        body = item.feed_text.strip()
        acquisition_method = AcquisitionMode.FEED_BODY
        media_type = "application/rss+xml"
        quality_flags.append("feed_body_fallback")
        canonical_url = canonicalize_url(item.url)
    if len(body) < minimum_chars:
        raise ExtractionError(
            f"{item.source.id}: extracted only {len(body)} characters from {item.url}"
        )
    if len(body.split()) < 50:
        quality_flags.append("low_text_density")
    if item.source.language == "en" and not _looks_english(body):
        quality_flags.append("language_mismatch")

    content_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    document_digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]
    revision_id = hashlib.sha256(
        f"{canonical_url}\0{content_sha256}\0{EXTRACTOR_VERSION}".encode()
    ).hexdigest()[:24]
    resolved_url = canonicalize_url(str(getattr(response, "url", item.url)))
    return Document(
        id=f"doc:{document_digest}",
        source_id=item.source.id,
        source_name=item.source.name,
        publisher=item.source.publisher,
        category=item.source.category,
        title=item.title,
        url=canonical_url,
        published_at=item.published_at,
        body=body,
        author=item.author,
        media_type=media_type,
        original_url=item.original_url or item.url,
        canonical_url=canonical_url,
        resolved_content_url=resolved_url,
        updated_at=item.updated_at,
        raw_published=item.raw_published,
        raw_updated=item.raw_updated,
        fetched_at=fetched_at,
        language=item.source.language,
        content_sha256=content_sha256,
        extractor_version=EXTRACTOR_VERSION,
        acquisition_method=acquisition_method,
        quality_flags=tuple(quality_flags),
        revision_id=revision_id,
        etag=response.headers.get("etag"),
        last_modified=response.headers.get("last-modified"),
        page_count=page_count,
        discovery_source_ids=(item.source.id,),
    )
