from __future__ import annotations

import argparse
import json
import os
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI

from macro_sage.config import load_sources
from macro_sage.extraction import extract
from macro_sage.feeds import discover
from macro_sage.http import HttpClient
from macro_sage.models import CollectionReport, SourceKind
from macro_sage.openai_models import (
    ModelSelection,
    describe_selection,
    select_models,
    write_github_env,
)
from macro_sage.pdf import render as render_pdf
from macro_sage.pipeline import collect_articles
from macro_sage.podcasts import PodcastTranscriber, collect_podcasts
from macro_sage.rendering import render_markdown
from macro_sage.reporting import (
    append_github_summary,
    load_manifest,
    print_status,
    status_markdown,
    write_manifest,
)
from macro_sage.settings import Settings
from macro_sage.storage import DocumentStore
from macro_sage.synthesis import synthesize

DEFAULT_CONFIG = Path("config/sources.toml")
DEFAULT_DATABASE = Path("data/macro_sage.sqlite3")
DEFAULT_OUTPUT = Path("output")


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _target(args: argparse.Namespace, settings: Settings) -> date:
    return args.date or datetime.now(ZoneInfo(settings.timezone_name)).date()


def _day_dir(output: Path, target: date) -> Path:
    return output / target.isoformat()


def _require_api_key(reason: str) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(f"OPENAI_API_KEY is required for {reason}")


def _write_model_selection(path: Path, selection: ModelSelection) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(selection.as_dict(), indent=2),
        encoding="utf-8",
    )


def _report_selection(selection: ModelSelection) -> None:
    lines = describe_selection(selection)
    for line in lines:
        print(line)
    if lines:
        append_github_summary(
            "## OpenAI models\n\n" + "\n".join(f"- {line}" for line in lines) + "\n\n"
        )


def _models(args: argparse.Namespace) -> int:
    _require_api_key("model preflight")
    settings = Settings.from_env()
    selection = select_models(
        settings,
        require_synthesis=args.require_synthesis,
        require_transcription=args.require_transcription,
    )
    _report_selection(selection)
    if args.output:
        _write_model_selection(args.output, selection)
    if args.github_env:
        write_github_env(selection, args.github_env)
    return 0


def _collect_corpus(
    args: argparse.Namespace,
    settings: Settings,
    target: date,
) -> CollectionReport:
    sources = load_sources(args.config)
    with HttpClient(settings) as http, DocumentStore(args.database) as store:
        report = collect_articles(
            sources,
            target,
            http,
            store,
            timezone_name=settings.timezone_name,
        )
        if args.include_podcasts:
            podcast_sources = [
                source
                for source in load_sources(args.config, include_disabled=True)
                if source.kind is SourceKind.PODCAST
            ]
            transcriber = PodcastTranscriber(
                OpenAI(),
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
            )
            report.documents.extend(podcast_report.documents)
            report.outcomes.extend(podcast_report.outcomes)
    return report


def _save_collection(
    output: Path,
    target: date,
    report: CollectionReport,
) -> None:
    output_dir = _day_dir(output, target)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(output_dir / "documents.json", target, report)
    status = status_markdown(target, report)
    (output_dir / "source-status.md").write_text(status, encoding="utf-8")
    print_status(target, report)
    append_github_summary(status + "\n")


def _collect(args: argparse.Namespace) -> int:
    base_settings = Settings.from_env()
    settings = replace(
        base_settings,
        max_podcast_episodes=args.max_podcast_episodes
        or base_settings.max_podcast_episodes,
        max_podcast_minutes=args.max_podcast_minutes
        or base_settings.max_podcast_minutes,
    )
    if args.include_podcasts:
        _require_api_key("podcast transcription")
        selection = select_models(
            settings,
            require_synthesis=False,
            require_transcription=True,
        )
        settings = selection.apply(settings)
        _report_selection(selection)
    target = _target(args, settings)
    report = _collect_corpus(args, settings, target)
    _save_collection(args.output, target, report)
    return 0 if report.documents else 1


def _synthesize_report(
    *,
    output: Path,
    target: date,
    report: CollectionReport,
    settings: Settings,
    selection: ModelSelection,
    selection_path: Path | None = None,
) -> Path:
    result = synthesize(report.documents, target, settings)
    output_dir = _day_dir(output, target)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "brief.json").write_text(
        result.brief.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "brief.md").write_text(
        render_markdown(result.brief, report.documents, report.outcomes),
        encoding="utf-8",
    )
    recorded_selection: dict[str, object] = selection.as_dict()
    if selection_path and selection_path.exists():
        recorded_selection = json.loads(selection_path.read_text(encoding="utf-8"))
    metadata = {
        "model": result.model,
        "reasoning_effort": (
            settings.reasoning_effort
            if result.model.startswith("gpt-5.6")
            else None
        ),
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "omitted_document_ids": result.omitted_ids,
        "truncated_document_ids": result.truncated_ids,
        "failed_or_partial_sources": [
            outcome.summary() for outcome in report.failures
        ],
        "model_selection": recorded_selection,
    }
    run_path = output_dir / "run.json"
    run_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    pdf_path = output / "pdf" / f"macro-sage-{target.isoformat()}.pdf"
    render_pdf(
        output_dir / "brief.json",
        output_dir / "documents.json",
        run_path,
        pdf_path,
    )
    print(f"Saved brief to {output_dir / 'brief.md'}")
    print(f"Saved PDF to {pdf_path}")
    append_github_summary(
        "## Brief generated\n\n"
        f"- Model: `{result.model}`\n"
        f"- Input tokens: {result.input_tokens or 'n/a'}\n"
        f"- Output tokens: {result.output_tokens or 'n/a'}\n"
        f"- PDF: `{pdf_path}`\n\n"
    )
    return pdf_path


