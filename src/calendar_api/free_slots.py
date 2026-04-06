# =============================================================================
# src/calendar_api/free_slots.py — Free-slot computation
# =============================================================================
# Given a list of busy blocks and the user's working-hour preferences,
# computes available time slots that the scheduler can use.
#
# This module is pure logic with no API calls — fully unit-testable.
#
# STEPS TO COMPLETE:
# 1. Implement compute_free_slots().
# 2. Implement _day_working_window() helper.
# =============================================================================

from __future__ import annotations

import datetime
from typing import Any


def compute_free_slots(
    busy_blocks: list[dict[str, str]],
    horizon_start: datetime.datetime,
    horizon_end: datetime.datetime,
    work_start: datetime.time,
    work_end: datetime.time,
    include_weekends: bool = False,
) -> list[dict[str, str]]:
    """Compute free time slots between busy blocks within working hours.

    Args:
        busy_blocks: Sorted list of {"start": <ISO>, "end": <ISO>} dicts.
        horizon_start: Earliest datetime to consider (now).
        horizon_end: Latest datetime to consider (deadline).
        work_start: Daily working hours start (e.g. 09:00).
        work_end: Daily working hours end (e.g. 18:00).
        include_weekends: If False, skip Saturday (5) and Sunday (6).

    Returns:
        List of {"start": <ISO>, "end": <ISO>} free-slot dicts, sorted
        chronologically.

    STEPS:
    1. Generate a list of working-day dates from horizon_start.date()
       to horizon_end.date() (inclusive).
       a. Skip weekends unless include_weekends is True.
    2. For each working day, compute the working window:
       a. day_start = datetime.combine(day, work_start, tzinfo=...)
       b. day_end   = datetime.combine(day, work_end,   tzinfo=...)
       c. Clamp day_start to max(day_start, horizon_start).
       d. Clamp day_end   to min(day_end,   horizon_end).
       e. If day_start >= day_end, skip this day.
    3. Collect all busy blocks that overlap with this day's window.
       a. Merge overlapping busy blocks to avoid double-counting.
    4. Walk through the day window:
       a. current_time = day_start
       b. For each busy block in this day (sorted):
          - If busy.start > current_time → gap found → append free slot.
          - Advance current_time = max(current_time, busy.end).
       c. After all busy blocks, if current_time < day_end → final gap.
    5. Return the full list of free slots across all days.
    """
    pass  # TODO: implement


def _day_working_window(
    day: datetime.date,
    work_start: datetime.time,
    work_end: datetime.time,
    tz: datetime.tzinfo | None = None,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Return the (start_dt, end_dt) working window for a single day.

    STEPS:
    1. Combine day + work_start + tz → start_dt.
    2. Combine day + work_end   + tz → end_dt.
    3. Return (start_dt, end_dt).
    """
    pass  # TODO: implement
