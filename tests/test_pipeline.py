from datetime import date, datetime, timezone

from macro_sage.models import (
    Document,
    FeedItem,
    SourceDefinition,
    SourceKind,
    SourceState,
)
from macro_sage.pipeline import collect_articles
from macro_sage.podcasts import PodcastTranscript, collect_podcasts


class Store:
    def __init__(self):
        self.documents = {}

    def get(self, identifier):
        return self.documents.get(identifier)

    def save(self, document):
        self.documents[document.id] = document


def source(kind=SourceKind.ARTICLE):
    return SourceDefinition(
        id="source",
        name="Source",
        publisher="Publisher",
        feed_url="https://example.com/feed.xml",
        category="research",
        kind=kind,
    )


def test_article_feed_failure_is_structured_and_explicit(monkeypatch):
    def fail_discovery(_source, _client):
        raise RuntimeError("HTTP 403")

    monkeypatch.setattr("macro_sage.pipeline.discover", fail_discovery)

    report = collect_articles(
        [source()],
        date(2026, 7, 27),
        object(),
        Store(),
        timezone_name="UTC",
    )

    assert report.failures[0].source_id == "source"
    assert report.failures[0].state is SourceState.FAILED
    assert "HTTP 403" in report.failures[0].summary()


def test_podcast_duration_budget_skips_before_paid_transcription(monkeypatch):
    podcast_source = source(SourceKind.PODCAST)
    item = FeedItem(
        source=podcast_source,
        title="Long episode",
        url="https://example.com/episode",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        media_url="https://example.com/audio.mp3",
        duration_seconds=90 * 60,
    )
    monkeypatch.setattr(
        "macro_sage.podcasts.discover",
        lambda _source, _client: [item],
    )

    class Transcriber:
        def transcribe(self, _url, *, max_seconds):
            raise AssertionError(f"should not transcribe with {max_seconds=}")

    report = collect_podcasts(
        [podcast_source],
        date(2026, 7, 27),
        object(),
        Store(),
        Transcriber(),
        timezone_name="UTC",
        max_episodes=1,
        max_minutes=60,
    )

    assert report.outcomes[0].state is SourceState.SKIPPED
    assert "duration exceeds" in report.outcomes[0].detail


def test_cached_podcast_does_not_consume_new_audio_budget(monkeypatch):
    podcast_source = source(SourceKind.PODCAST)
    item = FeedItem(
        source=podcast_source,
        title="Cached episode",
        url="https://example.com/episode",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        media_url="https://example.com/audio.mp3",
    )
    cached = Document(
        id=item.document_id,
        source_id=podcast_source.id,
        source_name=podcast_source.name,
        publisher=podcast_source.publisher,
        category=podcast_source.category,
        title=item.title,
        url=item.url,
        published_at=item.published_at,
        body="Transcript",
        media_type="audio/transcript",
    )
    store = Store()
    store.save(cached)
    monkeypatch.setattr(
        "macro_sage.podcasts.discover",
        lambda _source, _client: [item],
    )

    class Transcriber:
        def transcribe(self, _url, *, max_seconds):
            return PodcastTranscript("New", max_seconds)

    report = collect_podcasts(
        [podcast_source],
        date(2026, 7, 27),
        object(),
        store,
        Transcriber(),
        timezone_name="UTC",
        max_episodes=1,
        max_minutes=1,
    )

    assert report.documents == [cached]
    assert report.outcomes[0].state is SourceState.COLLECTED
