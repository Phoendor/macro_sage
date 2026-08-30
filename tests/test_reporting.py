import json
from datetime import date, datetime, timezone

from macro_sage.models import (
    CollectionReport,
    Document,
    SourceHealthSnapshot,
    SourceHealthStatus,
    SourceKind,
    SourceOutcome,
    SourceState,
)
from macro_sage.reporting import (
    load_manifest,
    status_markdown,
    write_audit_manifest,
    write_manifest,
)


def test_manifest_round_trip_preserves_explicit_source_failures(tmp_path):
    report = CollectionReport(
        documents=[
            Document(
                id="source:item",
                source_id="source",
                source_name="Source",
                publisher="Publisher",
                category="research",
                title="Item",
                url="https://example.com/item",
                published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
                body="Body",
            )
        ],
        outcomes=[
            SourceOutcome(
                "broken",
                "Broken Source",
                SourceKind.ARTICLE,
                SourceState.FAILED,
                stage="feed discovery",
                detail="HTTP 403",
                checked_at=datetime(2026, 7, 27, 8, tzinfo=timezone.utc),
                latest_publication_at=datetime(2026, 7, 26, 8, tzinfo=timezone.utc),
            )
        ],
        health_snapshots=[
            SourceHealthSnapshot(
                "broken",
                "Broken Source",
                SourceHealthStatus.WARNING,
                datetime(2026, 7, 27, 8, tzinfo=timezone.utc),
                None,
                datetime(2026, 7, 27, 8, tzinfo=timezone.utc),
                datetime(2026, 7, 26, 8, tzinfo=timezone.utc),
                None,
                1,
                3,
                "One adverse observation.",
            )
        ],
    )
    path = tmp_path / "documents.json"

    write_manifest(path, date(2026, 7, 27), report)
    target, loaded = load_manifest(path)

    assert target == date(2026, 7, 27)
    assert loaded.documents == report.documents
    assert loaded.failures[0].source_id == "broken"
    assert loaded.failures[0].checked_at == report.outcomes[0].checked_at
    assert loaded.health_snapshots == report.health_snapshots
    assert "HTTP 403" in status_markdown(target, loaded)


def test_audit_manifest_excludes_source_bodies(tmp_path):
    marker = "PRIVATE ARTICLE BODY MUST NOT BE UPLOADED"
    report = CollectionReport(
        documents=[
            Document(
                id="source:item",
                source_id="source",
                source_name="Source",
                publisher="Publisher",
                category="research",
                title="Item",
                url="https://example.com/item",
                published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
                body=marker,
            )
        ]
    )
    path = tmp_path / "manifest.json"

    write_audit_manifest(path, date(2026, 7, 27), report)

    text = path.read_text(encoding="utf-8")
    value = json.loads(text)
    assert marker not in text
    assert '"body"' not in text
    assert value["documents"][0]["body_chars"] == len(marker)
    assert '"content_sha256"' in text
