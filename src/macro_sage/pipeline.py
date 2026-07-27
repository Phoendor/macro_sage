from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from macro_sage.extraction import extract
from macro_sage.feeds import discover
from macro_sage.http import HttpClient
from macro_sage.models import CollectionReport, SourceDefinition, SourceKind
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
            report.errors.append(f"{source.name}: feed failed: {exc}")
            continue

        matching = [
            item for item in items if is_on_date(item.published_at, target, timezone_name)
        ]
        if not matching:
            report.skipped.append(f"{source.name}: no items on {target.isoformat()}")
            continue

        for item in matching:
            cached = store.get(item.document_id)
            if cached:
                report.documents.append(cached)
                continue
            try:
                document = extract(item, client)
                store.save(document)
                report.documents.append(document)
            except Exception as exc:
                report.errors.append(f"{source.name}: {item.title}: {exc}")
    return report