def _synthesize(args: argparse.Namespace) -> int:
    _require_api_key("brief synthesis")
    settings = Settings.from_env()
    selection = select_models(
        settings,
        require_synthesis=True,
        require_transcription=False,
    )
    settings = selection.apply(settings)
    _report_selection(selection)
    target = _target(args, settings)
    manifest_path = _day_dir(args.output, target) / "documents.json"
    manifest_target, report = load_manifest(manifest_path)
    if manifest_target != target:
        raise SystemExit(
            f"Manifest date {manifest_target} does not match requested date {target}"
        )
    if not report.documents:
        raise SystemExit(f"No documents in {manifest_path}")
    _synthesize_report(
        output=args.output,
        target=target,
        report=report,
        settings=settings,
        selection=selection,
        selection_path=args.model_selection,
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
    selection = select_models(
        settings,
        require_synthesis=True,
        require_transcription=args.include_podcasts,
    )
    settings = selection.apply(settings)
    _report_selection(selection)
    target = _target(args, settings)
    output_dir = _day_dir(args.output, target)
    selection_path = output_dir / "model-selection.json"
    _write_model_selection(selection_path, selection)
    report = _collect_corpus(args, settings, target)
    _save_collection(args.output, target, report)
    if not report.documents:
        return 1
    _synthesize_report(
        output=args.output,
        target=target,
        report=report,
        settings=settings,
        selection=selection,
        selection_path=selection_path,
    )
    return 0


def _validate(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    article_sources = [
        replace(source, max_items=args.limit)
        for source in load_sources(args.config)
        if source.kind is SourceKind.ARTICLE
    ]
    podcast_sources = (
        [
            replace(source, max_items=args.limit)
            for source in load_sources(args.config, include_disabled=True)
            if source.kind is SourceKind.PODCAST
        ]
        if args.include_podcasts
        else []
    )
    article_failures = 0
    podcast_failures = 0
    with HttpClient(settings) as http:
        for source in article_sources:
            try:
                items = discover(source, http)
                document = extract(items[0], http)
                print(
                    f"OK    {source.id:<22} {document.media_type:<16} "
                    f"{len(document.body):>7} chars"
                )
            except Exception as exc:
                article_failures += 1
                print(f"FAIL  {source.id:<22} {exc}")
        for source in podcast_sources:
            try:
                items = discover(source, http)
                if not items or not items[0].media_url:
                    raise ValueError("feed did not expose an audio enclosure")
                print(f"OK    {source.id:<22} audio enclosure discovered")
            except Exception as exc:
                podcast_failures += 1
                print(f"FAIL  {source.id:<22} {exc}")
    print(
        f"\n{len(article_sources) - article_failures}/"
        f"{len(article_sources)} enabled article sources passed."
    )
    if podcast_sources:
        print(
            f"{len(podcast_sources) - podcast_failures}/"
            f"{len(podcast_sources)} opt-in podcast feeds passed."
        )
    return 1 if article_failures or podcast_failures else 0


def _list_sources(args: argparse.Namespace) -> int:
    for source in load_sources(args.config, include_disabled=args.all):
        if source.enabled:
            state = "enabled"
        elif source.kind is SourceKind.PODCAST:
            state = "opt-in"
        else:
            state = "unavailable"
        print(f"{source.id:<24} {source.kind.value:<8} {state:<11} {source.name}")
    return 0


def _add_collection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date", type=_date)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--include-podcasts", action="store_true")
    parser.add_argument("--max-podcast-episodes", type=_positive_int)
    parser.add_argument("--max-podcast-minutes", type=_positive_int)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="macro-sage")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="collect, synthesize, and render one day")
    _add_collection_arguments(run)
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
    synthesize_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    synthesize_parser.add_argument("--model-selection", type=Path)
    synthesize_parser.set_defaults(handler=_synthesize)

    models = subparsers.add_parser(
        "models",
        help="verify model access and select explicit fallbacks",
    )
    models.add_argument("--require-synthesis", action="store_true")
    models.add_argument("--require-transcription", action="store_true")
    models.add_argument("--output", type=Path)
    models.add_argument("--github-env", type=Path)
    models.set_defaults(handler=_models)

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
    validate.set_defaults(handler=_validate)

    source_list = subparsers.add_parser("list-sources", help="print configured sources")
    source_list.add_argument("--all", action="store_true")
    source_list.set_defaults(handler=_list_sources)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.handler(args))
