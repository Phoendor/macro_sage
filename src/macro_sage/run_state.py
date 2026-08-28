from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from macro_sage.files import write_json_atomic
from macro_sage.models import (
    CollectionReport,
    ContentResult,
    RunHealth,
    SourceState,
)


@dataclass(frozen=True, slots=True)
class RunPaths:
    run_id: str
    directory: Path
    private_manifest: Path
    audit_manifest: Path
    source_status: Path
    model_selection: Path
    run_record: Path
    brief_json: Path
    brief_markdown: Path
    report_pdf: Path
    latest_pdf: Path


def normalize_run_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    if not normalized:
        raise ValueError("run ID must contain at least one letter or number")
    return normalized[:100]


def default_run_id() -> str:
    github_id = os.getenv("GITHUB_RUN_ID", "").strip()
    if github_id:
        attempt = os.getenv("GITHUB_RUN_ATTEMPT", "1").strip() or "1"
        return normalize_run_id(f"github-{github_id}-{attempt}")
    created = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return normalize_run_id(f"local-{created}-{os.getpid()}")


def build_run_paths(
    output: Path,
    target: date,
    run_id: str | None,
    *,
    create_run_id: bool,
) -> RunPaths:
    resolved_id = normalize_run_id(run_id) if run_id else None
    if resolved_id is None and create_run_id:
        resolved_id = default_run_id()
    directory = (
        output / "runs" / resolved_id
        if resolved_id is not None
        else output / target.isoformat()
    )
    display_id = resolved_id or f"date-{target.isoformat()}"
    return RunPaths(
        run_id=display_id,
        directory=directory,
        private_manifest=directory / "documents.private.json",
        audit_manifest=directory / "manifest.json",
        source_status=directory / "source-status.md",
        model_selection=directory / "model-selection.json",
        run_record=directory / "run.json",
        brief_json=directory / "brief.json",
        brief_markdown=directory / "brief.md",
        report_pdf=directory / "report.pdf",
        latest_pdf=output / "pdf" / f"macro-sage-{target.isoformat()}.pdf",
    )


def classify_collection(report: CollectionReport) -> tuple[ContentResult, RunHealth]:
    content = ContentResult.REPORT if report.documents else ContentResult.NO_DATA
    failures = report.failures
    if not failures:
        return content, RunHealth.HEALTHY
    if report.documents:
        return content, RunHealth.DEGRADED

    substantive = [
        outcome
        for outcome in report.outcomes
        if outcome.state not in {SourceState.SKIPPED}
    ]
    systemic = bool(substantive) and all(
        outcome.state in {SourceState.FAILED, SourceState.PARTIAL}
        for outcome in substantive
    )
    return content, RunHealth.FAILED if systemic else RunHealth.DEGRADED


def redact_text(message: str) -> str:
    secrets = [
        value
        for name, value in os.environ.items()
        if value and any(marker in name.upper() for marker in ("KEY", "TOKEN", "SECRET"))
    ]
    for secret in sorted(secrets, key=len, reverse=True):
        if len(secret) >= 6:
            message = message.replace(secret, "[REDACTED]")
    return message[:2_000]


def sanitized_error(error: BaseException) -> str:
    return redact_text(f"{type(error).__name__}: {error}")


def error_category(error: BaseException) -> str:
    name = type(error).__name__.lower()
    if "citation" in name:
        return "citation_validation"
    if "validation" in name or "schema" in name:
        return "schema_validation"
    if "connection" in name or "timeout" in name:
        return "transport"
    if name.startswith("api") or "openai" in type(error).__module__:
        return "api"
    return "application"


def request_id_from_error(error: BaseException) -> str | None:
    value = getattr(error, "request_id", None)
    return str(value)[:200] if value else None


def update_run_record(path: Path, **updates: Any) -> dict[str, Any]:
    current: dict[str, Any] = {}
    if path.exists():
        current = json.loads(path.read_text(encoding="utf-8"))
    current.update(updates)
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json_atomic(path, current)
    return current


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
