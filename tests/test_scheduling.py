from datetime import date, datetime, timedelta, timezone

from macro_sage.scheduling import (
    DateResolution,
    resolve_acquisition_window,
    resolve_target_date,
)


def test_explicit_date_is_preserved():
    resolution = resolve_target_date(
        requested=date(2026, 7, 27),
        timezone_name="Europe/Amsterdam",
        scheduled=True,
        now=datetime(2026, 8, 28, 1, 35, tzinfo=timezone.utc),
    )

    assert resolution.target_date == date(2026, 7, 27)
    assert resolution.rule == "explicit_date"


def test_delayed_runner_before_cutoff_uses_previous_weekday():
    resolution = resolve_target_date(
        requested=None,
        timezone_name="Europe/Amsterdam",
        scheduled=True,
        now=datetime(2026, 8, 28, 1, 35, tzinfo=timezone.utc),
    )

    assert resolution.target_date == date(2026, 8, 27)


def test_scheduled_weekend_uses_friday():
    resolution = resolve_target_date(
        requested=None,
        timezone_name="Europe/Amsterdam",
        scheduled=True,
        now=datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
    )

    assert resolution.target_date == date(2026, 8, 28)


def test_dst_start_after_cutoff_uses_current_local_day():
    resolution = resolve_target_date(
        requested=None,
        timezone_name="Europe/Amsterdam",
        scheduled=True,
        now=datetime(2026, 3, 30, 17, 31, tzinfo=timezone.utc),
    )

    assert resolution.local_time.isoformat().startswith("2026-03-30T19:31")
    assert resolution.target_date == date(2026, 3, 30)


def test_dst_end_before_cutoff_uses_previous_weekday():
    resolution = resolve_target_date(
        requested=None,
        timezone_name="Europe/Amsterdam",
        scheduled=True,
        now=datetime(2026, 10, 26, 18, 29, tzinfo=timezone.utc),
    )

    assert resolution.local_time.isoformat().startswith("2026-10-26T19:29")
    assert resolution.target_date == date(2026, 10, 23)


def test_scheduled_resolution_crosses_year_boundary():
    resolution = resolve_target_date(
        requested=None,
        timezone_name="Europe/Amsterdam",
        scheduled=True,
        now=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
    )

    assert resolution.target_date == date(2025, 12, 31)


def test_resolution_records_intended_cutoff_independent_of_runner_start():
    resolution = resolve_target_date(
        requested=None,
        timezone_name="Europe/Amsterdam",
        scheduled=True,
        now=datetime(2026, 8, 28, 1, 35, tzinfo=timezone.utc),
    )

    assert resolution.intended_cutoff.isoformat() == "2026-08-27T19:30:00+02:00"
    assert DateResolution.from_dict(resolution.as_dict()) == resolution


def test_manual_date_is_a_deterministic_local_calendar_window():
    resolution = resolve_target_date(
        requested=date(2026, 3, 29),
        timezone_name="Europe/Amsterdam",
        scheduled=False,
        now=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    window = resolve_acquisition_window(
        resolution,
        previous_successful_cutoff=datetime(2026, 3, 28, tzinfo=timezone.utc),
        history_available=True,
    )

    assert window.rule == "explicit_calendar_day"
    assert window.start.isoformat() == "2026-03-28T23:00:00+00:00"
    assert window.end.isoformat() == "2026-03-29T22:00:00+00:00"


def test_monday_window_includes_friday_evening_and_weekend_without_overlap():
    resolution = resolve_target_date(
        requested=None,
        timezone_name="Europe/Amsterdam",
        scheduled=True,
        now=datetime(2026, 8, 31, 18, 0, tzinfo=timezone.utc),
    )
    previous = datetime(2026, 8, 28, 17, 30, tzinfo=timezone.utc)

    window = resolve_acquisition_window(
        resolution,
        previous_successful_cutoff=previous,
        history_available=True,
    )

    assert window.rule == "since_previous_successful_cutoff"
    assert window.contains(previous)
    assert window.contains(datetime(2026, 8, 30, 12, tzinfo=timezone.utc))
    assert not window.contains(window.end)


def test_missing_history_uses_visible_recovery_window():
    resolution = resolve_target_date(
        requested=None,
        timezone_name="Europe/Amsterdam",
        scheduled=True,
        now=datetime(2026, 8, 31, 18, 0, tzinfo=timezone.utc),
    )

    window = resolve_acquisition_window(
        resolution,
        previous_successful_cutoff=None,
        history_available=False,
    )

    assert window.rule == "history_unavailable_seven_day_recovery"
    assert window.end - window.start == timedelta(days=7)
