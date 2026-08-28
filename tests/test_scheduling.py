from datetime import date, datetime, timezone

from macro_sage.scheduling import resolve_target_date


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
