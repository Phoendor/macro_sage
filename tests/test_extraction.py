from datetime import datetime, timezone
from pathlib import Path

from macro_sage.extraction import _preferred_pdf_url, extract
from macro_sage.models import FeedItem, SourceDefinition


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
