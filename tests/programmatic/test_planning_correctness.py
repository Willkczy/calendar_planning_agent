from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from src.calendar_api.free_slots import compute_free_slots
from src.domain.time import deadline_boundary
from src.orchestration.heuristics._engine import schedule
from src.orchestration.nodes.validate_candidates import validate_candidates_node
from src.validator.constraints import validate_schedule


def test_date_only_deadline_includes_local_deadline_day():
    events = [
        {
            "name": "Task",
            "description": "",
            "start": "2026-10-23T09:00:00-04:00",
            "end": "2026-10-23T10:00:00-04:00",
        }
    ]
    state = {
        "deadline": "2026-10-23",
        "timezone": "America/New_York",
        "work_start": "09:00",
        "work_end": "18:00",
        "busy_blocks": [],
    }
    state.update(
        {
            f"candidate_{s}": events
            for s in ("deadline_first", "min_fragmentation", "energy_aware")
        }
    )
    assert all(
        v["passed"]
        for v in validate_candidates_node(state)["candidate_validations"].values()
    )


@pytest.mark.parametrize(
    "date,offset", [("2026-03-08", "-04:00"), ("2026-11-01", "-05:00")]
)
def test_deadline_uses_zone_rules_across_dst(date, offset):
    assert deadline_boundary(date, "America/New_York").isoformat().endswith(offset)


def test_mixed_offsets_produce_local_free_slots_and_valid_work_hours():
    tz = ZoneInfo("America/New_York")
    busy = [{"start": "2026-10-23T13:00:00+00:00", "end": "2026-10-23T17:30:00+00:00"}]
    slots = compute_free_slots(
        busy,
        datetime(2026, 10, 23, 9, tzinfo=tz),
        datetime(2026, 10, 23, 18, tzinfo=tz),
        time(9),
        time(18),
    )
    assert slots[0]["start"] == "2026-10-23T13:30:00-04:00"
    event = {
        "name": "Work",
        "start": "2026-10-23T17:30:00+00:00",
        "end": "2026-10-23T18:30:00+00:00",
    }
    assert validate_schedule(
        [event],
        busy,
        time(9),
        time(18),
        deadline_boundary("2026-10-23", str(tz)),
        timezone=str(tz),
    )["passed"]


@pytest.mark.parametrize(
    "strategy", ["deadline_first", "min_fragmentation", "energy_aware"]
)
def test_missing_prerequisite_prevents_downstream_placement(strategy):
    tasks = [
        {
            "id": "a",
            "name": "A",
            "description": "",
            "duration_minutes": 90,
            "depends_on": [],
        },
        {
            "id": "b",
            "name": "B",
            "description": "",
            "duration_minutes": 30,
            "depends_on": ["a"],
        },
    ]
    slots = [{"start": "2026-10-26T09:00:00+00:00", "end": "2026-10-26T10:00:00+00:00"}]
    events = schedule(tasks, slots, strategy)
    assert events == []
    result = validate_schedule(
        events,
        [],
        time(9),
        time(18),
        deadline_boundary("2026-10-26", "UTC"),
        subtasks=tasks,
    )
    assert not result["passed"]
    assert len(result["violations"]) == 2


def test_dependency_validation_and_duplicate_names_use_ids():
    tasks = [
        {
            "id": "a",
            "name": "Same",
            "description": "",
            "duration_minutes": 60,
            "depends_on": [],
        },
        {
            "id": "b",
            "name": "Same",
            "description": "",
            "duration_minutes": 30,
            "depends_on": ["a"],
        },
    ]
    events = [
        {
            "task_id": "b",
            "name": "Same",
            "start": "2026-10-26T09:00:00+00:00",
            "end": "2026-10-26T09:30:00+00:00",
        }
    ]
    result = validate_schedule(
        events,
        [],
        time(9),
        time(18),
        deadline_boundary("2026-10-26", "UTC"),
        subtasks=tasks,
    )
    assert {v["violation_type"] for v in result["violations"]} == {
        "UNSCHEDULED",
        "DEPENDENCY",
    }


