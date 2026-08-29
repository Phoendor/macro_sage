from pathlib import Path

from macro_sage.feeds import canonicalize_url, discover, discover_with_diagnostics
from macro_sage.models import SourceDefinition, SourceKind


class Response:
    def __init__(self, content: bytes):
        self.content = content
        self.headers = {"content-type": "application/rss+xml"}
        self.url = "https://example.com/feed.xml"
        self.history = []
        self.status_code = 200


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
<item><title>Policy report</title><link>https://example.com/research/report</link>
<pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate></item>
</channel></rss>
"""
    source = SourceDefinition(
        id="filtered",
        name="Filtered",
        publisher="Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
        scan_depth=1,
        daily_limit=1,
        include_url_pattern="/research/",
        exclude_title_pattern="(?i)sponsored",
    )

    [item] = discover(source, Client(content))

    assert item.title == "Policy report"


def test_discover_parses_podcast_duration():
    content = b"""\
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel><title>Podcast</title>
<item><title>Episode</title><link>https://example.com/episode</link>
<pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate>
<itunes:duration>01:02:03</itunes:duration>
<enclosure url="https://example.com/audio.mp3" type="audio/mpeg"/>
</item>
</channel></rss>
"""
    source = SourceDefinition(
        id="podcast",
        name="Podcast",
        publisher="Publisher",
        feed_url="https://example.com/feed.xml",
        category="podcast",
        kind=SourceKind.PODCAST,
    )

    [item] = discover(source, Client(content))

    assert item.duration_seconds == 3723


def test_updated_timestamp_is_not_silently_used_as_publication_time():
    content = b"""\
<rss version="2.0"><channel><title>Example</title><item><title>Revised</title>
<link>https://example.com/revised</link>
<updated>Mon, 27 Jul 2026 08:00:00 GMT</updated></item></channel></rss>
"""
    source = SourceDefinition(
        id="example",
        name="Example",
        publisher="Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
    )

    result = discover_with_diagnostics(source, Client(content))

    assert result.items[0].published_at is None
    assert result.items[0].updated_at is not None
    assert result.items[0].timestamp_warning == "missing publication timestamp"


def test_entries_are_sorted_before_scan_depth_is_applied():
    content = b"""\
<rss version="2.0"><channel><title>Example</title>
<item><title>Old</title><link>https://example.com/old</link>
<pubDate>Sun, 26 Jul 2026 08:00:00 GMT</pubDate></item>
<item><title>New</title><link>https://example.com/new</link>
<pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate></item>
</channel></rss>
"""
    source = SourceDefinition(
        id="example",
        name="Example",
        publisher="Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
        scan_depth=1,
        daily_limit=1,
    )

    [item] = discover(source, Client(content))

    assert item.title == "New"


def test_source_policy_can_explicitly_treat_updated_as_publication_time():
    content = b"""\
<feed xmlns="http://www.w3.org/2005/Atom"><title>Example</title>
<entry><title>Policy note</title><id>tag:example,2026:1</id>
<link href="https://example.com/note"/><updated>2026-07-27T08:00:00Z</updated>
</entry></feed>
"""
    source = SourceDefinition(
        id="example",
        name="Example",
        publisher="Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
        published_from_updated=True,
    )

    [item] = discover(source, Client(content))

    assert item.published_at.isoformat() == "2026-07-27T08:00:00+00:00"
    assert item.updated_at == item.published_at
    assert "by source policy" in item.timestamp_warning


def test_implausible_future_timestamp_is_not_eligible_for_collection():
    content = b"""\
<rss version="2.0"><channel><title>Example</title><item><title>Future</title>
<link>https://example.com/future</link>
<pubDate>Mon, 27 Jul 2999 08:00:00 GMT</pubDate></item></channel></rss>
"""
    source = SourceDefinition(
        id="example",
        name="Example",
        publisher="Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
    )

    [item] = discover(source, Client(content))

    assert item.published_at is None
    assert "future publication" in item.timestamp_warning


def test_duplicate_tracking_urls_are_reported_once():
    content = b"""\
<rss version="2.0"><channel><title>Example</title>
<item><title>One</title><link>https://example.com/item?utm_source=a</link>
<pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate></item>
<item><title>One again</title><link>https://example.com/item?utm_source=b</link>
<pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate></item>
</channel></rss>
"""
    source = SourceDefinition(
        id="example",
        name="Example",
        publisher="Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
    )

    result = discover_with_diagnostics(source, Client(content))

    assert len(result.items) == 1
    assert result.duplicate_count == 1
