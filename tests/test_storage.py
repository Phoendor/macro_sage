import hashlib
import sqlite3
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from macro_sage.models import (
    Document,
    FeedItem,
    SourceDefinition,
    SourceHealthStatus,
    SourceKind,
    SourceOutcome,
    SourceState,
)
from macro_sage.storage import DocumentStore
from macro_sage.versions import DATABASE_SCHEMA_VERSION, EXTRACTOR_VERSION


def document(body="Body", revision="revision-1"):
    return Document(
        id="doc:abc",
        source_id="source",
        source_name="Source",
        publisher="Publisher",
        category="research",
        title="Title",
        url="https://example.com/title",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        body=body,
        canonical_url="https://example.com/title",
        content_sha256=hashlib.sha256(body.encode()).hexdigest(),
        extractor_version=EXTRACTOR_VERSION,
        revision_id=revision,
    )


def test_document_round_trip_records_provenance_defaults():
    value = document()

    with DocumentStore(":memory:") as store:
        saved = store.save(value)
        loaded = store.get(saved.id)

    assert loaded.body == value.body
    assert loaded.canonical_url == value.canonical_url
    assert loaded.content_sha256 == value.content_sha256
    assert loaded.revision_id == value.revision_id
    assert loaded.fetched_at is not None


def test_changed_content_creates_a_revision_instead_of_overwriting():
    first = document()
    second = replace(
        first,
        body="Corrected body",
        content_sha256=hashlib.sha256(b"Corrected body").hexdigest(),
        revision_id="revision-2",
    )

    with DocumentStore(":memory:") as store:
        store.save(first)
        store.save(second)

        assert store.revision_count(first.id) == 2
        assert store.get(first.id).body == "Corrected body"


def test_discovery_origins_are_many_to_many():
    first_source = SourceDefinition(
        "one", "One", "Publisher", "https://example.com/one.xml", "research"
    )
    second_source = replace(first_source, id="two", name="Two")
    first_item = FeedItem(
        first_source,
        "Title",
        "https://example.com/title",
        datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    second_item = replace(first_item, source=second_source)

    with DocumentStore(":memory:") as store:
        store.save(document(), item=first_item)
        store.save(document(), item=second_item)
        loaded = store.get("doc:abc")

    assert set(loaded.discovery_source_ids) == {"one", "two"}


def test_similar_titles_are_proposed_for_review_not_merged():
    first = replace(
        document(body="First body"),
        title="Quarterly monetary policy report June 2026",
    )
    second = replace(
        document(body="Second body", revision="revision-2"),
        id="doc:def",
        title="Quarterly Monetary Policy Report — June 2026",
        url="https://example.com/second",
        canonical_url="https://example.com/second",
    )

    with DocumentStore(":memory:") as store:
        first_saved = store.save(first)
        second_saved = store.save(second)
        candidates = store.duplicate_candidates()

    assert first_saved.id != second_saved.id
    assert len(candidates) == 1


def test_legacy_database_is_migrated_without_losing_the_document(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE documents (
            id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_name TEXT NOT NULL,
            publisher TEXT NOT NULL, category TEXT NOT NULL, title TEXT NOT NULL,
            url TEXT NOT NULL, published_at TEXT, body TEXT NOT NULL, author TEXT,
            media_type TEXT NOT NULL, fetched_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "legacy:id",
            "source",
            "Source",
            "Publisher",
            "research",
            "Title",
            "https://example.com/title",
            "2026-07-27T00:00:00+00:00",
            "Legacy body",
            None,
            "text/html",
            "2026-07-27T01:00:00+00:00",
        ),
    )
    connection.commit()
    connection.close()

    with DocumentStore(path) as store:
        assert store.schema_version == DATABASE_SCHEMA_VERSION
        assert store.get("legacy:id").body == "Legacy body"


def test_source_health_snapshot_tracks_consecutive_failures_and_publication():
    source = SourceDefinition(
        "source",
        "Source",
        "Publisher",
        "https://example.com/feed.xml",
        "research",
        event_driven=False,
        max_gap_days=4,
        failure_threshold=3,
    )
    checked = datetime(2026, 8, 24, 8, tzinfo=timezone.utc)
    publication = datetime(2026, 8, 24, 7, tzinfo=timezone.utc)

    with DocumentStore(":memory:") as store:
        store.record_source_health(
            SourceOutcome(
                source.id,
                source.name,
                SourceKind.ARTICLE,
                SourceState.COLLECTED,
                checked_at=checked,
                latest_publication_at=publication,
            )
        )
        for offset in range(1, 4):
            store.record_source_health(
                SourceOutcome(
                    source.id,
                    source.name,
                    SourceKind.ARTICLE,
                    SourceState.FAILED,
                    checked_at=checked + timedelta(days=offset),
                )
            )
        snapshot = store.source_health_snapshots(
            [source],
            target=date(2026, 8, 27),
            timezone_name="UTC",
        )[0]

    assert snapshot.status is SourceHealthStatus.FAILING
    assert snapshot.consecutive_failures == 3
    assert snapshot.last_success_at == checked
    assert snapshot.latest_publication_at == publication
    assert snapshot.expected_next_publication == date(2026, 8, 28)


def test_schema_two_health_events_migrate_in_place(tmp_path):
    path = tmp_path / "schema-two.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO schema_metadata VALUES ('version', '2');
        CREATE TABLE source_health_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            state TEXT NOT NULL,
            stage TEXT,
            detail TEXT,
            document_count INTEGER NOT NULL
        );
        INSERT INTO source_health_events (
            source_id, checked_at, state, stage, detail, document_count
        ) VALUES ('source', '2026-08-29T08:00:00+00:00', 'collected', NULL, NULL, 1);
        """
    )
    connection.commit()
    connection.close()

    with DocumentStore(path) as store:
        columns = store._table_columns("source_health_events")
        row = store.connection.execute(
            "SELECT state, latest_publication_at FROM source_health_events"
        ).fetchone()

    assert "latest_publication_at" in columns
    assert row["state"] == "collected"
    assert row["latest_publication_at"] is None
