from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from macro_sage.files import write_json_atomic
from macro_sage.models import (
    AcquisitionMode,
    CollectionReport,
    ContentResult,
    Document,
    ItemOutcome,
    ItemState,
    RunHealth,
    SourceDefinition,
    SourceHealthSnapshot,
    SourceHealthStatus,
    SourceKind,
    SourceOutcome,
    SourceState,
)
from macro_sage.run_state import assess_coverage


def document_to_dict(document: Document) -> dict[str, object]:
    value = asdict(document)
    for field_name in ("published_at", "updated_at", "fetched_at"):
        field_value = getattr(document, field_name)
        value[field_name] = field_value.isoformat() if field_value else None
    return value


def document_audit_to_dict(document: Document) -> dict[str, object]:
    value = document_to_dict(document)
    body = str(value.pop("body"))
    value["body_chars"] = len(body)
    value["content_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return value


def document_from_dict(value: dict[str, object]) -> Document:
    published = value.get("published_at")
    return Document(
        id=str(value["id"]),
        source_id=str(value["source_id"]),
        source_name=str(value["source_name"]),
        publisher=str(value["publisher"]),
        category=str(value["category"]),
        title=str(value["title"]),
        url=str(value["url"]),
        published_at=datetime.fromisoformat(str(published)) if published else None,
        body=str(value["body"]),
        author=str(value["author"]) if value.get("author") is not None else None,
        media_type=str(value.get("media_type", "text/html")),
        original_url=(
            str(value["original_url"]) if value.get("original_url") else None
        ),
        canonical_url=(
            str(value["canonical_url"]) if value.get("canonical_url") else None
        ),
        resolved_content_url=(
            str(value["resolved_content_url"])
            if value.get("resolved_content_url")
            else None
        ),
        updated_at=(
            datetime.fromisoformat(str(value["updated_at"]))
            if value.get("updated_at")
            else None
        ),
        raw_published=(
            str(value["raw_published"]) if value.get("raw_published") else None
        ),
        raw_updated=(
            str(value["raw_updated"]) if value.get("raw_updated") else None
        ),
        fetched_at=(
            datetime.fromisoformat(str(value["fetched_at"]))
            if value.get("fetched_at")
            else None
        ),
        language=str(value.get("language", "en")),
        content_sha256=str(value.get("content_sha256", "")),
        extractor_version=str(value.get("extractor_version", "")),
        acquisition_method=AcquisitionMode(
            str(value.get("acquisition_method", AcquisitionMode.FULL_HTML))
        ),
        quality_flags=tuple(str(item) for item in value.get("quality_flags", [])),
        revision_id=str(value.get("revision_id", "")),
        etag=str(value["etag"]) if value.get("etag") else None,
        last_modified=(
            str(value["last_modified"]) if value.get("last_modified") else None
        ),
        page_count=(int(value["page_count"]) if value.get("page_count") else None),
        discovery_source_ids=tuple(
            str(item) for item in value.get("discovery_source_ids", [])
        ),
    )


def outcome_to_dict(outcome: SourceOutcome) -> dict[str, object]:
    value = asdict(outcome)
    value["checked_at"] = outcome.checked_at.isoformat() if outcome.checked_at else None
    value["latest_publication_at"] = (
        outcome.latest_publication_at.isoformat()
        if outcome.latest_publication_at
        else None
    )
    return value


def outcome_from_dict(value: dict[str, object]) -> SourceOutcome:
    return SourceOutcome(
        source_id=str(value["source_id"]),
        source_name=str(value["source_name"]),
        kind=SourceKind(str(value["kind"])),
        state=SourceState(str(value["state"])),
        document_count=int(value.get("document_count", 0)),
        stage=str(value["stage"]) if value.get("stage") else None,
        detail=str(value["detail"]) if value.get("detail") else None,
        checked_at=(
            datetime.fromisoformat(str(value["checked_at"]))
            if value.get("checked_at")
            else None
        ),
        latest_publication_at=(
            datetime.fromisoformat(str(value["latest_publication_at"]))
            if value.get("latest_publication_at")
            else None
        ),
    )


def health_snapshot_to_dict(snapshot: SourceHealthSnapshot) -> dict[str, object]:
    return {
        "source_id": snapshot.source_id,
        "source_name": snapshot.source_name,
        "status": snapshot.status.value,
        "last_checked_at": (
            snapshot.last_checked_at.isoformat() if snapshot.last_checked_at else None
        ),
        "last_success_at": (
            snapshot.last_success_at.isoformat() if snapshot.last_success_at else None
        ),
        "last_failure_at": (
            snapshot.last_failure_at.isoformat() if snapshot.last_failure_at else None
        ),
        "latest_publication_at": (
            snapshot.latest_publication_at.isoformat()
            if snapshot.latest_publication_at
            else None
        ),
        "expected_next_publication": (
            snapshot.expected_next_publication.isoformat()
            if snapshot.expected_next_publication
            else None
        ),
        "consecutive_failures": snapshot.consecutive_failures,
        "failure_threshold": snapshot.failure_threshold,
        "detail": snapshot.detail,
    }


def health_snapshot_from_dict(value: dict[str, object]) -> SourceHealthSnapshot:
    def parsed_datetime(name: str) -> datetime | None:
        return (
            datetime.fromisoformat(str(value[name])) if value.get(name) else None
        )

    return SourceHealthSnapshot(
        source_id=str(value["source_id"]),
        source_name=str(value["source_name"]),
        status=SourceHealthStatus(str(value["status"])),
        last_checked_at=parsed_datetime("last_checked_at"),
        last_success_at=parsed_datetime("last_success_at"),
        last_failure_at=parsed_datetime("last_failure_at"),
        latest_publication_at=parsed_datetime("latest_publication_at"),
        expected_next_publication=(
            date.fromisoformat(str(value["expected_next_publication"]))
            if value.get("expected_next_publication")
            else None
        ),
        consecutive_failures=int(value.get("consecutive_failures", 0)),
        failure_threshold=int(value.get("failure_threshold", 3)),
        detail=str(value.get("detail", "")),
    )


def item_outcome_from_dict(value: dict[str, object]) -> ItemOutcome:
    return ItemOutcome(
        source_id=str(value["source_id"]),
        title=str(value["title"]),
        url=str(value["url"]),
        state=ItemState(str(value["state"])),
        stage=str(value["stage"]) if value.get("stage") else None,
        detail=str(value["detail"]) if value.get("detail") else None,
        document_id=(
            str(value["document_id"]) if value.get("document_id") else None
        ),
    )


def write_manifest(path: Path, target: date, report: CollectionReport) -> None:
    failures = [outcome.summary() for outcome in report.failures]
    no_items = [
        f"{outcome.source_id} ({outcome.source_name}): {outcome.detail}"
        for outcome in report.without_items
    ]
    value = {
        "date": target.isoformat(),
        "documents": [document_to_dict(document) for document in report.documents],
        "source_statuses": [
            outcome_to_dict(outcome) for outcome in report.outcomes
        ],
        "item_statuses": [asdict(outcome) for outcome in report.item_outcomes],
        "source_health": [
            health_snapshot_to_dict(snapshot) for snapshot in report.health_snapshots
        ],
        # Kept as human-readable compatibility fields for existing renderers.
        "errors": failures,
        "skipped": no_items,
    }
    write_json_atomic(path, value)


def write_audit_manifest(path: Path, target: date, report: CollectionReport) -> None:
    failures = [outcome.summary() for outcome in report.failures]
    no_items = [
        f"{outcome.source_id} ({outcome.source_name}): {outcome.detail}"
        for outcome in report.without_items
    ]
    value = {
        "date": target.isoformat(),
        "documents": [
            document_audit_to_dict(document) for document in report.documents
        ],
        "source_statuses": [
            outcome_to_dict(outcome) for outcome in report.outcomes
        ],
        "item_statuses": [asdict(outcome) for outcome in report.item_outcomes],
        "source_health": [
            health_snapshot_to_dict(snapshot) for snapshot in report.health_snapshots
        ],
        "errors": failures,
        "skipped": no_items,
    }
    write_json_atomic(path, value)


def load_manifest(path: Path) -> tuple[date, CollectionReport]:
    value = json.loads(path.read_text(encoding="utf-8"))
    report = CollectionReport(
        documents=[
            document_from_dict(document) for document in value.get("documents", [])
        ],
        outcomes=[
            outcome_from_dict(outcome)
            for outcome in value.get("source_statuses", [])
        ],
        item_outcomes=[
            item_outcome_from_dict(outcome)
            for outcome in value.get("item_statuses", [])
        ],
        health_snapshots=[
            health_snapshot_from_dict(snapshot)
            for snapshot in value.get("source_health", [])
        ],
    )
    return date.fromisoformat(value["date"]), report


def status_markdown(
    target: date,
    report: CollectionReport,
    *,
    content_result: ContentResult | None = None,
    health: RunHealth | None = None,
    sources: list[SourceDefinition] | None = None,
) -> str:
    failures = report.failures
    lines = [
        f"# Source acquisition status - {target.isoformat()}",
        "",
        f"- Documents collected: **{len(report.documents)}**",
        f"- Failed or partial sources: **{len(failures)}**",
        f"- Sources with no same-day item: **{len(report.without_items)}**",
    ]
    if content_result is not None:
        lines.append(f"- Content result: **{content_result.value}**")
    if health is not None:
        lines.append(f"- Run health: **{health.value}**")
    coverage = assess_coverage(report, sources)
    lines.extend(["", "## Material coverage gaps", ""])
    if coverage.material_gaps:
        lines.extend(f"- **{gap}**" for gap in coverage.material_gaps)
    else:
        lines.append("- None under configured critical-role rule v1.")
    lines.extend(["", "## Failed or partial sources", ""])
    if failures:
        lines.extend(f"- **{outcome.summary()}**" for outcome in failures)
    else:
        lines.append("- None.")

    attention = [
        snapshot
        for snapshot in report.health_snapshots
        if snapshot.status in {SourceHealthStatus.WARNING, SourceHealthStatus.FAILING}
    ]
    lines.extend(["", "## Accumulated source-health attention", ""])
    if attention:
        lines.extend(
            f"- `{snapshot.source_id}` - {snapshot.source_name}: "
            f"**{snapshot.status.value}**, {snapshot.consecutive_failures}/"
            f"{snapshot.failure_threshold} consecutive adverse observation(s). "
            f"{snapshot.detail}"
            for snapshot in attention
        )
    else:
        lines.append("- None.")

    skipped = [
        outcome
        for outcome in report.outcomes
        if outcome.state is SourceState.SKIPPED
    ]
    if skipped:
        lines.extend(["", "## Skipped by policy or run limits", ""])
        lines.extend(f"- {outcome.summary()}" for outcome in skipped)

    unavailable = [
        outcome
        for outcome in report.outcomes
        if outcome.state is SourceState.UNAVAILABLE
    ]
    if unavailable:
        lines.extend(["", "## Configured but unavailable", ""])
        lines.extend(f"- {outcome.summary()}" for outcome in unavailable)

    lines.extend(["", "## Sources with no same-day publication", ""])
    if report.without_items:
        lines.extend(
            f"- `{outcome.source_id}` - {outcome.source_name}"
            for outcome in report.without_items
        )
    else:
        lines.append("- None.")

    lines.extend(["", "## Collected sources", ""])
    collected = [
        outcome
        for outcome in report.outcomes
        if outcome.state in {SourceState.COLLECTED, SourceState.PARTIAL}
        and outcome.document_count
    ]
    if collected:
        lines.extend(
            f"- `{outcome.source_id}` - {outcome.source_name}: "
            f"{outcome.document_count} document(s)"
            for outcome in collected
        )
    else:
        lines.append("- None.")
    return "\n".join(lines).rstrip() + "\n"


def print_status(target: date, report: CollectionReport) -> None:
    print(
        f"Collected {len(report.documents)} documents; "
        f"{len(report.failures)} failed or partial sources; "
        f"{len(report.without_items)} sources without same-day items."
    )
    print("\nFAILED OR PARTIAL SOURCES")
    if report.failures:
        for outcome in report.failures:
            print(f"- {outcome.summary()}")
    else:
        print("- None")


def technical_report_markdown(
    target: date,
    report: CollectionReport,
    *,
    corpus_decisions: list[dict[str, object]],
    cited_document_ids: list[str],
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    planned_input_tokens: int | None = None,
    input_token_budget: int | None = None,
    input_token_count_method: str | None = None,
) -> str:
    """Render a body-free, deterministic acquisition and selection audit."""
    decisions = {
        str(item.get("document_id")): item for item in corpus_decisions
    }
    cited = set(cited_document_ids)
    documents_by_source: dict[str, list[Document]] = {}
    for document in report.documents:
        documents_by_source.setdefault(document.source_id, []).append(document)
    for documents in documents_by_source.values():
        documents.sort(
            key=lambda item: (
                item.published_at or datetime.min.replace(tzinfo=timezone.utc),
                item.title,
            ),
            reverse=True,
        )

    included = [
        item
        for item in corpus_decisions
        if str(item.get("outcome", "")).startswith("included")
    ]
    excluded = [
        item for item in corpus_decisions if item.get("outcome") == "omitted"
    ]
    not_extracted = [
        item
        for item in report.item_outcomes
        if item.state
        in {
            ItemState.FAILED,
            ItemState.DEGRADED,
            ItemState.FILTERED,
            ItemState.INVALID_DATE,
            ItemState.SKIPPED,
            ItemState.DUPLICATE,
        }
    ]
    source_word = "source" if len(documents_by_source) == 1 else "sources"
    lines = [
        f"# Macro Sage technical report - {target.isoformat()}",
        "",
        "This file is the operator-facing acquisition and selection record. It is "
        "generated deterministically and makes no additional model request.",
        "",
        "## Collection funnel",
        "",
        f"- **{len(report.documents)} documents collected from "
        f"{len(documents_by_source)} {source_word}.**",
        f"- **{len(included)} documents made available to synthesis.**",
        f"- **{len(cited)} documents were cited in the content report.**",
        f"- **{len(excluded)} collected documents were excluded before synthesis.**",
        f"- **{len(not_extracted)} discovered items were rejected or not added "
        "separately.**",
        f"- Model: `{model}`; input tokens: `{input_tokens or 'unknown'}`; "
        f"output tokens: `{output_tokens or 'unknown'}`.",
        f"- Planned model input: `{planned_input_tokens or 'unknown'}` of "
        f"`{input_token_budget or 'unknown'}` tokens; counting method: "
        f"`{input_token_count_method or 'unknown'}`.",
        "",
        "## Collected documents by source",
        "",
    ]
    for source_id, documents in sorted(
        documents_by_source.items(),
        key=lambda item: (item[1][0].source_name, item[0]),
    ):
        lines.extend(
            [
                f"### {documents[0].source_name} (`{source_id}`) - "
                f"{len(documents)} document(s)",
                "",
            ]
        )
        for document in documents:
            decision = decisions.get(document.id, {})
            outcome = str(decision.get("outcome", "decision_missing"))
            reason_label = str(decision.get("reason_label", outcome)).upper()
            if document.id in cited:
                use_label = "CITED"
            elif outcome.startswith("included"):
                use_label = "AVAILABLE_NOT_CITED"
            else:
                use_label = reason_label
            published = (
                document.published_at.isoformat() if document.published_at else "unknown"
            )
            lines.append(
                f"- **[{use_label}]** {document.title} - {document.url} "
                f"_(published {published})_"
            )
            reason = str(decision.get("reason", "No corpus decision was recorded."))
            lines.append(f"  Reason: `{reason_label}` - {reason}")

    lines.extend(["", "## Collected documents excluded before synthesis", ""])
    if excluded:
        document_lookup = {document.id: document for document in report.documents}
        for decision in excluded:
            document = document_lookup.get(str(decision.get("document_id")))
            title = document.title if document else str(decision.get("document_id"))
            url = document.url if document else "URL unavailable"
            label = str(decision.get("reason_label", "excluded")).upper()
            lines.append(f"- **[{label}]** {title} - {url}")
            lines.append(f"  Reason: {decision.get('reason', 'No reason recorded.')}")
    else:
        lines.append("- None. Every collected document fit within the synthesis corpus.")

    lines.extend(["", "## Discovered materials not added as separate documents", ""])
    if not_extracted:
        for item in not_extracted:
            detail = item.detail or "No additional detail recorded."
            lines.append(
                f"- **[{item.state.value.upper()}]** `{item.source_id}` - "
                f"{item.title} - {item.url}"
            )
            lines.append(f"  Reason: {detail}")
    else:
        lines.append("- None.")

    zero_document_outcomes = [
        outcome
        for outcome in report.outcomes
        if outcome.document_count == 0
        and outcome.state
        not in {
            SourceState.SKIPPED,
            SourceState.UNAVAILABLE,
            SourceState.FILTERED,
            SourceState.DUPLICATE,
        }
    ]
    cadence_attention = [
        outcome
        for outcome in zero_document_outcomes
        if outcome.state in {SourceState.STALE, SourceState.EXPECTED_ABSENT}
    ]
    acquisition_failures = [
        outcome
        for outcome in zero_document_outcomes
        if outcome.state
        in {
            SourceState.FAILED,
            SourceState.INVALID_DATES,
            SourceState.DEGRADED,
            SourceState.PARTIAL,
        }
    ]
    quiet = [
        outcome
        for outcome in zero_document_outcomes
        if outcome.state in {SourceState.NO_ITEMS, SourceState.QUIET_EXPECTED}
    ]
    lines.extend(["", "## Sources with no collected documents", ""])
    lines.extend(["### Publication cadence attention", ""])
    if cadence_attention:
        lines.extend(
            f"- **[{outcome.state.value.upper()}]** `{outcome.source_id}` - "
            f"{outcome.source_name}: {outcome.detail or 'No detail recorded.'}"
            for outcome in cadence_attention
        )
    else:
        lines.append("- None.")
    lines.extend(["", "### Acquisition failures", ""])
    if acquisition_failures:
        lines.extend(
            f"- **[{outcome.state.value.upper()}]** `{outcome.source_id}` - "
            f"{outcome.source_name}: {outcome.detail or 'No detail recorded.'}"
            for outcome in acquisition_failures
        )
    else:
        lines.append("- None.")
    lines.extend(["", "### No same-day publication, within configured cadence", ""])
    if quiet:
        lines.extend(
            f"- `[NO_SAME_DAY_ITEM]` `{outcome.source_id}` - {outcome.source_name}"
            for outcome in quiet
        )
    else:
        lines.append("- None.")

    excluded_sources = [
        outcome
        for outcome in report.outcomes
        if outcome.state
        in {
            SourceState.SKIPPED,
            SourceState.UNAVAILABLE,
            SourceState.FILTERED,
            SourceState.DUPLICATE,
        }
    ]
    lines.extend(["", "## Sources not participating in this run", ""])
    if excluded_sources:
        lines.extend(
            f"- **[{outcome.state.value.upper()}]** `{outcome.source_id}` - "
            f"{outcome.source_name}: {outcome.detail or 'No detail recorded.'}"
            for outcome in excluded_sources
        )
    else:
        lines.append("- None.")
    return "\n".join(lines).rstrip() + "\n"


def health_report_to_dict(
    target: date,
    report: CollectionReport,
    *,
    alert_source_ids: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "date": target.isoformat(),
        "alert_source_ids": list(alert_source_ids),
        "source_statuses": [outcome_to_dict(outcome) for outcome in report.outcomes],
        "source_health": [
            health_snapshot_to_dict(snapshot) for snapshot in report.health_snapshots
        ],
    }


def health_status_markdown(
    target: date,
    report: CollectionReport,
    *,
    alert_source_ids: tuple[str, ...] = (),
) -> str:
    counts = {
        status: sum(snapshot.status is status for snapshot in report.health_snapshots)
        for status in SourceHealthStatus
    }
    alert_ids = set(alert_source_ids)
    persistent_failures = sum(
        snapshot.status is SourceHealthStatus.FAILING
        and snapshot.source_id not in alert_ids
        for snapshot in report.health_snapshots
    )
    lines = [
        f"# Source health - {target.isoformat()}",
        "",
        "This is a discovery-only check. It does not call OpenAI, download podcast "
        "audio, or treat normal event-driven silence as a failure.",
        "",
        f"- Healthy: **{counts[SourceHealthStatus.HEALTHY]}**",
        f"- Quiet as expected: **{counts[SourceHealthStatus.QUIET]}**",
        f"- Warning: **{counts[SourceHealthStatus.WARNING]}**",
        f"- Failing threshold reached: **{counts[SourceHealthStatus.FAILING]}**",
        f"- Newly failing; workflow alert required: **{len(alert_ids)}**",
        f"- Persistently failing; retained without repeat alert: **{persistent_failures}**",
        f"- No history: **{counts[SourceHealthStatus.UNKNOWN]}**",
        "",
        "| Source | Status | Consecutive adverse | Latest publication | Last success | Detail |",
        "|---|---|---:|---|---|---|",
    ]
    for snapshot in report.health_snapshots:
        lines.append(
            f"| `{snapshot.source_id}` {snapshot.source_name} | "
            f"{snapshot.status.value} | {snapshot.consecutive_failures}/"
            f"{snapshot.failure_threshold} | "
            f"{snapshot.latest_publication_at.date() if snapshot.latest_publication_at else 'unknown'} | "
            f"{snapshot.last_success_at.date() if snapshot.last_success_at else 'none'} | "
            f"{snapshot.detail.replace('|', '/')} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def append_github_summary(markdown: str) -> None:
    raw = os.getenv("GITHUB_STEP_SUMMARY")
    if not raw:
        return
    with Path(raw).open("a", encoding="utf-8") as handle:
        handle.write(markdown)
        if not markdown.endswith("\n"):
            handle.write("\n")
