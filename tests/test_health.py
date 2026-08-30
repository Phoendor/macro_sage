from datetime import date, datetime, timezone
from types import SimpleNamespace

from macro_sage.health import check_source_health
from macro_sage.models import SourceDefinition, SourceHealthStatus
from macro_sage.storage import DocumentStore


def source() -> SourceDefinition:
    return SourceDefinition(
        "source",
        "Source",
        "Publisher",
        "https://example.com/feed.xml",
        "research",
        event_driven=False,
        max_gap_days=4,
    )


def test_discovery_only_health_check_records_healthy_feed(monkeypatch):
    published = datetime(2026, 8, 29, 8, tzinfo=timezone.utc)
    discovery = SimpleNamespace(
        items=[SimpleNamespace(published_at=published)],
        checked_at=datetime(2026, 8, 30, 7, tzinfo=timezone.utc),
        invalid_date_count=0,
        warnings=(),
    )
    monkeypatch.setattr(
        "macro_sage.health.discover_with_diagnostics",
        lambda *_args: discovery,
    )

    with DocumentStore(":memory:") as store:
        report = check_source_health(
            [source()],
            date(2026, 8, 30),
            object(),
            store,
            timezone_name="UTC",
        )

    assert report.health_snapshots[0].status is SourceHealthStatus.HEALTHY
    assert report.health_snapshots[0].latest_publication_at == published


def test_first_discovery_failure_is_visible_warning_not_quarantine(monkeypatch):
    monkeypatch.setattr(
        "macro_sage.health.discover_with_diagnostics",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("HTTP 503")),
    )

    with DocumentStore(":memory:") as store:
        report = check_source_health(
            [source()],
            date(2026, 8, 30),
            object(),
            store,
            timezone_name="UTC",
        )

    assert report.health_snapshots[0].status is SourceHealthStatus.WARNING
    assert report.health_snapshots[0].consecutive_failures == 1
    assert "HTTP 503" in report.outcomes[0].detail
