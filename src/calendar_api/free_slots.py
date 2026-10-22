"""Pure free-slot calculation: local working days, absolute interval arithmetic."""

from __future__ import annotations

import datetime

UTC = datetime.timezone.utc


def compute_free_slots(
    busy_blocks,
    horizon_start,
    horizon_end,
    work_start,
    work_end,
    include_weekends=False,
    workdays=None,
):
    if horizon_start.tzinfo is None or horizon_end.tzinfo is None:
        raise ValueError("Planning horizon must include a timezone")
    zone = horizon_start.tzinfo
    horizon_end = horizon_end.astimezone(zone)
    lower, upper = horizon_start.astimezone(UTC), horizon_end.astimezone(UTC)
    if lower >= upper:
        return []
    if work_start >= work_end:
        raise ValueError("Working hours must start before they end on the same day")
    busy = []
    for block in busy_blocks:
        a, b = (datetime.datetime.fromisoformat(block[key]) for key in ("start", "end"))
        if a.tzinfo is None or b.tzinfo is None or a >= b:
            raise ValueError("Invalid calendar busy interval")
        a, b = max(a.astimezone(UTC), lower), min(b.astimezone(UTC), upper)
        if a < b:
            busy.append((a, b))
    busy.sort()
    merged = []
    for a, b in busy:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    result = []

    def append(start, end):
        slot = {
            "start": start.astimezone(zone).isoformat(),
            "end": end.astimezone(zone).isoformat(),
        }
        if hasattr(zone, "key"):
            slot["timezone"] = zone.key
        result.append(slot)

    day = horizon_start.date()
    allowed = (
        set(workdays)
        if workdays is not None
        else set(range(7 if include_weekends else 5))
    )
    while day <= horizon_end.date():
        if day.weekday() in allowed:
            a, b = _day_working_window(day, work_start, work_end, zone)
            a, b = max(a.astimezone(UTC), lower), min(b.astimezone(UTC), upper)
            cursor = a
            for busy_start, busy_end in merged:
                if busy_end <= cursor or busy_start >= b:
                    continue
                if busy_start > cursor:
                    append(cursor, min(busy_start, b))
                cursor = max(cursor, busy_end)
            if cursor < b:
                append(cursor, b)
        day += datetime.timedelta(days=1)
    return result


def _day_working_window(day, work_start, work_end, tz=None):
    bounds = tuple(
        datetime.datetime.combine(day, t, tzinfo=tz) for t in (work_start, work_end)
    )
    for value in bounds:
        if tz and value.astimezone(UTC).astimezone(tz).replace(
            tzinfo=None
        ) != value.replace(tzinfo=None):
            raise ValueError(
                "Working-hours boundary does not exist on this daylight-saving date"
            )
    return bounds
