from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from macro_sage.feeds import discover_with_diagnostics
from macro_sage.http import HttpClient
from macro_sage.models import (
    CollectionReport,
    SourceDefinition,
    SourceOutcome,
    SourceState,
)
from macro_sage.run_state import redact_text
from macro_sage.storage import DocumentStore


def check_source_health(
    sources: list[SourceDefinition],
    target: date,
    client: HttpClient,
    store: DocumentStore,
    *,
    timezone_name: str,
) -> CollectionReport:
    """Run discovery-only source checks without extraction or model requests."""
    report = CollectionReport()
    local_zone = ZoneInfo(timezone_name)
    for source in sources:
        try:
            discovery = discover_with_diagnostics(source, client)
            dated = [item for item in discovery.items if item.published_at is not None]
            latest = max(
                (item.published_at for item in dated if item.published_at),
                default=None,
            )
            if not dated:
                state = SourceState.INVALID_DATES
                detail = (
                    f"discovery returned {len(discovery.items)} item(s), but none had "
                    "a valid publication timestamp"
                )
            elif latest is not None and (
                target - latest.astimezone(local_zone).date()
            ).days > source.max_gap_days:
                age = (target - latest.astimezone(local_zone).date()).days
                state = SourceState.STALE
                detail = (
                    f"newest publication is {age} days old; configured normal gap is "
                    f"at most {source.max_gap_days} days"
                )
            elif discovery.invalid_date_count or discovery.warnings:
                state = SourceState.DEGRADED
                detail = (
                    f"feed discovery succeeded with {discovery.invalid_date_count} invalid "
                    f"date(s) and {len(discovery.warnings)} warning(s)"
                )
            else:
                state = SourceState.COLLECTED
                detail = (
                    f"feed discovery succeeded with {len(discovery.items)} usable item(s)"
                )
            outcome = SourceOutcome(
                source.id,
                source.name,
                source.kind,
                state,
                stage="feed discovery health check",
                detail=detail,
                checked_at=discovery.checked_at,
                latest_publication_at=latest,
            )
        except Exception as exc:
            outcome = SourceOutcome(
                source.id,
                source.name,
                source.kind,
                SourceState.FAILED,
                stage="feed discovery health check",
                detail=redact_text(str(exc)),
                checked_at=datetime.now(timezone.utc),
            )
        report.outcomes.append(outcome)
        store.record_source_health(outcome)
    report.health_snapshots = store.source_health_snapshots(
        sources,
        target=target,
        timezone_name=timezone_name,
    )
    return report
