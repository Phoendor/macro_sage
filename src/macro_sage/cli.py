from __future__ import annotations

import argparse
import json
import os
import webbrowser
from dataclasses import asdict, replace
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI

from macro_sage.config import load_inventory, load_sources
from macro_sage.evaluation import evaluate_files
from macro_sage.files import copy_atomic, write_json_atomic, write_text_atomic
from macro_sage.health import check_source_health, newly_failing_source_ids
from macro_sage.history import (
    BriefHistoryRecord,
    DirectoryBriefHistory,
    HistoryContext,
    build_history_record,
)
from macro_sage.http import HttpClient
from macro_sage.models import (
    CollectionReport,
    ContentResult,
    Participation,
    RunHealth,
    SourceDefinition,
    SourceKind,
    SourceOutcome,
    SourceState,
)
from macro_sage.openai_models import (
    ModelSelection,
    describe_selection,
    load_model_selection,
    select_models,
    write_github_env,
)
from macro_sage.pdf import render as render_pdf
from macro_sage.pdf import render_technical as render_technical_pdf
from macro_sage.pipeline import collect_articles
from macro_sage.podcasts import PodcastTranscriber, collect_podcasts
from macro_sage.rendering import render_markdown
from macro_sage.reporting import (
    append_github_summary,
    health_report_to_dict,
    health_status_markdown,
    load_manifest,
    print_status,
    status_markdown,
    technical_report_markdown,
    write_audit_manifest,
    write_manifest,
)
from macro_sage.run_state import (
    RunPaths,
    assess_coverage,
    build_run_paths,
    classify_collection,
    error_category,
    request_id_from_error,
    sanitized_error,
    update_run_record,
)
from macro_sage.scheduling import (
    AcquisitionWindow,
    DateResolution,
    resolve_acquisition_window,
    resolve_target_date,
)
from macro_sage.settings import Settings
from macro_sage.storage import DocumentStore
from macro_sage.synthesis import synthesize
from macro_sage.telegram import (
    TelegramConfig,
    TelegramDeliveryError,
    private_technical_caption,
    public_delayed_message,
    public_no_data_message,
    public_report_caption,
    report_document_name,
    send_pdf,
    send_status,
)
from macro_sage.validation import apply_manual_reviews, run_validation
from macro_sage.versions import transformation_versions

