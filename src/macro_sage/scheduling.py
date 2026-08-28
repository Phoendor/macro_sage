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

    def as_dict(self) -> dict[str, str | None]:
        value = asdict(self)
        value["target_date"] = self.target_date.isoformat()
        value["requested_date"] = (
            self.requested_date.isoformat() if self.requested_date else None
        )
        value["local_time"] = self.local_time.isoformat()
        value["utc_time"] = self.utc_time.isoformat()
        return value

    @classmethod
    def from_dict(cls, value: dict[str, str | None]) -> DateResolution:
        requested = value.get("requested_date")
        return cls(
            target_date=date.fromisoformat(str(value["target_date"])),
            requested_date=date.fromisoformat(requested) if requested else None,
            rule=str(value["rule"]),
            timezone_name=str(value["timezone_name"]),
            local_time=datetime.fromisoformat(str(value["local_time"])),
            utc_time=datetime.fromisoformat(str(value["utc_time"])),
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

    return DateResolution(
        target_date=target,
        requested_date=requested,
        rule=rule,
        timezone_name=timezone_name,
        local_time=local_now,
        utc_time=utc_now,
    )
