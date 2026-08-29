from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import date, datetime
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
    SourceKind,
    SourceOutcome,
    SourceState,
)


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
    return asdict(outcome)


def outcome_from_dict(value: dict[str, object]) -> SourceOutcome:
    return SourceOutcome(
        source_id=str(value["source_id"]),
        source_name=str(value["source_name"]),
        kind=SourceKind(str(value["kind"])),
        state=SourceState(str(value["state"])),
        document_count=int(value.get("document_count", 0)),
        stage=str(value["stage"]) if value.get("stage") else None,
        detail=str(value["detail"]) if value.get("detail") else None,
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
    )
    return date.fromisoformat(value["date"]), report


def status_markdown(
    target: date,
    report: CollectionReport,
    *,
    content_result: ContentResult | None = None,
    health: RunHealth | None = None,
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
    lines.extend(["", "## Failed or partial sources", ""])
    if failures:
        lines.extend(f"- **{outcome.summary()}**" for outcome in failures)
    else:
        lines.append("- None.")

    skipped = [
        outcome
        for outcome in report.outcomes
        if outcome.state is SourceState.SKIPPED
    ]
    if skipped:
        lines.extend(["", "## Skipped by run limits", ""])
        lines.extend(f"- {outcome.summary()}" for outcome in skipped)

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


def append_github_summary(markdown: str) -> None:
    raw = os.getenv("GITHUB_STEP_SUMMARY")
    if not raw:
        return
    with Path(raw).open("a", encoding="utf-8") as handle:
        handle.write(markdown)
        if not markdown.endswith("\n"):
            handle.write("\n")