DEFAULT_CONFIG = Path("config/sources.toml")
DEFAULT_DATABASE = Path("data/macro_sage.sqlite3")
DEFAULT_HISTORY = Path("data/brief-history")
DEFAULT_OUTPUT = Path("output")


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _resolution(args: argparse.Namespace, settings: Settings) -> DateResolution:
    saved = getattr(args, "date_resolution", None)
    if saved is not None:
        value = json.loads(saved.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise SystemExit(f"Invalid date-resolution object in {saved}")
        resolution = DateResolution.from_dict(value)
        if args.date is not None and args.date != resolution.target_date:
            raise SystemExit(
                f"Requested date {args.date} does not match {resolution.target_date} in {saved}"
            )
        return resolution
    return resolve_target_date(
        requested=args.date,
        timezone_name=settings.timezone_name,
        scheduled=getattr(args, "scheduled", False),
    )


def _paths(args: argparse.Namespace, target: date, *, create_local: bool) -> RunPaths:
    configured = getattr(args, "run_id", None) or os.getenv("MACRO_SAGE_RUN_ID")
    hosted = bool(os.getenv("GITHUB_RUN_ID"))
    return build_run_paths(
        args.output,
        target,
        configured,
        create_run_id=create_local or hosted,
    )


def _history_context(
    args: argparse.Namespace,
    resolution: DateResolution,
) -> tuple[DirectoryBriefHistory, HistoryContext]:
    store = DirectoryBriefHistory(
        getattr(args, "history", DEFAULT_HISTORY),
        expect_initialized=getattr(args, "require_history", False),
    )
    context = store.context(
        resolution.target_date,
        resolution.intended_cutoff,
    )
    print(f"History baseline: {context.status.value} — {context.detail}")
    append_github_summary(
        "## Durable history\n\n"
        f"- Status: `{context.status.value}`\n"
        f"- Detail: {context.detail}\n"
        f"- Previous brief: `{context.previous.run_id if context.previous else 'none'}`\n"
        f"- One-week brief: `{context.week_ago.run_id if context.week_ago else 'none'}`\n\n"
    )
    return store, context


def _acquisition_window(
    resolution: DateResolution,
    context: HistoryContext,
) -> AcquisitionWindow:
    window = resolve_acquisition_window(
        resolution,
        previous_successful_cutoff=context.previous_cutoff,
        history_available=context.history_available,
    )
    print(
        f"Acquisition window: [{window.start.isoformat()}, {window.end.isoformat()}) "
        f"using {window.rule}"
    )
    append_github_summary(
        "## Acquisition window\n\n"
        f"- Interval: `[{window.start.isoformat()}, {window.end.isoformat()})`\n"
        f"- Rule: `{window.rule}`\n\n"
    )
    return window


def _recorded_acquisition_window(
    paths: RunPaths,
    resolution: DateResolution,
    context: HistoryContext,
) -> AcquisitionWindow:
    if paths.run_record.exists():
        run = json.loads(paths.run_record.read_text(encoding="utf-8"))
        value = run.get("acquisition_window")
        if isinstance(value, dict):
            return AcquisitionWindow.from_dict(value)
    return _acquisition_window(resolution, context)


def _require_api_key(reason: str) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(f"OPENAI_API_KEY is required for {reason}")


def _write_model_selection(path: Path, selection: ModelSelection) -> None:
    write_json_atomic(path, selection.as_dict())


def _report_selection(selection: ModelSelection) -> None:
    lines = describe_selection(selection)
    for line in lines:
        print(line)
    if lines:
        append_github_summary(
            "## OpenAI models\n\n" + "\n".join(f"- {line}" for line in lines) + "\n\n"
        )


def _selection_for(
    settings: Settings,
    *,
    require_synthesis: bool,
    require_transcription: bool,
    selection_path: Path | None,
) -> ModelSelection:
    if selection_path is not None:
        selection = load_model_selection(selection_path)
        if require_synthesis and selection.synthesis is None:
            raise SystemExit(
                f"{selection_path} does not contain a synthesis model selection"
            )
        if require_transcription and selection.transcription is None:
            raise SystemExit(
                f"{selection_path} does not contain a transcription model selection"
            )
        for line in describe_selection(selection):
            print(f"Recorded {line.lower()}")
        return selection

    _require_api_key("model preflight")
    selection = select_models(
        settings,
        require_synthesis=require_synthesis,
        require_transcription=require_transcription,
    )
    _report_selection(selection)
    return selection


def _resolve_date(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    resolution = _resolution(args, settings)
    print(
        f"Resolved {resolution.target_date.isoformat()} using {resolution.rule} "
        f"at {resolution.local_time.isoformat()}"
    )
    if args.output:
        write_json_atomic(args.output, resolution.as_dict())
    if args.github_env:
        args.github_env.parent.mkdir(parents=True, exist_ok=True)
        with args.github_env.open("a", encoding="utf-8") as handle:
            handle.write(f"TARGET_DATE={resolution.target_date.isoformat()}\n")
    append_github_summary(
        "## Publication date\n\n"
        f"- Target: `{resolution.target_date.isoformat()}`\n"
        f"- Rule: `{resolution.rule}`\n"
        f"- Amsterdam time: `{resolution.local_time.isoformat()}`\n\n"
    )
    return 0


def _models(args: argparse.Namespace) -> int:
    _require_api_key("model preflight")
    settings = Settings.from_env()
    if args.run_record:
        update_run_record(
            args.run_record,
            run_id=args.run_id,
            stage="model_preflight_started",
            content_result=ContentResult.NOT_PRODUCED.value,
            health=RunHealth.HEALTHY.value,
            versions=transformation_versions(),
        )
    try:
        selection = select_models(
            settings,
            require_synthesis=args.require_synthesis,
            require_transcription=args.require_transcription,
        )
    except Exception as exc:
        if args.run_record:
            update_run_record(
                args.run_record,
                stage="model_preflight_failed",
                content_result=ContentResult.NOT_PRODUCED.value,
                health=RunHealth.FAILED.value,
                error_category=error_category(exc),
                error=sanitized_error(exc),
                openai_request_id=request_id_from_error(exc),
            )
        raise
    _report_selection(selection)
    if args.output:
        _write_model_selection(args.output, selection)
    if args.github_env:
        write_github_env(selection, args.github_env)
    if args.run_record:
        update_run_record(
            args.run_record,
            stage="model_preflight_complete",
            model_selection=selection.as_dict(),
        )
    return 0


def _collect_corpus(
    args: argparse.Namespace,
    settings: Settings,
    target: date,
    window: AcquisitionWindow,
) -> CollectionReport:
    all_sources = load_sources(args.config, include_disabled=True)
    sources = [
        source
        for source in all_sources
        if source.participation is Participation.DEFAULT
    ]
    participating_sources = list(sources)
    with HttpClient(settings) as http, DocumentStore(args.database) as store:
        report = collect_articles(
            sources,
            target,
            http,
            store,
            timezone_name=settings.timezone_name,
            window=window,
        )
        if args.include_podcasts:
            podcast_sources = [
                source
                for source in all_sources
                if source.participation is Participation.OPTIONAL
                and source.kind is SourceKind.PODCAST
            ]
            participating_sources.extend(podcast_sources)
            transcriber = PodcastTranscriber(
                OpenAI(timeout=settings.request_timeout_seconds),
                http,
                settings.transcription_model,
            )
            podcast_report = collect_podcasts(
                podcast_sources,
                target,
                http,
                store,
                transcriber,
                timezone_name=settings.timezone_name,
                max_episodes=settings.max_podcast_episodes,
                max_minutes=settings.max_podcast_minutes,
                window=window,
            )
            report.documents.extend(podcast_report.documents)
            report.outcomes.extend(podcast_report.outcomes)
            report.item_outcomes.extend(podcast_report.item_outcomes)
        else:
            report.outcomes.extend(
                SourceOutcome(
                    source.id,
                    source.name,
                    source.kind,
                    SourceState.SKIPPED,
                    stage="source participation policy",
                    detail="optional podcast source was not enabled for this run",
                )
                for source in all_sources
                if source.participation is Participation.OPTIONAL
            )
        report.outcomes.extend(
            SourceOutcome(
                source.id,
                source.name,
                source.kind,
                SourceState.UNAVAILABLE,
                stage="source participation policy",
                detail=source.unavailable_reason,
            )
            for source in all_sources
            if source.participation is Participation.UNAVAILABLE
        )
        report.health_snapshots = store.source_health_snapshots(
            participating_sources,
            target=target,
            timezone_name=settings.timezone_name,
        )
    return report


def _save_collection(
    paths: RunPaths,
    target: date,
    report: CollectionReport,
    resolution: DateResolution,
    window: AcquisitionWindow,
    selection: ModelSelection | None,
    sources: list[SourceDefinition],
) -> tuple[ContentResult, RunHealth]:
    paths.directory.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.private_manifest, target, report)
    paths.private_manifest.chmod(0o600)
    write_audit_manifest(paths.audit_manifest, target, report)
    content_result, health = classify_collection(report, sources)
    coverage = assess_coverage(report, sources)
    status = status_markdown(
        target,
        report,
        content_result=content_result,
        health=health,
        sources=sources,
    )
    write_text_atomic(paths.source_status, status)
    run_updates: dict[str, object] = {
        "run_id": paths.run_id,
        "target_date": target.isoformat(),
        "date_resolution": resolution.as_dict(),
        "acquisition_window": window.as_dict(),
        "stage": "collection_complete",
        "content_result": content_result.value,
        "health": health.value,
        "document_count": len(report.documents),
        "failed_or_partial_source_count": len(report.failures),
        "no_item_source_count": len(report.without_items),
        "coverage_assessment": coverage.as_dict(),
        "source_health_attention_count": sum(
            snapshot.status.value in {"warning", "failing"}
            for snapshot in report.health_snapshots
        ),
        "versions": transformation_versions(),
    }
    if selection is not None:
        run_updates["model_selection"] = selection.as_dict()
    update_run_record(paths.run_record, **run_updates)
    print_status(target, report)
    append_github_summary(status + "\n")
    return content_result, health


def _collect(args: argparse.Namespace) -> int:
    base_settings = Settings.from_env()
    settings = replace(
        base_settings,
        max_podcast_episodes=args.max_podcast_episodes
        or base_settings.max_podcast_episodes,
        max_podcast_minutes=args.max_podcast_minutes
        or base_settings.max_podcast_minutes,
    )
    selection: ModelSelection | None = None
    if args.include_podcasts:
        _require_api_key("podcast transcription")
        selection = _selection_for(
            settings,
            require_synthesis=False,
            require_transcription=True,
            selection_path=args.model_selection,
        )
        settings = selection.apply(settings)
    resolution = _resolution(args, settings)
    target = resolution.target_date
    _, history_context = _history_context(args, resolution)
    window = _acquisition_window(resolution, history_context)
    paths = _paths(args, target, create_local=False)
    run_updates: dict[str, object] = {
        "run_id": paths.run_id,
        "target_date": target.isoformat(),
        "date_resolution": resolution.as_dict(),
        "acquisition_window": window.as_dict(),
        "stage": "collection_started",
        "content_result": ContentResult.NOT_PRODUCED.value,
        "health": RunHealth.HEALTHY.value,
        "versions": transformation_versions(),
    }
    if selection is not None:
        run_updates["model_selection"] = selection.as_dict()
    update_run_record(paths.run_record, **run_updates)
    try:
        report = _collect_corpus(args, settings, target, window)
        _, health = _save_collection(
            paths,
            target,
            report,
            resolution,
            window,
            selection,
            load_sources(args.config, include_disabled=True),
        )
    except Exception as exc:
        update_run_record(
            paths.run_record,
            stage="collection_failed",
            content_result=ContentResult.NOT_PRODUCED.value,
            health=RunHealth.FAILED.value,
            error_category=error_category(exc),
            error=sanitized_error(exc),
            openai_request_id=request_id_from_error(exc),
        )
        append_github_summary(
            "## Collection failed\n\n"
            f"- Run ID: `{paths.run_id}`\n"
            f"- Error: `{sanitized_error(exc)}`\n\n"
        )
        raise
    return 1 if health is RunHealth.FAILED else 0


def _synthesize_report(
    *,
    paths: RunPaths,
    target: date,
    report: CollectionReport,
    settings: Settings,
    selection: ModelSelection,
    resolution: DateResolution,
    history_store: DirectoryBriefHistory,
    history_context: HistoryContext,
    window: AcquisitionWindow,
    source_definitions: list[SourceDefinition],
) -> Path:
    _, collection_health = classify_collection(report, source_definitions)
    update_run_record(
        paths.run_record,
        stage="synthesis_started",
        content_result=ContentResult.NOT_PRODUCED.value,
        health=collection_health.value,
        model_selection=selection.as_dict(),
        regeneration_used=False,
    )
    try:
        result = synthesize(
            report.documents,
            target,
            settings,
            history=history_context,
            report=report,
            sources=source_definitions,
            data_cutoff=window.end,
        )
    except Exception as exc:
        update_run_record(
            paths.run_record,
            stage="synthesis_failed",
            content_result=ContentResult.NOT_PRODUCED.value,
            health=RunHealth.FAILED.value,
            error_category=error_category(exc),
            error=sanitized_error(exc),
            openai_request_id=request_id_from_error(exc),
            regeneration_used=False,
        )
        append_github_summary(
            "## Synthesis failed\n\n"
            f"- Run ID: `{paths.run_id}`\n"
            f"- Category: `{error_category(exc)}`\n"
            f"- Error: `{sanitized_error(exc)}`\n\n"
        )
        raise

    history_record = build_history_record(
        run_id=paths.run_id,
        target=target,
        intended_cutoff=resolution.intended_cutoff,
        acquisition_window=window,
        health=collection_health.value,
        versions=transformation_versions(),
        model=result.model,
        reasoning_effort=(
            settings.reasoning_effort
            if result.model.startswith("gpt-5.6")
            else None
        ),
        document_ids=[document.id for document in report.documents],
        brief=result.brief,
        context=history_context,
    )
    paths.directory.mkdir(parents=True, exist_ok=True)
    write_text_atomic(
        paths.brief_json,
        result.brief.model_dump_json(indent=2) + "\n",
    )
    write_text_atomic(
        paths.brief_markdown,
        render_markdown(
            result.brief,
            report.documents,
            report.outcomes,
            history_record.comparison,
        ),
    )
    corpus_decisions = [asdict(decision) for decision in result.corpus_decisions]
    write_text_atomic(
        paths.technical_markdown,
        technical_report_markdown(
            target,
            report,
            corpus_decisions=corpus_decisions,
            cited_document_ids=result.brief.source_ids_used,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            planned_input_tokens=result.planned_input_tokens,
            input_token_budget=result.input_token_budget,
            input_token_count_method=result.input_token_count_method,
        ),
    )
    metadata = {
        "model": result.model,
        "reasoning_effort": (
            settings.reasoning_effort
            if result.model.startswith("gpt-5.6")
            else None
        ),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "planned_input_tokens": result.planned_input_tokens,
        "input_token_budget": result.input_token_budget,
        "input_token_count_method": result.input_token_count_method,
        "omitted_document_ids": result.omitted_ids,
        "truncated_document_ids": result.truncated_ids,
        "citation_map": result.citation_map,
        "corpus_selection": corpus_decisions,
        "failed_or_partial_sources": [
            outcome.summary() for outcome in report.failures
        ],
        "model_selection": selection.as_dict(),
        "versions": transformation_versions(),
        "actual_models": {
            "synthesis": result.model,
        },
        "attempted_models": {
            "synthesis": [result.model],
        },
        "comparison": history_record.comparison.model_dump(mode="json"),
    }
    update_run_record(
        paths.run_record,
        **metadata,
        stage="rendering_started",
        content_result=ContentResult.REPORT.value,
        health=collection_health.value,
    )
    temporary_pdf = paths.report_pdf.with_name(f".{paths.report_pdf.name}.tmp")
    temporary_technical_pdf = paths.technical_pdf.with_name(
        f".{paths.technical_pdf.name}.tmp"
    )
    try:
        render_pdf(
            paths.brief_json,
            paths.audit_manifest,
            paths.run_record,
            temporary_pdf,
        )
        render_technical_pdf(
            paths.brief_json,
            paths.audit_manifest,
            paths.run_record,
            temporary_technical_pdf,
        )
        temporary_pdf.replace(paths.report_pdf)
        temporary_technical_pdf.replace(paths.technical_pdf)
    except Exception as exc:
        temporary_pdf.unlink(missing_ok=True)
        temporary_technical_pdf.unlink(missing_ok=True)
        update_run_record(
            paths.run_record,
            stage="rendering_failed",
            content_result=ContentResult.NOT_PRODUCED.value,
            health=RunHealth.FAILED.value,
            error_category=error_category(exc),
            error=sanitized_error(exc),
            openai_request_id=request_id_from_error(exc),
        )
        append_github_summary(
            "## PDF rendering failed\n\n"
            f"- Run ID: `{paths.run_id}`\n"
            f"- Error: `{sanitized_error(exc)}`\n\n"
        )
        raise
    update_run_record(paths.run_record, stage="history_persistence_started")
    try:
        history_path = history_store.save(history_record)
        copy_atomic(paths.report_pdf, paths.latest_pdf)
        copy_atomic(paths.technical_pdf, paths.latest_technical_pdf)
    except Exception as exc:
        update_run_record(
            paths.run_record,
            stage="history_persistence_failed",
            content_result=ContentResult.REPORT.value,
            health=RunHealth.FAILED.value,
            error_category=error_category(exc),
            error=sanitized_error(exc),
        )
        append_github_summary(
            "## Durable history persistence failed\n\n"
            f"- Run ID: `{paths.run_id}`\n"
            f"- Error: `{sanitized_error(exc)}`\n\n"
        )
        raise
    hosted = bool(os.getenv("GITHUB_RUN_ID"))
    update_run_record(
        paths.run_record,
        stage="history_sync_pending" if hosted else "complete",
        content_result=ContentResult.REPORT.value,
        health=collection_health.value,
        report_pdf=str(paths.report_pdf),
        technical_report_pdf=str(paths.technical_pdf),
        latest_pdf=str(paths.latest_pdf),
        latest_technical_pdf=str(paths.latest_technical_pdf),
        history_record=str(history_path),
    )
    print(f"Saved brief to {paths.brief_markdown}")
    print(f"Saved PDF to {paths.report_pdf}")
    print(f"Saved technical report to {paths.technical_pdf}")
    append_github_summary(
        "## Brief generated\n\n"
        f"- Run ID: `{paths.run_id}`\n"
        f"- Outcome: `report/{collection_health.value}`\n"
        f"- Model: `{result.model}`\n"
        f"- Input tokens: {result.input_tokens or 'n/a'}\n"
        f"- Output tokens: {result.output_tokens or 'n/a'}\n"
        f"- Planned input: {result.planned_input_tokens} / "
        f"{result.input_token_budget} ({result.input_token_count_method})\n"
        f"- Comparison baseline: `{history_record.comparison.baseline_status.value}`\n"
        f"- Previous brief: `{history_record.comparison.previous_run_id or 'none'}`\n"
        f"- PDF: `{paths.report_pdf}`\n\n"
        f"- Technical PDF: `{paths.technical_pdf}`\n\n"
    )
    return paths.report_pdf


def _confirm_history(args: argparse.Namespace) -> int:
    if not args.run_record.exists():
        raise SystemExit(f"Run record does not exist: {args.run_record}")
    run = json.loads(args.run_record.read_text(encoding="utf-8"))
    history_value = run.get("history_record")
    if not history_value:
        raise SystemExit(f"Run record has no prepared history record: {args.run_record}")
    history_path = Path(str(history_value))
    if not history_path.exists():
        raise SystemExit(f"Prepared history record does not exist: {history_path}")
    history_record = BriefHistoryRecord.model_validate_json(
        history_path.read_text(encoding="utf-8")
    )
    if history_record.run_id != run.get("run_id"):
        raise SystemExit(
            f"History run ID {history_record.run_id} does not match {run.get('run_id')}"
        )
    update_run_record(
        args.run_record,
        stage="complete",
        hosted_history_backend=args.backend,
        hosted_history_synced_at=datetime.now(timezone.utc).isoformat(),
    )
    append_github_summary(
        "## Durable history persisted\n\n"
        f"- Backend: `{args.backend}`\n"
        f"- Record: `{history_path}`\n\n"
    )
    print(f"Confirmed durable history record {history_path}")
    return 0


def _synthesize(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    resolution = _resolution(args, settings)
    target = resolution.target_date
    history_store, history_context = _history_context(args, resolution)
    paths = _paths(args, target, create_local=False)
    window = _recorded_acquisition_window(paths, resolution, history_context)
    legacy_manifest = paths.directory / "documents.json"
    manifest_path = (
        paths.private_manifest if paths.private_manifest.exists() else legacy_manifest
    )
    manifest_target, report = load_manifest(manifest_path)
    if manifest_target != target:
        raise SystemExit(
            f"Manifest date {manifest_target} does not match requested date {target}"
        )
    source_definitions = load_sources(args.config, include_disabled=True)
    content_result, health = classify_collection(report, source_definitions)
    if not paths.audit_manifest.exists():
        write_audit_manifest(paths.audit_manifest, target, report)
    if not report.documents:
        update_run_record(
            paths.run_record,
            run_id=paths.run_id,
            target_date=target.isoformat(),
            date_resolution=resolution.as_dict(),
            stage="complete",
            content_result=content_result.value,
            health=health.value,
            versions=transformation_versions(),
            document_count=0,
        )
        append_github_summary(
            "## No brief generated\n\n"
            f"- Run ID: `{paths.run_id}`\n"
            f"- Outcome: `{content_result.value}/{health.value}`\n"
            "- No synthesis request was made.\n\n"
        )
        if getattr(args, "deliver", False):
            delivery_result = _deliver_run_record(
                paths.run_record,
                state_path=args.history / "delivery" / "telegram.json",
                force=False,
                notify_failure=False,
            )
            if delivery_result:
                return delivery_result
        return 1 if health is RunHealth.FAILED else 0

    _require_api_key("brief synthesis")
    selection_path = args.model_selection
    if selection_path is None and paths.model_selection.exists():
        selection_path = paths.model_selection
    selection = _selection_for(
        settings,
        require_synthesis=True,
        require_transcription=False,
        selection_path=selection_path,
    )
    settings = selection.apply(settings)
    _synthesize_report(
        paths=paths,
        target=target,
        report=report,
        settings=settings,
        selection=selection,
        resolution=resolution,
        history_store=history_store,
        history_context=history_context,
        window=window,
        source_definitions=source_definitions,
    )
    if getattr(args, "deliver", False):
        return _deliver_run_record(
            paths.run_record,
            state_path=args.history / "delivery" / "telegram.json",
            force=False,
            notify_failure=False,
        )
    return 0


def _run(args: argparse.Namespace) -> int:
    _require_api_key("brief generation")
    settings = Settings.from_env()
    settings = replace(
        settings,
        max_podcast_episodes=args.max_podcast_episodes
        or settings.max_podcast_episodes,
        max_podcast_minutes=args.max_podcast_minutes
        or settings.max_podcast_minutes,
    )
    selection = _selection_for(
        settings,
        require_synthesis=True,
        require_transcription=args.include_podcasts,
        selection_path=args.model_selection,
    )
    settings = selection.apply(settings)
    resolution = _resolution(args, settings)
    target = resolution.target_date
    history_store, history_context = _history_context(args, resolution)
    window = _acquisition_window(resolution, history_context)
    paths = _paths(args, target, create_local=True)
    _write_model_selection(paths.model_selection, selection)
    update_run_record(
        paths.run_record,
        run_id=paths.run_id,
        target_date=target.isoformat(),
        date_resolution=resolution.as_dict(),
        acquisition_window=window.as_dict(),
        stage="collection_started",
        content_result=ContentResult.NOT_PRODUCED.value,
        health=RunHealth.HEALTHY.value,
        model_selection=selection.as_dict(),
        versions=transformation_versions(),
    )
    try:
        report = _collect_corpus(args, settings, target, window)
        _, health = _save_collection(
            paths,
            target,
            report,
            resolution,
            window,
            selection,
            load_sources(args.config, include_disabled=True),
        )
    except Exception as exc:
        update_run_record(
            paths.run_record,
            stage="collection_failed",
            content_result=ContentResult.NOT_PRODUCED.value,
            health=RunHealth.FAILED.value,
            error_category=error_category(exc),
            error=sanitized_error(exc),
            openai_request_id=request_id_from_error(exc),
        )
        raise
    if not report.documents:
        update_run_record(paths.run_record, stage="complete")
        append_github_summary(
            "## No brief generated\n\n"
            f"- Run ID: `{paths.run_id}`\n"
            f"- Outcome: `no_data/{health.value}`\n"
            "- No synthesis request was made.\n\n"
        )
        if getattr(args, "deliver", False):
            delivery_result = _deliver_run_record(
                paths.run_record,
                state_path=args.history / "delivery" / "telegram.json",
                force=False,
                notify_failure=False,
            )
            if delivery_result:
                return delivery_result
        return 1 if health is RunHealth.FAILED else 0
    _synthesize_report(
        paths=paths,
        target=target,
        report=report,
        settings=settings,
        selection=selection,
        resolution=resolution,
        history_store=history_store,
        history_context=history_context,
        window=window,
        source_definitions=load_sources(args.config, include_disabled=True),
    )
    if getattr(args, "deliver", False):
        return _deliver_run_record(
            paths.run_record,
            state_path=args.history / "delivery" / "telegram.json",
            force=False,
            notify_failure=False,
        )
    return 0


def _validate(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    inventory = load_inventory(args.config)
    article_sources = [
        replace(source, scan_depth=max(args.limit, 1), daily_limit=1)
        for source in inventory.sources
        if source.participation is Participation.DEFAULT
        if source.kind is SourceKind.ARTICLE
    ]
    podcast_sources = (
        [
            replace(source, scan_depth=max(args.limit, 1), daily_limit=1)
            for source in inventory.sources
            if source.participation is Participation.OPTIONAL
            if source.kind is SourceKind.PODCAST
        ]
        if args.include_podcasts
        else []
    )
    output = args.output or Path(
        f"validation/source-validation-{date.today().isoformat()}.json"
    )
    record = run_validation(
        [*article_sources, *podcast_sources],
        settings,
        output=output,
        samples_dir=args.samples_dir,
        validation_operator=args.operator,
        review_bundle=args.review_bundle,
        workers=args.workers,
    )
    print(
        f"\nValidation: {record['passed']} passed, {record['degraded']} degraded, "
        f"{record['failed']} failed. Saved {output}."
    )
    return 1 if record["failed"] else 0


def _review_source_contracts(args: argparse.Namespace) -> int:
    summary = apply_manual_reviews(
        validation_path=args.validation,
        samples_dir=args.samples_dir,
        decisions_path=args.decisions,
    )
    counts = summary["counts"]
    print(
        "Manual source review recorded: "
        f"{counts['approved']} approved, "
        f"{counts['approved_with_limitations']} approved with limitations, "
        f"{counts['rejected']} rejected."
    )
    return 0


def _list_sources(args: argparse.Namespace) -> int:
    for source in load_sources(args.config, include_disabled=args.all):
        state = source.participation.value
        print(f"{source.id:<24} {source.kind.value:<8} {state:<11} {source.name}")
    return 0


def _source_health(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    inventory = load_inventory(args.config)
    sources = [
        source
        for source in inventory.sources
        if source.participation is Participation.DEFAULT
        or (args.include_podcasts and source.participation is Participation.OPTIONAL)
    ]
    target = args.date or datetime.now(ZoneInfo(settings.timezone_name)).date()
    with HttpClient(settings) as http, DocumentStore(args.database) as store:
        previous_snapshots = store.source_health_snapshots(
            sources,
            target=target,
            timezone_name=settings.timezone_name,
        )
        report = check_source_health(
            sources,
            target,
            http,
            store,
            timezone_name=settings.timezone_name,
        )
    alert_source_ids = newly_failing_source_ids(
        previous_snapshots,
        report.health_snapshots,
    )
    markdown = health_status_markdown(
        target,
        report,
        alert_source_ids=alert_source_ids,
    )
    write_json_atomic(
        args.output,
        health_report_to_dict(
            target,
            report,
            alert_source_ids=alert_source_ids,
        ),
    )
    write_text_atomic(args.markdown, markdown)
    print(markdown)
    append_github_summary(markdown + "\n")
    return int(bool(alert_source_ids))


def _evaluate(args: argparse.Namespace) -> int:
    result = evaluate_files(args.brief, args.manifest)
    value = result.as_dict()
    if args.output:
        write_json_atomic(args.output, value)
    print(
        f"Evaluation {'passed' if result.passed else 'failed'}: "
        f"{result.material_claim_count} material claims, "
        f"{result.cited_document_count} cited documents, "
        f"{len(result.issues)} issue(s)."
    )
    for issue in result.issues:
        print(f"- {issue.severity.upper()} {issue.code}: {issue.detail}")
    return 0 if result.passed else 1


def _latest_report(args: argparse.Namespace) -> int:
    pdf_directory = args.output / "pdf"
    candidates = sorted(
        (
            path
            for path in pdf_directory.glob("macro-sage-*.pdf")
            if not path.name.startswith("macro-sage-technical-")
        ),
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    if not candidates:
        raise SystemExit(f"No completed report PDF found under {pdf_directory}")
    latest = candidates[-1].resolve()
    print(latest)
    if args.open and not webbrowser.open(latest.as_uri()):
        raise SystemExit(f"Could not open {latest}; its path was printed above")
    return 0


def _deliver_run_record(
    run_record: Path,
    *,
    state_path: Path,
    force: bool,
    notify_failure: bool,
) -> int:
    config = TelegramConfig.from_env()
    if config is None:
        print("Telegram delivery disabled: configuration is absent.")
        return 0
    run = json.loads(run_record.read_text(encoding="utf-8"))
    target_date = str(run.get("target_date", "unknown"))
    run_id = str(run.get("run_id", "unknown"))
    content_result = str(run.get("content_result", "not_produced"))
    deliveries: dict[str, object] = {}
    try:
        if content_result == ContentResult.REPORT.value and run.get("report_pdf"):
            public_result = send_pdf(
                config,
                pdf_path=Path(str(run["report_pdf"])),
                target_date=target_date,
                run_id=run_id,
                caption=public_report_caption(target_date),
                state_path=state_path,
                force=force,
            )
            deliveries["public"] = public_result.as_dict()
            if config.admin_chat_id:
                technical_path = run.get("technical_report_pdf")
                if not technical_path:
                    raise TelegramDeliveryError(
                        "Run record has no private technical report PDF"
                    )
                admin_result = send_pdf(
                    TelegramConfig(config.bot_token, config.admin_chat_id),
                    pdf_path=Path(str(technical_path)),
                    target_date=target_date,
                    run_id=run_id,
                    caption=private_technical_caption(target_date),
                    state_path=state_path,
                    destination="admin",
                    document_name=report_document_name(target_date, technical=True),
                    force=force,
                )
                deliveries["admin"] = admin_result.as_dict()
            else:
                deliveries["admin"] = {
                    "status": "disabled",
                    "detail": "TELEGRAM_ADMIN_CHAT_ID is not configured.",
                }
        elif content_result == ContentResult.NO_DATA.value:
            public_result = send_status(
                config,
                target_date=target_date,
                run_id=run_id,
                text=public_no_data_message(target_date),
                state_path=state_path,
                status_kind="no_data",
                force=force,
            )
            deliveries["public"] = public_result.as_dict()
        elif notify_failure:
            public_result = send_status(
                config,
                target_date=target_date,
                run_id=run_id,
                text=public_delayed_message(target_date),
                state_path=state_path,
                status_kind="failure",
                force=force,
            )
            deliveries["public"] = public_result.as_dict()
        else:
            print("Telegram failure notification disabled; nothing was sent.")
            return 0
    except TelegramDeliveryError as exc:
        safe_error = sanitized_error(exc)
        update_run_record(
            run_record,
            delivery_stage="telegram_failed",
            telegram_delivery={
                **deliveries,
                "status": "failed",
                "error": safe_error,
            },
        )
        append_github_summary(
            "## Telegram delivery failed\n\n"
            f"- Error: `{safe_error}`\n"
            "- The generated report and audit artifact remain available.\n\n"
        )
        print(f"Telegram delivery failed: {safe_error}")
        return 1
    results = [
        value
        for value in deliveries.values()
        if isinstance(value, dict) and value.get("status") != "disabled"
    ]
    all_duplicates = bool(results) and all(
        value.get("status") == "duplicate_suppressed" for value in results
    )
    update_run_record(
        run_record,
        delivery_stage=(
            "telegram_duplicate_suppressed" if all_duplicates else "telegram_complete"
        ),
        telegram_delivery=deliveries,
    )
    public = deliveries.get("public", {})
    admin = deliveries.get("admin", {})
    append_github_summary(
        "## Telegram delivery\n\n"
        f"- Public status: `{public.get('status', 'not_requested')}`\n"
        f"- Public message ID: `{public.get('message_id') or 'none'}`\n"
        f"- Admin status: `{admin.get('status', 'not_requested')}`\n"
        f"- Admin message ID: `{admin.get('message_id') or 'none'}`\n\n"
    )
    print(
        "Telegram delivery: "
        f"public={public.get('status', 'not_requested')}; "
        f"admin={admin.get('status', 'not_requested')}"
    )
    return 0


def _deliver(args: argparse.Namespace) -> int:
    return _deliver_run_record(
        args.run_record,
        state_path=args.state,
        force=args.force,
        notify_failure=args.notify_failure,
    )


def _add_collection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date", type=_date)
    parser.add_argument("--scheduled", action="store_true")
    parser.add_argument("--date-resolution", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument(
        "--require-history",
        action="store_true",
        help="label an absent durable history marker as missing instead of first run",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model-selection", type=Path)
    parser.add_argument("--include-podcasts", action="store_true")
    parser.add_argument("--max-podcast-episodes", type=_positive_int)
    parser.add_argument("--max-podcast-minutes", type=_positive_int)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="macro-sage")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="collect, synthesize, and render one day")
    _add_collection_arguments(run)
    run.add_argument(
        "--deliver",
        action="store_true",
        help="send the completed result through configured Telegram delivery",
    )
    run.set_defaults(handler=_run)

    collect = subparsers.add_parser(
        "collect",
        help="collect and cache a source corpus without synthesizing it",
    )
    _add_collection_arguments(collect)
    collect.set_defaults(handler=_collect)

    synthesize_parser = subparsers.add_parser(
        "synthesize",
        help="synthesize and render an already collected source corpus",
    )
    synthesize_parser.add_argument("--date", type=_date)
    synthesize_parser.add_argument("--scheduled", action="store_true")
    synthesize_parser.add_argument("--date-resolution", type=Path)
    synthesize_parser.add_argument("--run-id")
    synthesize_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    synthesize_parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    synthesize_parser.add_argument("--require-history", action="store_true")
    synthesize_parser.add_argument("--model-selection", type=Path)
    synthesize_parser.add_argument("--deliver", action="store_true")
    synthesize_parser.set_defaults(handler=_synthesize)

    resolve_date = subparsers.add_parser(
        "resolve-date",
        help="resolve and record the intended Amsterdam publication date",
    )
    resolve_date.add_argument("--date", type=_date)
    resolve_date.add_argument("--scheduled", action="store_true")
    resolve_date.add_argument("--output", type=Path)
    resolve_date.add_argument("--github-env", type=Path)
    resolve_date.set_defaults(handler=_resolve_date)

    models = subparsers.add_parser(
        "models",
        help="verify model access and select explicit fallbacks",
    )
    models.add_argument("--require-synthesis", action="store_true")
    models.add_argument("--require-transcription", action="store_true")
    models.add_argument("--output", type=Path)
    models.add_argument("--github-env", type=Path)
    models.add_argument("--run-record", type=Path)
    models.add_argument("--run-id")
    models.set_defaults(handler=_models)

    confirm_history = subparsers.add_parser(
        "confirm-history",
        help="confirm that a prepared history record reached its hosted backend",
    )
    confirm_history.add_argument("--run-record", type=Path, required=True)
    confirm_history.add_argument("--backend", required=True)
    confirm_history.set_defaults(handler=_confirm_history)

    validate = subparsers.add_parser(
        "validate-sources",
        help="live-check enabled article feeds and extraction",
    )
    validate.add_argument("--limit", type=int, default=1)
    validate.add_argument(
        "--include-podcasts",
        action="store_true",
        help="also verify opt-in podcast feeds without downloading audio",
    )
    validate.add_argument("--output", type=Path)
    validate.add_argument(
        "--samples-dir", type=Path, default=Path("validation/contracts")
    )
    validate.add_argument(
        "--operator",
        "--reviewer",
        dest="operator",
        default="Macro Sage source validator",
        help="identity of the validation operator; this does not mark manual review",
    )
    validate.add_argument(
        "--review-bundle",
        type=Path,
        help="write private excerpts for manual inspection; keep this under output/",
    )
    validate.add_argument("--workers", type=_positive_int, default=6)
    validate.set_defaults(handler=_validate)

    review = subparsers.add_parser(
        "review-source-contracts",
        help="apply explicit, fingerprint-bound manual source review decisions",
    )
    review.add_argument("--validation", type=Path, required=True)
    review.add_argument(
        "--samples-dir", type=Path, default=Path("validation/contracts")
    )
    review.add_argument("--decisions", type=Path, required=True)
    review.set_defaults(handler=_review_source_contracts)

    source_list = subparsers.add_parser("list-sources", help="print configured sources")
    source_list.add_argument("--all", action="store_true")
    source_list.set_defaults(handler=_list_sources)

    source_health = subparsers.add_parser(
        "source-health",
        help="run discovery-only cadence-aware source checks without OpenAI",
    )
    source_health.add_argument("--date", type=_date)
    source_health.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    source_health.add_argument("--include-podcasts", action="store_true")
    source_health.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT / "source-health" / "latest.json",
    )
    source_health.add_argument(
        "--markdown",
        type=Path,
        default=DEFAULT_OUTPUT / "source-health" / "latest.md",
    )
    source_health.set_defaults(handler=_source_health)

    evaluate = subparsers.add_parser(
        "evaluate",
        help="run deterministic grounding and decision-contract checks",
    )
    evaluate.add_argument("--brief", type=Path, required=True)
    evaluate.add_argument("--manifest", type=Path, required=True)
    evaluate.add_argument("--output", type=Path)
    evaluate.set_defaults(handler=_evaluate)

    latest = subparsers.add_parser(
        "latest-report",
        help="print or open the latest completed local PDF",
    )
    latest.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    latest.add_argument("--open", action="store_true")
    latest.set_defaults(handler=_latest_report)

    deliver = subparsers.add_parser(
        "deliver",
        help="deliver an existing run result through configured Telegram",
    )
    deliver.add_argument("--run-record", type=Path, required=True)
    deliver.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_HISTORY / "delivery" / "telegram.json",
    )
    deliver.add_argument("--force", action="store_true")
    deliver.add_argument("--notify-failure", action="store_true")
    deliver.set_defaults(handler=_deliver)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.handler(args))
