from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from macro_sage.extraction import extract
from macro_sage.feeds import discover_with_diagnostics
from macro_sage.http import HttpClient
from macro_sage.models import (
    CollectionReport,
    ItemOutcome,
    ItemState,
    SourceDefinition,
    SourceKind,
    SourceOutcome,
    SourceState,
)
from macro_sage.run_state import redact_text
from macro_sage.scheduling import AcquisitionWindow
from macro_sage.storage import DocumentStore


def is_on_date(value: datetime | None, target: date, timezone_name: str) -> bool:
    if value is None:
        return False
    return value.astimezone(ZoneInfo(timezone_name)).date() == target


def _empty_state(
    source: SourceDefinition,
    target: date,
    dated_items: list,
    invalid_count: int,
    timezone_name: str,
) -> tuple[SourceState, str]:
    if not dated_items and invalid_count:
        return SourceState.INVALID_DATES, (
            f"{invalid_count} scanned entries lacked a valid publication timestamp"
        )
    if dated_items:
        newest = max(item.published_at for item in dated_items if item.published_at)
        newest_day = newest.astimezone(ZoneInfo(timezone_name)).date()
        age = (target - newest_day).days
        if age > source.max_gap_days:
            return SourceState.STALE, (
                f"newest publication is {newest_day.isoformat()} ({age} days old; "
                f"normal gap <= {source.max_gap_days})"
            )
    return SourceState.QUIET_EXPECTED, (
        f"no same-day publication was observed on {target.isoformat()}; "
        f"the source remains within its normal {source.max_gap_days}-day gap"
    )


def collect_articles(
    sources: list[SourceDefinition],
    target: date,
    client: HttpClient,
    store: DocumentStore,
    *,
    timezone_name: str,
    window: AcquisitionWindow | None = None,
) -> CollectionReport:
    report = CollectionReport()
    collected_ids: set[str] = set()
    for source in sources:
        if source.kind is not SourceKind.ARTICLE:
            continue
        try:
            discovery = discover_with_diagnostics(source, client)
        except Exception as exc:
            outcome = SourceOutcome(
                source.id,
                source.name,
                source.kind,
                SourceState.FAILED,
                stage="feed discovery",
                detail=redact_text(str(exc)),
                checked_at=datetime.now(timezone.utc),
            )
            report.outcomes.append(outcome)
            store.record_source_health(outcome)
            continue

        invalid_items = [item for item in discovery.items if item.published_at is None]
        for item in invalid_items:
            report.item_outcomes.append(
                ItemOutcome(
                    source.id,
                    item.title,
                    item.url,
                    ItemState.INVALID_DATE,
                    stage="publication dating",
                    detail=item.timestamp_warning or "missing publication timestamp",
                )
            )
        dated_items = [item for item in discovery.items if item.published_at is not None]
        latest_publication = max(
            (item.published_at for item in dated_items if item.published_at),
            default=None,
        )
        checked_at = getattr(discovery, "checked_at", datetime.now(timezone.utc))
        matching_all = [
            item
            for item in dated_items
            if (
                window.contains(item.published_at)
                if window
                else is_on_date(item.published_at, target, timezone_name)
            )
        ]
        matching = []
        filtered = []
        counts_by_day: dict[date, int] = {}
        for item in matching_all:
            publication_day = item.published_at.astimezone(
                ZoneInfo(timezone_name)
            ).date()
            count = counts_by_day.get(publication_day, 0)
            if count >= source.daily_limit:
                filtered.append(item)
                continue
            matching.append(item)
            counts_by_day[publication_day] = count + 1
        for item in filtered:
            report.item_outcomes.append(
                ItemOutcome(
                    source.id,
                    item.title,
                    item.url,
                    ItemState.FILTERED,
                    stage="per-publication-day inclusion limit",
                    detail=f"per-day limit is {source.daily_limit}",
                )
            )
        if not matching:
            state, detail = _empty_state(
                source,
                target,
                dated_items,
                len(invalid_items),
                timezone_name,
            )
            outcome = SourceOutcome(
                source.id,
                source.name,
                source.kind,
                state,
                stage="publication dating" if state is SourceState.INVALID_DATES else None,
                detail=detail,
                checked_at=checked_at,
                latest_publication_at=latest_publication,
            )
            report.outcomes.append(outcome)
            store.record_source_health(outcome)
            continue

        collected = 0
        failures: list[str] = []
        degraded: list[str] = []
        duplicates = 0
        for item in matching:
            cached = store.get_for_item(item)
            try:
                document = extract(item, client, cached=cached)
                saved = store.save(document, item=item)
                if saved.id in collected_ids:
                    duplicates += 1
                    report.item_outcomes.append(
                        ItemOutcome(
                            source.id,
                            item.title,
                            item.url,
                            ItemState.DUPLICATE,
                            stage="identity resolution",
                            detail="same canonical document or exact content already collected",
                            document_id=saved.id,
                        )
                    )
                    continue
                collected_ids.add(saved.id)
                report.documents.append(saved)
                is_cached = bool(cached and cached.revision_id == saved.revision_id)
                item_state = (
                    ItemState.DEGRADED
                    if saved.quality_flags
                    else ItemState.CACHED
                    if is_cached
                    else ItemState.COLLECTED
                )
                detail = ", ".join(saved.quality_flags) or None
                report.item_outcomes.append(
                    ItemOutcome(
                        source.id,
                        item.title,
                        item.url,
                        item_state,
                        stage="content quality" if saved.quality_flags else None,
                        detail=detail,
                        document_id=saved.id,
                    )
                )
                if saved.quality_flags:
                    degraded.append(f"{item.title}: {detail}")
                collected += 1
            except Exception as exc:
                safe_error = redact_text(str(exc))
                failures.append(f"{item.title}: {safe_error}")
                report.item_outcomes.append(
                    ItemOutcome(
                        source.id,
                        item.title,
                        item.url,
                        ItemState.FAILED,
                        stage="article extraction",
                        detail=safe_error,
                    )
                )
        details = [*failures, *degraded]
        if failures or degraded:
            state = SourceState.PARTIAL if collected else SourceState.FAILED
        elif duplicates and not collected:
            state = SourceState.DUPLICATE
        else:
            state = SourceState.COLLECTED
        outcome = SourceOutcome(
            source.id,
            source.name,
            source.kind,
            state,
            document_count=collected,
            stage="article extraction" if failures else "content quality" if degraded else None,
            detail="; ".join(details) if details else None,
            checked_at=checked_at,
            latest_publication_at=latest_publication,
        )
        report.outcomes.append(outcome)
        store.record_source_health(outcome)
    return report
