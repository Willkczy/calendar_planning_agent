"""One definition of deadline and timezone semantics across the application."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def aware(value: str | datetime, tz: str | ZoneInfo = "UTC") -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    zone = ZoneInfo(tz) if isinstance(tz, str) else tz
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must include a UTC offset")
    return parsed.astimezone(zone)


def deadline_boundary(value: str | date, tz: str) -> datetime:
    """A date includes the whole local day; a timestamp is an exact boundary."""
    zone = ZoneInfo(tz)
    if isinstance(value, datetime):
        return aware(value, zone)
    raw = str(value)
    if len(raw) == 10:
        return datetime.combine(
            date.fromisoformat(raw) + timedelta(days=1), time.min, zone
        )
    return aware(raw, zone)


def elapsed_minutes(start: datetime, end: datetime) -> float:
    return (
        end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
    ).total_seconds() / 60
