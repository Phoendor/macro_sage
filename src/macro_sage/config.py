from __future__ import annotations

import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

from macro_sage.models import (
    AcquisitionMode,
    CadenceBasis,
    CandidateDefinition,
    EvidenceTier,
    Participation,
    SourceDefinition,
    SourceInventory,
    SourceKind,
    ValidationStatus,
)


class ConfigurationError(ValueError):
    pass


def _date(value: object, *, field: str) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ConfigurationError(f"{field} must be an ISO date") from exc


def _required_date(value: object, *, field: str) -> date:
    parsed = _date(value, field=field)
    if parsed is None:
        raise ConfigurationError(f"{field} is required")
    return parsed


def _strings(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ConfigurationError(f"{field} must be a non-empty string list")
    return tuple(item.strip() for item in value)


def _participation(row: dict[str, Any], kind: SourceKind) -> Participation:
    configured = row.get("participation")
    if configured is not None:
        return Participation(str(configured))
    enabled = bool(row.get("enabled", True))
    if enabled:
        return Participation.DEFAULT
    return (
        Participation.OPTIONAL
        if kind is SourceKind.PODCAST
        else Participation.UNAVAILABLE
    )


def _source(row: dict[str, Any], *, strict: bool) -> SourceDefinition:
    try:
        kind = SourceKind(row.get("kind", "article"))
        participation = _participation(row, kind)
        acquisition_default = (
            AcquisitionMode.MACHINE_TRANSCRIPT
            if kind is SourceKind.PODCAST
            else AcquisitionMode.FULL_PDF
            if row.get("prefer_pdf")
            else AcquisitionMode.FULL_HTML
        )
        daily_limit = int(row.get("daily_limit", row.get("max_items", 3)))
        source = SourceDefinition(
            id=str(row["id"]),
            name=str(row["name"]),
            publisher=str(row["publisher"]),
            feed_url=str(row["feed_url"]),
            category=str(row["category"]),
            kind=kind,
            participation=participation,
            homepage_url=str(row.get("homepage_url", "")),
            description=str(row.get("description", "")),
            rationale=str(row.get("rationale", "")),
            evidence_tier=EvidenceTier(
                row.get("evidence_tier", EvidenceTier.INSTITUTIONAL_ANALYSIS)
            ),
            geographies=_strings(
                row.get("geographies", ["global"]), field="geographies"
            ),
            topics=_strings(row.get("topics", ["macro"]), field="topics"),
            asset_classes=_strings(
                row.get("asset_classes", ["rates", "fx", "equities"]),
                field="asset_classes",
            ),
            language=str(row.get("language", "en")),
            cadence=str(row.get("cadence", "event-driven")),
            cadence_basis=CadenceBasis(
                row.get("cadence_basis", CadenceBasis.EXPECTED)
            ),
            max_gap_days=int(row.get("max_gap_days", 31)),
            active_weekdays=tuple(
                int(value) for value in row.get("active_weekdays", [0, 1, 2, 3, 4])
            ),
            event_driven=bool(row.get("event_driven", True)),
            acquisition_mode=AcquisitionMode(
                row.get("acquisition_mode", acquisition_default)
            ),
            priority=int(row.get("priority", 50)),
            critical_coverage_role=(
                str(row["critical_coverage_role"])
                if row.get("critical_coverage_role")
                else None
            ),
            scan_depth=int(row.get("scan_depth", max(50, daily_limit))),
            daily_limit=daily_limit,
            publisher_cap=int(row.get("publisher_cap", 5)),
            validation_status=ValidationStatus(
                row.get("validation_status", ValidationStatus.NEEDS_VALIDATION)
            ),
            last_validation_date=_date(
                row.get("last_validation_date"), field="last_validation_date"
            ),
            validation_note=(
                str(row["validation_note"]) if row.get("validation_note") else None
            ),
            owner=str(row.get("owner", row["publisher"])),
            include_url_pattern=row.get("include_url_pattern"),
            exclude_title_pattern=row.get("exclude_title_pattern"),
            pdf_link_pattern=row.get("pdf_link_pattern"),
            published_from_updated=bool(row.get("published_from_updated", False)),
            published_from_feed_last_modified=bool(
                row.get("published_from_feed_last_modified", False)
            ),
            max_future_days=int(row.get("max_future_days", 1)),
            unavailable_reason=row.get(
                "unavailable_reason", row.get("disabled_reason")
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"Invalid source row: {row!r}") from exc

    if not source.feed_url.startswith("https://"):
        raise ConfigurationError(f"{source.id}: feed_url must use HTTPS")
    if source.homepage_url and not source.homepage_url.startswith("https://"):
        raise ConfigurationError(f"{source.id}: homepage_url must use HTTPS")
    for name, value in (
        ("scan_depth", source.scan_depth),
        ("daily_limit", source.daily_limit),
        ("publisher_cap", source.publisher_cap),
        ("max_gap_days", source.max_gap_days),
        ("max_future_days", source.max_future_days),
    ):
        if value < 1:
            raise ConfigurationError(f"{source.id}: {name} must be positive")
    if source.daily_limit > source.scan_depth:
        raise ConfigurationError(f"{source.id}: daily_limit cannot exceed scan_depth")
    if any(day < 0 or day > 6 for day in source.active_weekdays):
        raise ConfigurationError(f"{source.id}: active_weekdays must be 0 through 6")
    if (
        source.participation is Participation.UNAVAILABLE
        and not source.unavailable_reason
    ):
        raise ConfigurationError(
            f"{source.id}: unavailable sources require unavailable_reason"
        )
    if source.acquisition_mode is AcquisitionMode.FULL_PDF and not source.pdf_link_pattern:
        raise ConfigurationError(
            f"{source.id}: full_pdf sources require pdf_link_pattern"
        )
    for field_name, pattern in (
        ("include_url_pattern", source.include_url_pattern),
        ("exclude_title_pattern", source.exclude_title_pattern),
        ("pdf_link_pattern", source.pdf_link_pattern),
    ):
        if pattern is not None:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ConfigurationError(
                    f"{source.id}: invalid {field_name}: {pattern!r}"
                ) from exc
    if strict:
        missing = [
            name
            for name in ("homepage_url", "description", "rationale", "cadence")
            if not getattr(source, name)
        ]
        if missing:
            raise ConfigurationError(
                f"{source.id}: version 2 inventory is missing {', '.join(missing)}"
            )
    return source


def _candidate(row: dict[str, Any]) -> CandidateDefinition:
    try:
        return CandidateDefinition(
            id=str(row["id"]),
            name=str(row["name"]),
            homepage_url=str(row["homepage_url"]),
            expected_cadence=str(row["expected_cadence"]),
            cadence_basis=CadenceBasis(row["cadence_basis"]),
            description=str(row["description"]),
            rationale=str(row["rationale"]),
            attempted_endpoints=_strings(
                row["attempted_endpoints"], field="attempted_endpoints"
            ),
            precise_failure=str(row["precise_failure"]),
            last_attempt_date=_required_date(
                row["last_attempt_date"], field="last_attempt_date"
            ),
            lawful_alternative=(
                str(row["lawful_alternative"])
                if row.get("lawful_alternative")
                else None
            ),
            constraint=str(row["constraint"]),
            next_review_date=_required_date(
                row["next_review_date"], field="next_review_date"
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"Invalid candidate row: {row!r}") from exc


def load_inventory(path: str | Path) -> SourceInventory:
    config_path = Path(path)
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    version = int(raw.get("version", 1))
    rows = raw.get("sources")
    if not isinstance(rows, list) or not rows:
        raise ConfigurationError("sources.toml must contain at least one [[sources]] table")
    defaults = raw.get("source_defaults", {})
    if not isinstance(defaults, dict):
        raise ConfigurationError("source_defaults must be a table")
    sources: list[SourceDefinition] = []
    seen: set[str] = set()
    for raw_row in rows:
        row = {**defaults, **raw_row}
        source = _source(row, strict=version >= 2)
        if source.id in seen:
            raise ConfigurationError(f"Duplicate source id: {source.id}")
        seen.add(source.id)
        sources.append(source)
    candidates = tuple(_candidate(row) for row in raw.get("candidates", []))
    candidate_ids = [candidate.id for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ConfigurationError("Duplicate candidate id")
    if seen.intersection(candidate_ids):
        raise ConfigurationError("Source and candidate ids must not overlap")
    return SourceInventory(version, tuple(sources), candidates)


def load_sources(
    path: str | Path,
    *,
    include_disabled: bool = False,
) -> list[SourceDefinition]:
    inventory = load_inventory(path)
    if include_disabled:
        return list(inventory.sources)
    return [
        source
        for source in inventory.sources
        if source.participation is Participation.DEFAULT
    ]
