from datetime import date, datetime, timezone

from macro_sage.models import (
    Document,
    FeedItem,
    ItemState,
    SourceDefinition,
    SourceKind,
    SourceState,
)
from macro_sage.pipeline import collect_articles
from macro_sage.podcasts import (
    SEGMENT_SECONDS,
    PodcastTranscriber,
    PodcastTranscript,
    collect_podcasts,
)


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


def test_article_failure_redacts_environment_secret(monkeypatch):
    monkeypatch.setenv("PUBLISHER_API_TOKEN", "publisher-secret-value")

    def fail_discovery(_source, _client):
        raise RuntimeError("rejected publisher-secret-value")

    monkeypatch.setattr("macro_sage.pipeline.discover", fail_discovery)

    report = collect_articles(
        [source()],
        date(2026, 7, 27),
        object(),
        Store(),
        timezone_name="UTC",
    )

    assert "publisher-secret-value" not in report.failures[0].detail
    assert "[REDACTED]" in report.failures[0].detail


def test_article_item_failure_remains_individually_auditable(monkeypatch):
    article_source = source()
    item = FeedItem(
        source=article_source,
        title="Broken article",
        url="https://example.com/broken",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    monkeypatch.setattr("macro_sage.pipeline.discover", lambda *_args: [item])
    monkeypatch.setattr(
        "macro_sage.pipeline.extract",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("paywall")),
    )

    report = collect_articles(
        [article_source],
        date(2026, 7, 27),
        object(),
        Store(),
        timezone_name="UTC",
    )

    assert report.item_outcomes[0].title == "Broken article"
    assert report.item_outcomes[0].state is ItemState.FAILED
    assert report.item_outcomes[0].stage == "article extraction"
    assert report.item_outcomes[0].detail == "paywall"


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


def test_failed_transcription_consumes_episode_attempt_limit(monkeypatch):
    podcast_source = source(SourceKind.PODCAST)
    items = [
        FeedItem(
            source=podcast_source,
            title=f"Episode {number}",
            url=f"https://example.com/episode-{number}",
            published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
            media_url=f"https://example.com/audio-{number}.mp3",
        )
        for number in (1, 2)
    ]
    monkeypatch.setattr(
        "macro_sage.podcasts.discover",
        lambda _source, _client: items,
    )

    class Transcriber:
        def __init__(self):
            self.calls = 0

        def transcribe(self, _url, *, max_seconds):
            self.calls += 1
            raise RuntimeError(f"rejected with {max_seconds=}")

    transcriber = Transcriber()
    report = collect_podcasts(
        [podcast_source],
        date(2026, 7, 27),
        object(),
        Store(),
        transcriber,
        timezone_name="UTC",
        max_episodes=1,
        max_minutes=60,
    )

    assert transcriber.calls == 1
    assert report.outcomes[0].state is SourceState.FAILED
    assert "daily episode limit reached" in report.outcomes[0].detail


def test_long_compressed_audio_is_segmented_by_duration(monkeypatch, tmp_path):
    audio_path = tmp_path / "episode.mp3"
    audio_path.write_bytes(b"small compressed audio")
    command = None

    def fake_run(arguments, **_kwargs):
        nonlocal command
        command = arguments
        (tmp_path / "segment-000.mp3").write_bytes(b"segment")

    monkeypatch.setattr("macro_sage.podcasts.shutil.which", lambda _name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("macro_sage.podcasts.subprocess.run", fake_run)

    segments = PodcastTranscriber._segments(
        object(),
        audio_path,
        tmp_path,
        SEGMENT_SECONDS + 1,
    )

    assert segments == [tmp_path / "segment-000.mp3"]
    assert command[command.index("-segment_time") + 1] == str(SEGMENT_SECONDS)
