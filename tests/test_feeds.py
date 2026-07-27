from pathlib import Path

from macro_sage.feeds import canonicalize_url, discover
from macro_sage.models import SourceDefinition


class Response:
    def __init__(self, content: bytes):
        self.content = content


class Client:
    def __init__(self, content: bytes):
        self.content = content

    def get(self, _url: str):
        return Response(self.content)


def test_discover_normalizes_feed_item():
    content = Path("tests/fixtures/feed.xml").read_bytes()
    source = SourceDefinition(
        id="example",
        name="Example",
        publisher="Example Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
    )

    [item] = discover(source, Client(content))

    assert item.title == "Rates and growth"
    assert item.url == "https://example.com/research/rates?keep=yes"
    assert item.published_at.isoformat() == "2026-07-27T08:30:00+00:00"
    assert item.author == "Research Team"


def test_canonicalize_url_removes_fragment_tracking_and_duplicate_slashes():
    value = canonicalize_url("HTTPS://EXAMPLE.COM//a///b?utm_medium=rss&x=1#section")

    assert value == "https://example.com/a/b?x=1"


def test_discover_filters_before_applying_item_limit():
    content = b"""\
<rss version="2.0"><channel><title>Example</title>
<item><title>Spreadsheet</title><link>https://example.com/data.xlsx</link></item>
<item><title>Sponsored Content</title><link>https://example.com/research/ad</link></item>
<item><title>Policy report</title><link>https://example.com/research/report</link></item>
</channel></rss>
"""
    source = SourceDefinition(
        id="filtered",
        name="Filtered",
        publisher="Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
        max_items=1,
        include_url_pattern="/research/",
        exclude_title_pattern="(?i)sponsored",
    )

    [item] = discover(source, Client(content))

    assert item.title == "Policy report"
