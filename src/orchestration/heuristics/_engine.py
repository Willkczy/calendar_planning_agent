"""Shared, deterministic greedy scheduler. No I/O and no automatic repair loop."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from src.domain.tasks import normalize_tasks
from src.domain.time import elapsed_minutes
from src.orchestration.heuristics._structural import (
    COMPLEXITY_SCORE,
    complexity_score,
    has_any_structural_tags,
    safe_structural_shuffle,
)


def period(start: datetime) -> str:
    return (
        "morning" if start.hour < 12 else "afternoon" if start.hour < 17 else "evening"
    )


def energy_mismatch(
    start: datetime, end: datetime, complexity: int, energy: dict
) -> float:
    boundaries = [start, end]
    for hour in (12, 17):
        boundary = datetime.combine(start.date(), time(hour), start.tzinfo)
        if start.timestamp() < boundary.timestamp() < end.timestamp():
            boundaries.append(boundary)
    boundaries.sort(key=lambda value: value.timestamp())
    weighted = sum(
        elapsed_minutes(a, b)
        * abs(COMPLEXITY_SCORE.get(energy.get(period(a)), 2) - complexity)
        for a, b in zip(boundaries, boundaries[1:])
    )
    return weighted / max(elapsed_minutes(start, end), 1)


def schedule(
    tasks: list[dict],
    slots: list[dict],
    strategy: str,
    break_minutes: int = 0,
    energy: dict | None = None,
    max_session_minutes: int | None = None,
) -> list[dict]:
    energy = energy or {"morning": "high", "afternoon": "medium", "evening": "low"}
    structural = has_any_structural_tags(tasks)
    typed = any("depends_on" in task for task in tasks)
    identity = any("id" in task for task in tasks)
    normalized = normalize_tasks(tasks)
    priority = (
        complexity_score
        if strategy == "energy_aware"
        else lambda task: task["duration_minutes"]
    )
    if structural:
        normalized = safe_structural_shuffle(normalized, priority)
    elif typed and strategy != "deadline_first":
        normalized.sort(key=priority, reverse=True)

    zone_name = next((slot["timezone"] for slot in slots if slot.get("timezone")), None)
    zone = ZoneInfo(zone_name) if zone_name else None

    def parse(value):
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(zone) if zone and parsed.tzinfo else parsed

    pool = sorted(
        ((parse(s["start"]), parse(s["end"])) for s in slots),
        key=lambda pair: pair[0].timestamp(),
    )
    if any(a.tzinfo is None or b.tzinfo is None for a, b in pool):
        raise ValueError("Free slots must have UTC offsets")
    events, done, failed = [], set(), set()
    cursor = None
    pending = list(normalized)
    while pending:
        # A failed prerequisite prevents its dependants from being scheduled.
        blocked = [task for task in pending if set(task["depends_on"]) & failed]
        for task in blocked:
            failed.add(task["id"])
            pending.remove(task)
        ready = next(
            (task for task in pending if set(task["depends_on"]) <= done), None
        )
        if ready is None:
            break
        pending.remove(ready)
        minutes = ready["duration_minutes"]
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("Task duration must be a positive integer")
        if max_session_minutes is not None and minutes > max_session_minutes:
            failed.add(ready["id"])
            continue
        options = []
        for index, (start, end) in enumerate(pool):
            earliest = (
                max(start, cursor, key=lambda t: t.timestamp()) if cursor else start
            )
            starts = [earliest]
            if strategy == "energy_aware":
                starts += [
                    datetime.combine(start.date(), time(h), start.tzinfo)
                    for h in (12, 17)
                ]
            for candidate in starts:
                finish = (
                    candidate.astimezone(timezone.utc) + timedelta(minutes=minutes)
                ).astimezone(candidate.tzinfo)
                if (
                    candidate.timestamp() < earliest.timestamp()
                    or finish.timestamp() > end.timestamp()
                ):
                    continue
                if strategy == "energy_aware":
                    preference = energy_mismatch(
                        candidate, finish, complexity_score(ready), energy
                    )
                elif strategy == "min_fragmentation" and (structural or typed):
                    preference = -elapsed_minutes(candidate, end)
                else:
                    preference = 0
                options.append(
                    (
                        (candidate.date(), preference, candidate.timestamp()),
                        index,
                        candidate,
                        finish,
                    )
                )
        if not options:
            failed.add(ready["id"])
            continue
        _, index, start, end = min(options)
        slot_start, slot_end = pool.pop(index)
        event = {
            "name": ready["name"],
            "description": ready["description"],
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        if identity:
            event.update(id=f"{ready['id']}-1", task_id=ready["id"], segment_id=1)
        events.append(event)
        done.add(ready["id"])
        cursor = (
            end.astimezone(timezone.utc) + timedelta(minutes=max(0, break_minutes))
        ).astimezone(end.tzinfo)
        if slot_start.timestamp() < start.timestamp():
            pool.append((slot_start, start))
        if end.timestamp() < slot_end.timestamp():
            pool.append((end, slot_end))
        pool.sort(key=lambda pair: pair[0].timestamp())
    return events
