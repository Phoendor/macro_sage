from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from macro_sage.extraction import extract
from macro_sage.feeds import discover_with_diagnostics
from macro_sage.files import write_json_atomic
from macro_sage.http import HttpClient
from macro_sage.models import SourceDefinition, SourceKind
from macro_sage.run_state import sanitized_error
from macro_sage.settings import Settings
from macro_sage.versions import SOURCE_CONFIG_VERSION, transformation_versions

VALIDATION_RECORD_VERSION = 1


def _entry(item) -> dict[str, object]:
    return {
        "title": item.title,
        "url": item.url,
        "original_url": item.original_url,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "raw_published": item.raw_published,
        "raw_updated": item.raw_updated,
        "guid": item.guid,
        "media_url": item.media_url,
        "media_type": item.media_type,
        "timestamp_warning": item.timestamp_warning,
    }


def validate_source(source: SourceDefinition, client: HttpClient) -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc)
    base: dict[str, Any] = {
        "source_id": source.id,
        "source_name": source.name,
        "kind": source.kind.value,
        "participation": source.participation.value,
        "checked_at": checked_at.isoformat(),
        "status": "failed",
        "failure_stage": None,
        "error": None,
        "warnings": [],
    }
    try:
        discovery = discover_with_diagnostics(source, client)
    except Exception as exc:
        base.update(failure_stage="feed_discovery", error=sanitized_error(exc))
        return base
    base.update(
        feed_url=discovery.feed_url,
        resolved_feed_url=discovery.resolved_feed_url,
        http_status=discovery.http_status,
        redirect_chain=list(discovery.redirect_chain),
        feed_content_type=discovery.feed_content_type,
        feed_content_length=discovery.feed_content_length,
        parsed_entry_count=discovery.parsed_entry_count,
        filtered_entry_count=discovery.filtered_entry_count,
        invalid_date_count=discovery.invalid_date_count,
        duplicate_count=discovery.duplicate_count,
        warnings=list(discovery.warnings),
    )
    if not discovery.items:
        base.update(
            failure_stage="feed_filtering",
            error="No usable entries remained after source policy filters.",
        )
        return base
    valid_items = [item for item in discovery.items if item.published_at is not None]
    newest = valid_items[0] if valid_items else discovery.items[0]
    base["newest_entry"] = _entry(newest)
    if source.kind is SourceKind.PODCAST:
        if not newest.media_url:
            base.update(
                failure_stage="podcast_enclosure",
                error="Newest podcast entry has no audio enclosure.",
            )
            return base
        try:
            response = client.probe(newest.media_url)
            content_type = response.headers.get("content-type", "")
            content_length = response.headers.get("content-length")
            declared_audio = bool(
                newest.media_type and newest.media_type.startswith("audio/")
            )
            probed_audio = content_type.startswith("audio/")
            warnings = list(base["warnings"])
            if declared_audio and not probed_audio:
                warnings.append(
                    f"probe returned {content_type or 'no content type'}; "
                    f"feed declares {newest.media_type}"
                )
            base.update(
                status="passed" if declared_audio or probed_audio else "degraded",
                extraction_method="audio_enclosure_probe",
                resolved_content_url=str(response.url),
                content_type=content_type,
                content_length=int(content_length) if content_length else None,
                declared_media_type=newest.media_type,
                probe_http_status=response.status_code,
                warnings=warnings,
            )
            response.close()
        except Exception as exc:
            base.update(
                failure_stage="podcast_enclosure",
                error=sanitized_error(exc),
            )
        return base
    document = None
    selected = None
    attempts: list[dict[str, object]] = []
    for candidate in (valid_items or discovery.items)[:3]:
        try:
            document = extract(candidate, client)
            selected = candidate
            attempts.append(
                {"title": candidate.title, "url": candidate.url, "status": "passed"}
            )
            break
        except Exception as exc:
            attempts.append(
                {
                    "title": candidate.title,
                    "url": candidate.url,
                    "status": "failed",
                    "error": sanitized_error(exc),
                }
            )
    base["extraction_attempts"] = attempts
    if document is None or selected is None:
        base.update(
            failure_stage="content_extraction",
            error=str(attempts[-1]["error"]) if attempts else "No extraction candidate",
        )
        return base
    base["representative_entry"] = _entry(selected)
    failed_attempts = [attempt for attempt in attempts if attempt["status"] == "failed"]
    warnings = [*base["warnings"], *document.quality_flags]
    warnings.extend(
        f"representative fallback after extraction failure: {attempt['title']}: "
        f"{attempt['error']}"
        for attempt in failed_attempts
    )
    base.update(
        status="degraded" if document.quality_flags or failed_attempts else "passed",
        extraction_method=document.acquisition_method.value,
        resolved_content_url=document.resolved_content_url,
        canonical_url=document.canonical_url,
        content_type=document.media_type,
        content_length=len(document.body),
        content_sha256=document.content_sha256,
        revision_id=document.revision_id,
        page_count=document.page_count,
        language=document.language,
        quality_flags=list(document.quality_flags),
        warnings=warnings,
    )
    return base