def test_energy_strategy_considers_boundaries_inside_long_slot():
    tasks = [
        {
            "id": "a",
            "name": "Deep work",
            "description": "",
            "duration_minutes": 60,
            "complexity": "high",
            "depends_on": [],
        }
    ]
    slots = [{"start": "2026-10-26T09:00:00+00:00", "end": "2026-10-26T18:00:00+00:00"}]
    events = schedule(
        tasks,
        slots,
        "energy_aware",
        energy={"morning": "low", "afternoon": "high", "evening": "low"},
    )
    assert events[0]["start"] == "2026-10-26T12:00:00+00:00"


def test_invalid_interval_and_short_break_are_visible():
    events = [
        {
            "name": "A",
            "start": "2026-10-26T09:00:00+00:00",
            "end": "2026-10-26T10:00:00+00:00",
        },
        {
            "name": "B",
            "start": "2026-10-26T10:05:00+00:00",
            "end": "2026-10-26T10:35:00+00:00",
        },
        {"name": "C", "start": "2026-10-26T11:00:00", "end": "2026-10-26T11:00:00"},
    ]
    result = validate_schedule(
        events,
        [],
        time(9),
        time(18),
        deadline_boundary("2026-10-26", "UTC"),
        break_minutes=10,
    )
    assert {v["violation_type"] for v in result["violations"]} == {
        "INVALID_TIME",
        "BREAK_TOO_SHORT",
    }


def test_fall_back_uses_elapsed_minutes_through_repeated_hour():
    zone = ZoneInfo("America/New_York")
    slots = compute_free_slots(
        [],
        datetime(2026, 11, 1, 0, tzinfo=zone),
        datetime(2026, 11, 1, 4, tzinfo=zone),
        time(0),
        time(4),
        workdays=[6],
    )
    tasks = [
        {
            "id": "a",
            "name": "Long focus",
            "description": "",
            "duration_minutes": 180,
            "depends_on": [],
        }
    ]
    events = schedule(tasks, slots, "deadline_first")
    assert events[0]["end"] == "2026-11-01T02:00:00-05:00"
    assert validate_schedule(
        events,
        [],
        time(0),
        time(4),
        deadline_boundary("2026-11-01", str(zone)),
        timezone=str(zone),
        subtasks=tasks,
    )["passed"]


def test_nonexistent_spring_forward_boundary_fails_explicitly():
    zone = ZoneInfo("America/New_York")
    with pytest.raises(ValueError, match="does not exist"):
        compute_free_slots(
            [],
            datetime(2026, 3, 8, 0, tzinfo=zone),
            datetime(2026, 3, 8, 5, tzinfo=zone),
            time(2, 30),
            time(4),
            workdays=[6],
        )


def test_all_day_calendar_timezone_and_free_events(monkeypatch):
    from src.calendar_api.events import fetch_busy_blocks

    class Resource:
        def list(self, **kwargs):
            return self

        def execute(self):
            return {
                "timeZone": "America/New_York",
                "items": [
                    {"start": {"date": "2026-11-01"}, "end": {"date": "2026-11-02"}},
                    {
                        "transparency": "transparent",
                        "start": {"date": "2026-11-03"},
                        "end": {"date": "2026-11-04"},
                    },
                    {
                        "attendees": [{"self": True, "responseStatus": "declined"}],
                        "start": {"date": "2026-11-05"},
                        "end": {"date": "2026-11-06"},
                    },
                ],
            }

    class Service:
        def events(self):
            return Resource()

    monkeypatch.setattr(
        "src.calendar_api.events.build_calendar_service", lambda: Service()
    )
    blocks = fetch_busy_blocks(
        datetime(2026, 11, 1, tzinfo=timezone.utc),
        datetime(2026, 11, 7, tzinfo=timezone.utc),
    )
    assert blocks == [
        {"start": "2026-11-01T00:00:00-04:00", "end": "2026-11-02T00:00:00-05:00"}
    ]
