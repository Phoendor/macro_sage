import json
from datetime import date, datetime, timezone

from macro_sage.models import (
    CollectionReport,
    Document,
    ItemOutcome,
    ItemState,
    SourceHealthSnapshot,
    SourceHealthStatus,
    SourceKind,
    SourceOutcome,
    SourceState,
)
from macro_sage.reporting import (
    health_report_to_dict,
    health_status_markdown,
    load_manifest,
    status_markdown,
    technical_report_markdown,
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


def test_health_report_separates_new_alerts_from_persistent_failures():
    checked = datetime(2026, 9, 2, 8, tzinfo=timezone.utc)
    snapshots = [
        SourceHealthSnapshot(
            "new",
            "New Failure",
            SourceHealthStatus.FAILING,
            checked,
            None,
            checked,
            None,
            None,
            3,
            3,
            "Newly reached the threshold.",
        ),
        SourceHealthSnapshot(
            "persistent",
            "Persistent Failure",
            SourceHealthStatus.FAILING,
            checked,
            None,
            checked,
            None,
            None,
            8,
            3,
            "Still failing.",
        ),
    ]
    report = CollectionReport(health_snapshots=snapshots)

    markdown = health_status_markdown(
        date(2026, 9, 2),
        report,
        alert_source_ids=("new",),
    )
    value = health_report_to_dict(
        date(2026, 9, 2),
        report,
        alert_source_ids=("new",),
    )

    assert "Newly failing; workflow alert required: **1**" in markdown
    assert "Persistently failing; retained without repeat alert: **1**" in markdown
    assert value["alert_source_ids"] == ["new"]


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


def test_technical_report_lists_collection_funnel_and_every_document():
    published = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    documents = [
        Document(
            id="doc:used",
            source_id="source-a",
            source_name="Source A",
            publisher="Publisher A",
            category="research",
            title="Used document",
            url="https://example.com/used",
            published_at=published,
            body="Body",
        ),
        Document(
            id="doc:excluded",
            source_id="source-a",
            source_name="Source A",
            publisher="Publisher A",
            category="research",
            title="Excluded document",
            url="https://example.com/excluded",
            published_at=published,
            body="Body",
        ),
    ]
    report = CollectionReport(
        documents=documents,
        outcomes=[
            SourceOutcome(
                "source-a",
                "Source A",
                SourceKind.ARTICLE,
                SourceState.COLLECTED,
                document_count=2,
            ),
            SourceOutcome(
                "stale",
                "Stale Source",
                SourceKind.ARTICLE,
                SourceState.STALE,
                detail="newest publication exceeds configured gap",
            ),
        ],
        item_outcomes=[
            ItemOutcome(
                "source-a",
                "Duplicate discovery",
                "https://example.com/duplicate",
                ItemState.DUPLICATE,
                detail="canonical document already collected",
                document_id="doc:used",
            )
        ],
    )
    decisions = [
        {
            "document_id": "doc:used",
            "outcome": "included",
            "reason_label": "included_full",
            "reason": "fit within bounded corpus",
        },
        {
            "document_id": "doc:excluded",
            "outcome": "omitted",
            "reason_label": "explicit_keyword_exclusion",
            "reason": "matched explicit exclusion",
        },
    ]

    output = technical_report_markdown(
        date(2026, 8, 31),
        report,
        corpus_decisions=decisions,
        cited_document_ids=["doc:used"],
        model="gpt-5.6-luna",
        input_tokens=100,
        output_tokens=50,
        planned_input_tokens=90,
        input_token_budget=250_000,
        input_token_count_method="openai_preflight",
    )

    assert "2 documents collected from 1 source" in output
    assert "[CITED]" in output
    assert "[EXPLICIT_KEYWORD_EXCLUSION]" in output
    assert "Excluded document" in output
    assert "Publication cadence attention" in output
    assert "Stale Source" in output
    assert "[DUPLICATE]" in output
    assert "Duplicate discovery" in output
    assert "Planned model input: `90` of `250000` tokens" in output
    assert "counting method: `openai_preflight`" in output
