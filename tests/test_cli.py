import json
from argparse import Namespace
from datetime import date
from pathlib import Path

from macro_sage.cli import _collect, _synthesize
from macro_sage.models import CollectionReport, SourceKind, SourceOutcome, SourceState


def arguments(tmp_path):
    return Namespace(
        config=Path("config/sources.toml"),
        date=date(2026, 7, 27),
        scheduled=False,
        date_resolution=None,
        run_id="test-run",
        database=tmp_path / "data.sqlite3",
        output=tmp_path / "output",
        model_selection=None,
        include_podcasts=False,
        max_podcast_episodes=None,
        max_podcast_minutes=None,
    )


def test_healthy_no_data_collect_and_synthesize_are_successful(
    monkeypatch,
    tmp_path,
):
    report = CollectionReport(
        outcomes=[
            SourceOutcome(
                "quiet",
                "Quiet Source",
                SourceKind.ARTICLE,
                SourceState.NO_ITEMS,
                detail="no items on 2026-07-27",
            )
        ]
    )
    monkeypatch.setattr("macro_sage.cli._collect_corpus", lambda *_args: report)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    args = arguments(tmp_path)

    assert _collect(args) == 0
    assert _synthesize(args) == 0

    run_path = args.output / "runs" / "test-run" / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    assert run["content_result"] == "no_data"
    assert run["health"] == "healthy"
    assert run["stage"] == "complete"


def test_systemic_empty_collection_returns_failure(monkeypatch, tmp_path):
    report = CollectionReport(
        outcomes=[
            SourceOutcome(
                "broken",
                "Broken Source",
                SourceKind.ARTICLE,
                SourceState.FAILED,
                stage="feed discovery",
                detail="HTTP 403",
            )
        ]
    )
    monkeypatch.setattr("macro_sage.cli._collect_corpus", lambda *_args: report)

    assert _collect(arguments(tmp_path)) == 1
