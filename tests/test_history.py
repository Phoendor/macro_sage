from datetime import date, datetime, timezone

from macro_sage.history import (
    BaselineStatus,
    ChangeStatus,
    DirectoryBriefHistory,
    HistoryContext,
    build_history_record,
    canonical_asset,
    canonical_horizon,
    canonical_theme,
)
from macro_sage.models import Bias, DailyBrief
from macro_sage.scheduling import AcquisitionWindow


def brief(*, asset="EUR/USD", bias=Bias.BULLISH, confidence=3, horizon="one week"):
    return DailyBrief(
        as_of_date="2026-08-24",
        executive_summary=["Summary"],
        macro_themes=[
            {
                "theme": "The inflation outlook",
                "market_implication": "Rates remain volatile.",
                "source_ids": ["doc:one"],
            }
        ],
        asset_views=[
            {
                "asset": asset,
                "bias": bias,
                "horizon": horizon,
                "confidence": confidence,
                "drivers": ["Policy"],
                "risks": ["Data"],
                "source_ids": ["doc:one"],
            }
        ],
        top_risks=["Inflation"],
        source_ids_used=["doc:one"],
    )


def record(
    *,
    run_id="run-one",
    target=date(2026, 8, 24),
    value=None,
    context=None,
):
    cutoff = datetime(
        target.year,
        target.month,
        target.day,
        17,
        30,
        tzinfo=timezone.utc,
    )
    return build_history_record(
        run_id=run_id,
        target=target,
        intended_cutoff=cutoff,
        acquisition_window=AcquisitionWindow(
            cutoff.replace(hour=0),
            cutoff,
            "since_previous_successful_cutoff",
        ),
        health="healthy",
        versions={"application": "test", "brief_schema": "1"},
        model="gpt-5.6-luna",
        reasoning_effort="low",
        document_ids=["doc:one", "doc:unused"],
        brief=value or brief(),
        context=context
        or HistoryContext(
            BaselineStatus.FIRST_RUN,
            "No earlier brief.",
            None,
            None,
        ),
    )


def test_canonical_keys_ignore_common_cosmetic_wording():
    assert canonical_asset("EUR/USD") == canonical_asset("EURUSD")
    assert canonical_asset("U.S. Treasury yields") == canonical_asset("US Treasuries")
    assert canonical_horizon("one week") == canonical_horizon("days to weeks")
    assert canonical_theme("The inflation outlook") == canonical_theme("Inflation outlook")
    assert canonical_theme("Central-bank meeting decision")[1] == "event"


def test_canonical_keys_cover_asset_labels_observed_in_the_hosted_canary():
    assert canonical_asset("Euro") == ("fx:eur", "fx")
    assert canonical_asset("NZD") == ("fx:nzd", "fx")
    assert canonical_asset("Copper") == ("commodities:copper", "commodities")
    assert canonical_asset("Agricultural commodities") == (
        "commodities:agriculture",
        "commodities",
    )
    assert canonical_asset("Polish government bonds") == (
        "rates:poland:curve",
        "rates",
    )
    assert canonical_asset("US front-end rates") == (
        "rates:us:front-end",
        "rates",
    )
    assert canonical_horizon("near term") == "short_term"


def test_missing_hosted_store_is_not_silently_called_a_first_run(tmp_path):
    local = DirectoryBriefHistory(tmp_path / "local")
    hosted = DirectoryBriefHistory(tmp_path / "hosted", expect_initialized=True)

    assert local.context(date(2026, 8, 25)).status is BaselineStatus.FIRST_RUN
    assert hosted.context(date(2026, 8, 25)).status is BaselineStatus.MISSING


def test_incompatible_history_marker_is_explicit(tmp_path):
    root = tmp_path / "history"
    root.mkdir()
    (root / "store.json").write_text(
        '{"store_schema_version": 1, "record_schema_version": 999}',
        encoding="utf-8",
    )

    context = DirectoryBriefHistory(root, expect_initialized=True).context(
        date(2026, 8, 25)
    )

    assert context.status is BaselineStatus.INCOMPATIBLE
    assert "999" in context.detail


