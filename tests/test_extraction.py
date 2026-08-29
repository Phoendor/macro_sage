from datetime import datetime, timezone
from pathlib import Path

import pytest

from macro_sage.extraction import (
    ExtractionError,
    _boilerplate_extraction_is_suspicious,
    _pdf_reading_order_is_suspicious,
    _preferred_pdf_url,
    extract,
)
from macro_sage.models import AcquisitionMode, FeedItem, SourceDefinition


class Response:
    def __init__(self, text: str):
        self.text = text
        self.content = text.encode()
        self.url = "https://example.com/research/rates"
        self.headers = {"content-type": "text/html; charset=utf-8"}


class Client:
    def __init__(self, text: str):
        self.text = text

    def get(self, _url: str):
        return Response(self.text)


def test_extract_returns_main_article_text():
    html = Path("tests/fixtures/article.html").read_text(encoding="utf-8")
    source = SourceDefinition(
        id="example",
        name="Example",
        publisher="Example Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
    )
    item = FeedItem(
        source=source,
        title="Rates and growth",
        url="https://example.com/research/rates",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
    )

    document = extract(item, Client(html))

    assert "services inflation" in document.body
    assert "Cookie settings" not in document.body
    assert document.publisher == "Example Publisher"


def test_preferred_pdf_url_ranks_full_report_link():
    html = """\
<a href="/appendix.pdf">Appendix</a>
<a href="/full-report.pdf">Download the report</a>
"""

    value = _preferred_pdf_url(html, "https://example.com/publication")

    assert value == "https://example.com/full-report.pdf"


def test_access_control_page_is_rejected_even_when_http_succeeds():
    source = SourceDefinition(
        "example", "Example", "Publisher", "https://example.com/feed", "research"
    )
    item = FeedItem(
        source,
        "Research",
        "https://example.com/research",
        datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    html = "<html><body><h1>Access denied</h1>Verify you are human.</body></html>"

    with pytest.raises(ExtractionError, match="access-control"):
        extract(item, Client(html))


def test_feed_body_fallback_is_explicitly_degraded():
    source = SourceDefinition(
        "example", "Example", "Publisher", "https://example.com/feed", "research"
    )
    item = FeedItem(
        source,
        "Research",
        "https://example.com/research",
        datetime(2026, 7, 27, tzinfo=timezone.utc),
        feed_text="Feed summary with macro evidence. " * 20,
    )

    document = extract(item, Client("<html><body>Short.</body></html>"))

    assert document.acquisition_method is AcquisitionMode.FEED_BODY
    assert "feed_body_fallback" in document.quality_flags


def test_html_canonical_link_controls_source_independent_identity():
    source = SourceDefinition(
        "example", "Example", "Publisher", "https://example.com/feed", "research"
    )
    item = FeedItem(
        source,
        "Rates and growth",
        "https://example.com/tracking?utm_source=feed",
        datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    html = """\
<html><head><title>Rates and growth</title>
<link rel="canonical" href="https://example.com/research/rates"/></head>
<body><article><h1>Rates and growth</h1><p>{}</p></article></body></html>
""".format("Macro growth inflation policy and markets. " * 30)

    document = extract(item, Client(html))

    assert document.canonical_url == "https://example.com/research/rates"
    assert document.id.startswith("doc:")
    assert not document.id.startswith("example:")


def test_short_complete_official_page_is_not_degraded_for_site_navigation():
    assert not _boilerplate_extraction_is_suspicious(
        body_chars=550,
        visible_chars=10_000,
        title_represented=True,
    )
    assert _boilerplate_extraction_is_suspicious(
        body_chars=300,
        visible_chars=10_000,
        title_represented=False,
    )


def test_pdf_tables_do_not_look_like_broken_reading_order_until_dominant():
    report_lines = ["one"] * 60 + ["normal report sentence with evidence"] * 40
    broken_lines = ["one"] * 80 + ["normal report sentence with evidence"] * 20

    assert not _pdf_reading_order_is_suspicious(report_lines)
    assert _pdf_reading_order_is_suspicious(broken_lines)
