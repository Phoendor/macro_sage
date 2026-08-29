from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class DateResolution:
    target_date: date
    requested_date: date | None
    rule: str
    timezone_name: str
    local_time: datetime
    utc_time: datetime
    intended_cutoff: datetime

    def as_dict(self) -> dict[str, str | None]:
        value = asdict(self)
        value["target_date"] = self.target_date.isoformat()
        value["requested_date"] = (
            self.requested_date.isoformat() if self.requested_date else None
        )
        value["local_time"] = self.local_time.isoformat()
        value["utc_time"] = self.utc_time.isoformat()
        value["intended_cutoff"] = self.intended_cutoff.isoformat()
        return value

    @classmethod
    def from_dict(cls, value: dict[str, str | None]) -> DateResolution:
        requested = value.get("requested_date")
        timezone_name = str(value["timezone_name"])
        target_date = date.fromisoformat(str(value["target_date"]))
        intended = value.get("intended_cutoff")
        if intended:
            intended_cutoff = datetime.fromisoformat(str(intended))
        else:
            # Compatibility with date-resolution records written before schema 2.
            intended_cutoff = datetime.combine(
                target_date + timedelta(days=1),
                time.min,
                ZoneInfo(timezone_name),
            )
        return cls(
            target_date=target_date,
            requested_date=date.fromisoformat(requested) if requested else None,
            rule=str(value["rule"]),
            timezone_name=timezone_name,
            local_time=datetime.fromisoformat(str(value["local_time"])),
            utc_time=datetime.fromisoformat(str(value["utc_time"])),
            intended_cutoff=intended_cutoff,
        )


@dataclass(frozen=True, slots=True)
class AcquisitionWindow:
    start: datetime
    end: datetime
    rule: str

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("acquisition-window bounds must be timezone-aware")
        if self.start >= self.end:
            raise ValueError("acquisition-window start must precede its end")

    def contains(self, value: datetime | None) -> bool:
        if value is None:
            return False
        return self.start <= value.astimezone(timezone.utc) < self.end

    def as_dict(self) -> dict[str, str]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "rule": self.rule,
            "interval": "[start, end)",
        }

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> AcquisitionWindow:
        return cls(
            datetime.fromisoformat(value["start"]),
            datetime.fromisoformat(value["end"]),
            value["rule"],
        )


def _previous_weekday(value: date) -> date:
    candidate = value - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


def resolve_target_date(
    *,
    requested: date | None,
    timezone_name: str,
    scheduled: bool,
    now: datetime | None = None,
    scheduled_time: time = time(19, 30),
) -> DateResolution:
    zone = ZoneInfo(timezone_name)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    utc_now = current.astimezone(timezone.utc)
    local_now = current.astimezone(zone)

    if requested is not None:
        target = requested
        rule = "explicit_date"
    elif not scheduled:
        target = local_now.date()
        rule = "current_local_date"
    elif local_now.weekday() < 5 and local_now.timetz().replace(tzinfo=None) >= scheduled_time:
        target = local_now.date()
        rule = "scheduled_current_weekday_after_cutoff"
    else:
        target = _previous_weekday(local_now.date())
        rule = "scheduled_previous_weekday_before_cutoff_or_weekend"

    if requested is not None or not scheduled:
        intended_cutoff = datetime.combine(
            target + timedelta(days=1),
            time.min,
            zone,
        )
    else:
        intended_cutoff = datetime.combine(target, scheduled_time, zone)

    return DateResolution(
        target_date=target,
        requested_date=requested,
        rule=rule,
        timezone_name=timezone_name,
        local_time=local_now,
        utc_time=utc_now,
        intended_cutoff=intended_cutoff,
    )


def resolve_acquisition_window(
    resolution: DateResolution,
    *,
    previous_successful_cutoff: datetime | None,
    history_available: bool,
    scheduled_time: time = time(19, 30),
) -> AcquisitionWindow:
    """Resolve the immutable collection interval for one run.

    Manual dates always replay one local calendar day. Scheduled runs use the
    last durable successful cutoff. A first scheduled run starts at the prior
    scheduled weekday cutoff; missing/corrupt history uses a visible seven-day
    recovery window so history loss cannot create a silent gap.
    """
    zone = ZoneInfo(resolution.timezone_name)
    end = resolution.intended_cutoff.astimezone(timezone.utc)
    if not resolution.rule.startswith("scheduled_"):
        start = datetime.combine(resolution.target_date, time.min, zone)
        return AcquisitionWindow(
            start.astimezone(timezone.utc),
            end,
            "explicit_calendar_day",
        )
    if previous_successful_cutoff is not None:
        return AcquisitionWindow(
            previous_successful_cutoff.astimezone(timezone.utc),
            end,
            "since_previous_successful_cutoff",
        )
    if not history_available:
        return AcquisitionWindow(
            end - timedelta(days=7),
            end,
            "history_unavailable_seven_day_recovery",
        )

    previous_day = _previous_weekday(resolution.target_date)
    start = datetime.combine(previous_day, scheduled_time, zone)
    return AcquisitionWindow(
        start.astimezone(timezone.utc),
        end,
        "first_run_since_previous_scheduled_cutoff",
    )
