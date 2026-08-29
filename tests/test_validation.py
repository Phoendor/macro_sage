from macro_sage.models import Participation, SourceDefinition, SourceKind
from macro_sage.validation import validate_source


class Response:
    def __init__(self, content, *, url, content_type, status=200):
        self.content = content
        self.text = content.decode() if isinstance(content, bytes) else content
        self.url = url
        self.status_code = status
        self.headers = {"content-type": content_type, "content-length": str(len(content))}
        self.history = []

    def close(self):
        return None


class ArticleClient:
    def get(self, url, **_kwargs):
        if url.endswith("feed.xml"):
            return Response(
                b"""<rss version="2.0"><channel><title>Feed</title><item>
                <title>Rates and growth</title><link>https://example.com/article</link>
                <pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate>
                </item></channel></rss>""",
                url=url,
                content_type="application/rss+xml",
            )
        body = "Rates and growth. " + "The economy and inflation are changing. " * 30
        return Response(
            f"<html><head><title>Rates and growth</title></head><body><article>{body}</article></body></html>".encode(),
            url=url,
            content_type="text/html",
        )


class PodcastClient(ArticleClient):
    def get(self, url, **_kwargs):
        return Response(
            b"""<rss version="2.0"><channel><title>Feed</title><item>
            <title>Episode</title><link>https://example.com/episode</link>
            <pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate>
            <enclosure url="https://example.com/audio.mp3" type="audio/mpeg"/>
            </item></channel></rss>""",
            url=url,
            content_type="application/rss+xml",
        )

    def probe(self, url):
        return Response(b"0", url=url, content_type="text/plain")


def test_article_validation_record_has_auditable_contract_fields():
    source = SourceDefinition(
        "source", "Source", "Publisher", "https://example.com/feed.xml", "research"
    )

    result = validate_source(source, ArticleClient())

    assert result["status"] == "passed"
    assert result["http_status"] == 200
    assert result["parsed_entry_count"] == 1
    assert result["newest_entry"]["published_at"]
    assert result["extraction_method"] == "full_html"
    assert result["content_sha256"]
    assert "body" not in result


def test_declared_audio_enclosure_survives_generic_probe_content_type():
    source = SourceDefinition(
        "podcast",
        "Podcast",
        "Publisher",
        "https://example.com/feed.xml",
        "podcast",
        kind=SourceKind.PODCAST,
        participation=Participation.OPTIONAL,
    )

    result = validate_source(source, PodcastClient())

    assert result["status"] == "passed"
    assert result["declared_media_type"] == "audio/mpeg"
    assert "feed declares audio/mpeg" in result["warnings"][0]