def test_history_round_trip_loads_previous_and_week_baselines(tmp_path):
    store = DirectoryBriefHistory(tmp_path / "history")
    store.save(record(run_id="week", target=date(2026, 8, 17)))
    store.save(record(run_id="previous", target=date(2026, 8, 24)))

    context = store.context(date(2026, 8, 25))

    assert context.status is BaselineStatus.AVAILABLE
    assert context.previous.run_id == "previous"
    assert context.week_ago.run_id == "week"
    assert context.previous.document_ids == ["doc:one", "doc:unused"]
    assert context.previous.cited_document_ids == ["doc:one"]


def test_calendar_replay_does_not_advance_the_scheduled_collection_cutoff(tmp_path):
    store = DirectoryBriefHistory(tmp_path / "history")
    scheduled = record(run_id="scheduled", target=date(2026, 8, 24))
    manual = record(run_id="manual", target=date(2026, 8, 25)).model_copy(
        update={"acquisition_rule": "explicit_calendar_day"}
    )
    store.save(scheduled)
    store.save(manual)

    context = store.context(
        date(2026, 8, 26),
        datetime(2026, 8, 26, 17, 30, tzinfo=timezone.utc),
    )

    assert context.previous.run_id == "manual"
    assert context.collection_predecessor.run_id == "scheduled"
    assert context.previous_cutoff == scheduled.acquisition_end


def test_asset_comparison_is_stable_across_cosmetic_labels_and_detects_reversal():
    previous = record(value=brief(asset="EUR/USD", bias=Bias.BULLISH))
    context = HistoryContext(
        BaselineStatus.AVAILABLE,
        "Loaded.",
        previous,
        None,
    )

    current = record(
        run_id="run-two",
        target=date(2026, 8, 25),
        value=brief(asset="EURUSD", bias=Bias.BEARISH),
        context=context,
    )

    [change] = current.comparison.asset_view_changes
    assert change.status is ChangeStatus.REVERSED
    assert change.previous_bias is Bias.BULLISH
    assert change.current_bias is Bias.BEARISH
    assert change.current_source_document_ids == ["doc:one"]
    assert current.asset_views[0].supporting_evidence == ["Policy"]
    assert current.asset_views[0].contradicting_evidence == ["Data"]
    assert [event.status for event in current.asset_views[0].status_history] == [
        ChangeStatus.NEW,
        ChangeStatus.REVERSED,
    ]


def test_prior_record_keys_are_renormalized_under_the_current_contract():
    previous = record(value=brief(asset="Euro", horizon="near term"))
    previous.asset_views[0].key = "asset-view:other:euro:unspecified"
    previous.asset_views[0].family = "other"
    previous.asset_views[0].horizon_key = "unspecified"
    context = HistoryContext(
        BaselineStatus.AVAILABLE,
        "Loaded.",
        previous,
        None,
    )

    current = record(
        run_id="run-two",
        target=date(2026, 8, 25),
        value=brief(asset="EUR", horizon="short term"),
        context=context,
    )

    [change] = current.comparison.asset_view_changes
    assert change.key == "asset-view:fx:eur:short_term"
    assert change.status is ChangeStatus.UNCHANGED


def test_absent_current_view_is_carried_until_expiry_not_called_a_reversal():
    previous = record(value=brief(horizon="one week"))
    empty = brief().model_copy(update={"asset_views": []})
    context = HistoryContext(
        BaselineStatus.AVAILABLE,
        "Loaded.",
        previous,
        None,
    )

    current = record(
        run_id="run-two",
        target=date(2026, 8, 25),
        value=empty,
        context=context,
    )

    [change] = current.comparison.asset_view_changes
    assert change.status is ChangeStatus.UNCHANGED
    assert change.carried_forward is True
    assert change.current_source_document_ids == []
    assert current.asset_views[0].freshness.value == "carried"


def test_absent_view_retires_only_after_deterministic_expiry():
    previous = record(value=brief(horizon="intraday"))
    empty = brief().model_copy(update={"asset_views": []})
    context = HistoryContext(
        BaselineStatus.AVAILABLE,
        "Loaded.",
        previous,
        None,
    )

    current = record(
        run_id="run-two",
        target=date(2026, 8, 25),
        value=empty,
        context=context,
    )

    [change] = current.comparison.asset_view_changes
    assert change.status is ChangeStatus.RETIRED
    assert change.resolved_date == date(2026, 8, 25)
    assert current.asset_views == []
