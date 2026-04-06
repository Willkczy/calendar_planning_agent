# =============================================================================
# tests/conftest.py — Shared pytest fixtures
# =============================================================================
# Provides reusable test data and mock objects used across all test files.
#
# STEPS TO COMPLETE:
# 1. Add more fixtures as you implement each module's tests.
# =============================================================================

from __future__ import annotations

import datetime
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Sample busy blocks matching mock_calendar.py's data
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_busy_blocks() -> list[dict[str, str]]:
    """A small set of busy blocks for testing free-slot computation."""
    return [
        {"start": "2026-04-06T09:30:00+00:00", "end": "2026-04-06T10:00:00+00:00"},
        {"start": "2026-04-06T14:00:00+00:00", "end": "2026-04-06T15:30:00+00:00"},
        {"start": "2026-04-07T11:00:00+00:00", "end": "2026-04-07T11:30:00+00:00"},
    ]


# ---------------------------------------------------------------------------
# Sample free slots (expected output for the busy blocks above)
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_free_slots() -> list[dict[str, str]]:
    """Free slots computed from sample_busy_blocks with 09:00–18:00 hours."""
    return [
        {"start": "2026-04-06T09:00:00+00:00", "end": "2026-04-06T09:30:00+00:00"},
        {"start": "2026-04-06T10:00:00+00:00", "end": "2026-04-06T14:00:00+00:00"},
        {"start": "2026-04-06T15:30:00+00:00", "end": "2026-04-06T18:00:00+00:00"},
        {"start": "2026-04-07T09:00:00+00:00", "end": "2026-04-07T11:00:00+00:00"},
        {"start": "2026-04-07T11:30:00+00:00", "end": "2026-04-07T18:00:00+00:00"},
    ]


# ---------------------------------------------------------------------------
# Sample subtasks from goal decomposition
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_subtasks() -> list[dict[str, Any]]:
    """Example subtasks for a 'Learn React basics' goal."""
    return [
        {"name": "Set up dev environment",     "description": "Install Node.js, create React app", "duration_minutes": 30},
        {"name": "Read React docs intro",      "description": "Official React documentation",       "duration_minutes": 60},
        {"name": "Build a counter component",  "description": "Hands-on practice with state",       "duration_minutes": 90},
        {"name": "Learn about hooks",          "description": "useState, useEffect patterns",       "duration_minutes": 60},
        {"name": "Build a todo app",           "description": "Mini-project combining concepts",    "duration_minutes": 90},
    ]


# ---------------------------------------------------------------------------
# Working hours and deadline
# ---------------------------------------------------------------------------
@pytest.fixture
def work_start() -> datetime.time:
    return datetime.time(9, 0)


@pytest.fixture
def work_end() -> datetime.time:
    return datetime.time(18, 0)


@pytest.fixture
def deadline() -> datetime.datetime:
    return datetime.datetime(2026, 4, 17, 18, 0, tzinfo=datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Sample proposed schedule (valid, no violations)
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_valid_schedule() -> list[dict[str, str]]:
    """A schedule with no constraint violations."""
    return [
        {"name": "Set up dev environment",  "description": "Install Node.js", "start": "2026-04-06T10:00:00+00:00", "end": "2026-04-06T10:30:00+00:00"},
        {"name": "Read React docs intro",   "description": "Official docs",   "start": "2026-04-06T10:30:00+00:00", "end": "2026-04-06T11:30:00+00:00"},
        {"name": "Build counter component", "description": "Hands-on",        "start": "2026-04-07T09:00:00+00:00", "end": "2026-04-07T10:30:00+00:00"},
    ]


# ---------------------------------------------------------------------------
# Sample proposed schedule WITH violations
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_invalid_schedule() -> list[dict[str, str]]:
    """A schedule with intentional violations for testing the validator."""
    return [
        # Overlaps with the 09:30–10:00 busy block
        {"name": "Task A", "description": "...", "start": "2026-04-06T09:00:00+00:00", "end": "2026-04-06T10:00:00+00:00"},
        # Starts before working hours
        {"name": "Task B", "description": "...", "start": "2026-04-07T07:00:00+00:00", "end": "2026-04-07T08:00:00+00:00"},
        # Ends after the deadline
        {"name": "Task C", "description": "...", "start": "2026-04-17T17:00:00+00:00", "end": "2026-04-17T19:00:00+00:00"},
    ]
