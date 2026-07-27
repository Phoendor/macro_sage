from __future__ import annotations

from io import BytesIO
from urllib.parse import urljoin

import trafilatura
from bs4 import BeautifulSoup
from pypdf import PdfReader

from macro_sage.http import HttpClient
from macro_sage.models import Document, FeedItem


class ExtractionError(RuntimeError):
    pass


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(page for page in pages if page)


def _preferred_pdf_url(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[tuple[int, str]] = []
    for link in soup.select("a[href]"):
        href = str(link.get("href") or "")
        if ".pdf" not in href.lower():
            continue
        text = link.get_text(" ", strip=True).lower()
        score = sum(
            marker in text
            for marker in ("download", "report", "paper", "bulletin", "minutes")
        )
        candidates.append((score, urljoin(base_url, href)))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def extract(item: FeedItem, client: HttpClient, *, minimum_chars: int = 250) -> Document:
    response = client.get(item.url)
    content_type = response.headers.get("content-type", "").lower()
    is_pdf = "application/pdf" in content_type or item.url.lower().endswith(".pdf")
    if item.source.prefer_pdf and not is_pdf:
        pdf_url = _preferred_pdf_url(response.text, response.url)
        if not pdf_url:
            raise ExtractionError(f"{item.source.id}: preferred PDF link was not found")
        response = client.get(pdf_url)
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in content_type or pdf_url.lower().endswith(".pdf")
        if not is_pdf:
            raise ExtractionError(f"{item.source.id}: preferred link is not a PDF")
    if is_pdf:
        body = _pdf_text(response.content)
        media_type = "application/pdf"
    else:
        body = trafilatura.extract(
            response.text,
            url=response.url,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        ) or ""
        media_type = "text/html"

    body = body.strip()
    if len(body) < minimum_chars and len(item.feed_text) >= minimum_chars:
        body = item.feed_text.strip()
        media_type = "application/rss+xml"
    if len(body) < minimum_chars:
        raise ExtractionError(
            f"{item.source.id}: extracted only {len(body)} characters from {item.url}"
        )

    return Document(
        id=item.document_id,
        source_id=item.source.id,
        source_name=item.source.name,
        publisher=item.source.publisher,
        category=item.source.category,
        title=item.title,
        url=response.url,
        published_at=item.published_at,
        body=body,
        author=item.author,
        media_type=media_type,
    )
