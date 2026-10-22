"""Deterministic schedule validation. No LLM, API, storage or repair side effects."""

from __future__ import annotations

import datetime
import hashlib
from collections import defaultdict, deque
from zoneinfo import ZoneInfo

from src.domain.tasks import normalize_tasks
from src.domain.time import elapsed_minutes


def intervals_overlap(start_a, end_a, start_b, end_b) -> bool:
    utc = datetime.timezone.utc
    return start_a.astimezone(utc) < end_b.astimezone(utc) and start_b.astimezone(
        utc
    ) < end_a.astimezone(utc)


def validate_schedule(
    schedule,
    busy_blocks,
    work_start,
    work_end,
    deadline,
    *,
    timezone: str | None = None,
    subtasks: list[dict] | None = None,
    max_session_minutes: int | None = None,
    break_minutes: int = 0,
    workdays: list[int] | None = None,
    not_before=None,
) -> dict:
    zone = ZoneInfo(timezone) if timezone else deadline.tzinfo
    if zone is None or deadline.tzinfo is None:
        raise ValueError("Validation requires an explicit timezone")
    violations, parsed = [], []

    def add(event, kind, description):
        identity = event.get("task_id", event.get("id", event["name"]))
        key = hashlib.sha256(f"{identity}:{kind}:{description}".encode()).hexdigest()[
            :20
        ]
        violations.append(
            {
                "id": key,
                "task_id": event.get("task_id"),
                "event_name": event["name"],
                "violation_type": kind,
                "description": description,
            }
        )

    for event in schedule:
        try:
            start, end = (
                datetime.datetime.fromisoformat(event[k]) for k in ("start", "end")
            )
            if start.tzinfo is None or end.tzinfo is None or start >= end:
                raise ValueError("invalid interval")
            start, end = start.astimezone(zone), end.astimezone(zone)
        except (ValueError, TypeError, KeyError):
            add(
                event,
                "INVALID_TIME",
                "Event must have aware timestamps and a positive duration",
            )
            continue
        parsed.append(
            (
                event,
                start.astimezone(datetime.timezone.utc),
                end.astimezone(datetime.timezone.utc),
            )
        )
        if (
            start.date() != end.date()
            or start.time() < work_start
            or end.time() > work_end
        ):
            add(
                event,
                "OUT_OF_HOURS",
                f"Event is outside working hours ({work_start}-{work_end})",
            )
        if workdays is not None and start.weekday() not in workdays:
            add(event, "NON_WORKDAY", "Event falls on a non-working day")
        if end > deadline:
            add(
                event,
                "DEADLINE_EXCEEDED",
                f"Event ends after deadline {deadline.isoformat()}",
            )
        if not_before is not None and start < not_before:
            add(event, "IN_PAST", "Event starts before the latest calendar check")
        if (
            max_session_minutes is not None
            and elapsed_minutes(start, end) > max_session_minutes
        ):
            add(
                event,
                "SESSION_TOO_LONG",
                f"Session exceeds {max_session_minutes} minutes",
            )

    busy = []
    for block in busy_blocks:
        a, b = (datetime.datetime.fromisoformat(block[k]) for k in ("start", "end"))
        if a.tzinfo is None or b.tzinfo is None or a >= b:
            raise ValueError("Invalid busy interval; cannot safely validate calendar")
        busy.append((a, b))
    parsed.sort(key=lambda item: item[1])
    for i, (event, start, end) in enumerate(parsed):
        for a, b in busy:
            if intervals_overlap(start, end, a, b):
                add(
                    event,
                    "OVERLAP",
                    f"Overlaps an existing event from {a.isoformat()} to {b.isoformat()}",
                )
        for other, a, b in parsed[i + 1 :]:
            if intervals_overlap(start, end, a, b):
                add(event, "SELF_OVERLAP", f"Overlaps proposed task {other['name']}")
        if (
            i
            and break_minutes
            and not intervals_overlap(start, end, parsed[i - 1][1], parsed[i - 1][2])
        ):
            if elapsed_minutes(parsed[i - 1][2], start) < break_minutes:
                add(
                    event,
                    "BREAK_TOO_SHORT",
                    f"Less than {break_minutes} minutes between sessions",
                )

    if subtasks is not None:
        tasks = normalize_tasks(subtasks)
        by_id = {task["id"]: task for task in tasks}
        by_name = defaultdict(deque)
        for task in tasks:
            by_name[task["name"]].append(task["id"])
        assigned = defaultdict(list)
        for event, start, end in parsed:
            task_id = event.get("task_id")
            if task_id is None and by_name[event["name"]]:
                task_id = by_name[event["name"]].popleft()
            if task_id not in by_id:
                add(event, "UNKNOWN_TASK", "Event does not match a task in this plan")
                continue
            assigned[task_id].append((event, start, end))
        for task in tasks:
            placeholder = {"name": task["name"], "task_id": task["id"]}
            entries = assigned[task["id"]]
            if not entries:
                add(
                    placeholder,
                    "UNSCHEDULED",
                    "Task could not be placed within the available time",
                )
                continue
            if len(entries) > 1:
                add(
                    placeholder,
                    "DUPLICATE_TASK",
                    "Task has more than one scheduled session",
                )
            if (
                abs(
                    sum(elapsed_minutes(a, b) for _, a, b in entries)
                    - task["duration_minutes"]
                )
                > 0.01
            ):
                add(
                    placeholder,
                    "DURATION_MISMATCH",
                    "Scheduled duration does not match the task estimate",
                )
            for dep in task["depends_on"]:
                if not assigned[dep] or max(b for _, _, b in assigned[dep]) > min(
                    a for _, a, _ in entries
                ):
                    add(
                        placeholder,
                        "DEPENDENCY",
                        f"Prerequisite {by_id[dep]['name']} is missing or ends too late",
                    )
    return {"passed": not violations, "violations": violations}
