from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from macro_sage.extraction import extract
from macro_sage.feeds import discover
from macro_sage.http import HttpClient
from macro_sage.models import (
    CollectionReport,
    SourceDefinition,
    SourceKind,
    SourceOutcome,
    SourceState,
)
from macro_sage.storage import DocumentStore


def is_on_date(value: datetime | None, target: date, timezone_name: str) -> bool:
    if value is None:
        return False
    return value.astimezone(ZoneInfo(timezone_name)).date() == target


def collect_articles(
    sources: list[SourceDefinition],
    target: date,
    client: HttpClient,
    store: DocumentStore,
    *,
    timezone_name: str,
) -> CollectionReport:
    report = CollectionReport()
    for source in sources:
        if source.kind is not SourceKind.ARTICLE:
            continue
        try:
            items = discover(source, client)
        except Exception as exc:
            report.outcomes.append(
                SourceOutcome(
                    source.id,
                    source.name,
                    source.kind,
                    SourceState.FAILED,
                    stage="feed discovery",
                    detail=str(exc),
                )
            )
            continue

        matching = [
            item for item in items if is_on_date(item.published_at, target, timezone_name)
        ]
        if not matching:
            report.outcomes.append(
                SourceOutcome(
                    source.id,
                    source.name,
                    source.kind,
                    SourceState.NO_ITEMS,
                    detail=f"no items on {target.isoformat()}",
                )
            )
            continue

        collected = 0
        failures: list[str] = []
        for item in matching:
            cached = store.get(item.document_id)
            if cached:
                report.documents.append(cached)
                collected += 1
                continue
            try:
                document = extract(item, client)
                store.save(document)
                report.documents.append(document)
                collected += 1
            except Exception as exc:
                failures.append(f"{item.title}: {exc}")
        state = (
            SourceState.PARTIAL
            if collected and failures
            else SourceState.FAILED
            if failures
            else SourceState.COLLECTED
        )
        report.outcomes.append(
            SourceOutcome(
                source.id,
                source.name,
                source.kind,
                state,
                document_count=collected,
                stage="article extraction" if failures else None,
                detail="; ".join(failures) if failures else None,
            )
        )
    return report
