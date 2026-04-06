# =============================================================================
# tests/test_calendar_api.py — Calendar API module tests
# =============================================================================
# Tests for free-slot computation and mock calendar.
# Real Google Calendar API calls should NOT be tested here — those require
# integration tests with real credentials.
#
# STEPS TO COMPLETE:
# 1. Test compute_free_slots with various busy-block configurations.
# 2. Test mock calendar fetch/create functions.
# 3. Test edge cases: no busy blocks, all-day blocks, weekends.
# =============================================================================

from __future__ import annotations

import datetime

import pytest

from src.calendar_api.free_slots import compute_free_slots


class TestComputeFreeSlots:
    """Test the free-slot computation logic."""

    def test_no_busy_blocks_gives_full_days(self, work_start, work_end):
        """With no busy blocks, every working day should be fully free.

        STEPS:
        1. Call compute_free_slots with empty busy_blocks list.
        2. Set horizon to a 3-day window.
        3. Assert result contains one free slot per working day,
           each spanning work_start to work_end.
        """
        pass  # TODO: implement

    def test_single_busy_block_splits_day(self, work_start, work_end):
        """A single busy block in the middle splits the day into two free slots.

        STEPS:
        1. Provide one busy block from 12:00 to 13:00.
        2. Assert two free slots: 09:00–12:00 and 13:00–18:00.
        """
        pass  # TODO: implement

    def test_overlapping_busy_blocks_merged(self, work_start, work_end):
        """Overlapping busy blocks should be merged before gap computation.

        STEPS:
        1. Provide two overlapping blocks: 10:00–12:00 and 11:00–13:00.
        2. Assert they are treated as one block: 10:00–13:00.
        """
        pass  # TODO: implement

    def test_weekends_excluded_by_default(self, work_start, work_end):
        """Saturday and Sunday should be skipped unless include_weekends=True.

        STEPS:
        1. Set horizon to span a weekend.
        2. Assert no free slots on Saturday/Sunday.
        """
        pass  # TODO: implement

    def test_weekends_included_if_flag_set(self, work_start, work_end):
        """With include_weekends=True, weekend days should produce free slots.

        STEPS:
        1. Same as above but include_weekends=True.
        2. Assert free slots exist on weekend days.
        """
        pass  # TODO: implement

    def test_horizon_clamping(self, work_start, work_end):
        """Free slots should be clamped to the horizon boundaries.

        STEPS:
        1. Set horizon_start to 14:00 today (mid-afternoon).
        2. Assert the first free slot starts at 14:00, not 09:00.
        """
        pass  # TODO: implement


class TestMockCalendar:
    """Test the mock calendar data module."""

    def test_fetch_returns_only_events_in_window(self):
        """mock fetch should filter events outside the time window.

        STEPS:
        1. Call fetch_mock_busy_blocks with a narrow 1-day window.
        2. Assert only events on that day are returned.
        """
        pass  # TODO: implement

    def test_create_mock_event_returns_dict(self):
        """create_mock_event should return a response-like dict.

        STEPS:
        1. Call create_mock_event with sample data.
        2. Assert the returned dict has "id" and "summary" keys.
        """
        pass  # TODO: implement
