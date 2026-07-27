from __future__ import annotations

from io import BytesIO

import trafilatura
from pypdf import PdfReader

from macro_sage.http import HttpClient
from macro_sage.models import Document, FeedItem


class ExtractionError(RuntimeError):
    pass


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(page for page in pages if page)


def extract(item: FeedItem, client: HttpClient, *, minimum_chars: int = 250) -> Document:
    response = client.get(item.url)
    content_type = response.headers.get("content-type", "").lower()
    is_pdf = "application/pdf" in content_type or item.url.lower().endswith(".pdf")
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
