from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, replace
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI

from macro_sage.config import load_sources
from macro_sage.extraction import extract
from macro_sage.feeds import discover
from macro_sage.http import HttpClient
from macro_sage.models import Document, SourceKind
from macro_sage.pipeline import collect_articles
from macro_sage.podcasts import PodcastTranscriber, collect_podcasts
from macro_sage.rendering import render_markdown
from macro_sage.settings import Settings
from macro_sage.storage import DocumentStore
from macro_sage.synthesis import synthesize

DEFAULT_CONFIG = Path("config/sources.toml")
DEFAULT_DATABASE = Path("data/macro_sage.sqlite3")


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _document_json(document: Document) -> dict[str, object]:
    value = asdict(document)
    value["published_at"] = (
        document.published_at.isoformat() if document.published_at else None
    )
    return value


def _run(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    sources = load_sources(args.config)
    target = args.date or datetime.now(ZoneInfo(settings.timezone_name)).date()
    output_dir = args.output / target.isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)

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
            openai_client = OpenAI()
            transcriber = PodcastTranscriber(
                openai_client, http, settings.transcription_model
            )
            podcast_report = collect_podcasts(
                podcast_sources,
                target,
                http,
                store,
                transcriber,
                timezone_name=settings.timezone_name,
            )
            report.documents.extend(podcast_report.documents)
            report.errors.extend(podcast_report.errors)
            report.skipped.extend(podcast_report.skipped)

    manifest = {
        "date": target.isoformat(),
        "documents": [_document_json(document) for document in report.documents],
        "errors": report.errors,
        "skipped": report.skipped,
    }
    (output_dir / "documents.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"Collected {len(report.documents)} documents; "
        f"{len(report.errors)} errors; {len(report.skipped)} sources without items."
    )
    if not report.documents:
        print(f"No documents found for {target.isoformat()}; see documents.json.")
        return 1 if report.errors else 0
    if args.no_ai:
        print(f"Saved source corpus to {output_dir / 'documents.json'}")
        return 0
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required unless --no-ai is used")

    result = synthesize(report.documents, target, settings)
    (output_dir / "brief.json").write_text(
        result.brief.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "brief.md").write_text(
        render_markdown(result.brief, report.documents),
        encoding="utf-8",
    )
    metadata = {
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "omitted_document_ids": result.omitted_ids,
    }
    (output_dir / "run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved brief to {output_dir / 'brief.md'}")
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
        state = "enabled" if source.enabled else "opt-in"
        print(f"{source.id:<24} {source.kind.value:<8} {state:<7} {source.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="macro-sage")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="collect and synthesize one day")
    run.add_argument("--date", type=_date)
    run.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    run.add_argument("--output", type=Path, default=Path("output"))
    run.add_argument("--no-ai", action="store_true")
    run.add_argument("--include-podcasts", action="store_true")
    run.set_defaults(handler=_run)

    validate = subparsers.add_parser(
        "validate-sources", help="live-check enabled article feeds and extraction"
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