def _live(source: SourceDefinition, settings: Settings) -> dict[str, Any]:
    with HttpClient(settings) as client:
        return validate_source(source, client)


def run_validation(
    sources: list[SourceDefinition],
    settings: Settings,
    *,
    output: Path,
    samples_dir: Path,
    reviewer: str,
    workers: int = 6,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_live, source, settings): source for source in sources}
        for future in as_completed(futures):
            source = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "source_id": source.id,
                    "source_name": source.name,
                    "kind": source.kind.value,
                    "participation": source.participation.value,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "status": "failed",
                    "failure_stage": "validator",
                    "error": sanitized_error(exc),
                    "warnings": [],
                }
            results.append(result)
            print(
                f"{result['status'].upper():8} {source.id:<28} "
                f"{result.get('failure_stage') or result.get('extraction_method', '')}",
                flush=True,
            )
    results.sort(key=lambda value: str(value["source_id"]))
    completed = datetime.now(timezone.utc)
    record = {
        "record_version": VALIDATION_RECORD_VERSION,
        "source_config_version": SOURCE_CONFIG_VERSION,
        "transformation_versions": transformation_versions(),
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "reviewer": reviewer,
        "source_count": len(results),
        "passed": sum(result["status"] == "passed" for result in results),
        "degraded": sum(result["status"] == "degraded" for result in results),
        "failed": sum(result["status"] == "failed" for result in results),
        "sources": results,
    }
    write_json_atomic(output, record)
    samples_dir.mkdir(parents=True, exist_ok=True)
    current_ids = {str(result["source_id"]) for result in results}
    for stale_sample in samples_dir.glob("*.json"):
        if stale_sample.stem not in current_ids:
            stale_sample.unlink()
    for result in results:
        if result["status"] == "failed":
            (samples_dir / f"{result['source_id']}.json").unlink(missing_ok=True)
            continue
        sample = {
            "contract_version": 1,
            "source_id": result["source_id"],
            "review": {
                "status": "reviewed",
                "reviewer": reviewer,
                "reviewed_at": completed.isoformat(),
            },
            "newest_entry": result.get("newest_entry"),
            "representative_entry": result.get("representative_entry"),
            "extraction_attempts": result.get("extraction_attempts"),
            "resolved_content_url": result.get("resolved_content_url"),
            "extraction_method": result.get("extraction_method"),
            "content_type": result.get("content_type"),
            "content_length": result.get("content_length"),
            "content_sha256": result.get("content_sha256"),
            "revision_id": result.get("revision_id"),
            "warnings": result.get("warnings", []),
        }
        write_json_atomic(samples_dir / f"{result['source_id']}.json", sample)
    return record
