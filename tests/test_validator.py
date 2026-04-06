# =============================================================================
# tests/test_validator.py — Deterministic validator tests
# =============================================================================
# The validator is the easiest module to test because it is pure logic.
# Every constraint should have both a passing and failing test.
#
# STEPS TO COMPLETE:
# 1. Test each of the four constraints independently.
# 2. Test combinations of violations.
# 3. Test edge cases.
# =============================================================================

from __future__ import annotations

import datetime

import pytest

from src.validator.constraints import validate_schedule, intervals_overlap


class TestIntervalsOverlap:
    """Unit tests for the intervals_overlap helper."""

    def test_non_overlapping_intervals(self):
        """Two intervals that don't touch should return False.

        STEPS:
        1. A=[09:00, 10:00), B=[11:00, 12:00).
        2. Assert intervals_overlap returns False.
        """
        pass  # TODO: implement

    def test_overlapping_intervals(self):
        """Two intervals that overlap should return True.

        STEPS:
        1. A=[09:00, 11:00), B=[10:00, 12:00).
        2. Assert intervals_overlap returns True.
        """
        pass  # TODO: implement

    def test_adjacent_intervals_do_not_overlap(self):
        """[09:00, 10:00) and [10:00, 11:00) should NOT overlap.

        STEPS:
        1. A=[09:00, 10:00), B=[10:00, 11:00).
        2. Assert intervals_overlap returns False — they are adjacent, not overlapping.
        """
        pass  # TODO: implement

    def test_contained_interval(self):
        """A fully contained within B should overlap.

        STEPS:
        1. A=[10:00, 11:00), B=[09:00, 12:00).
        2. Assert True.
        """
        pass  # TODO: implement


class TestValidateSchedule:
    """Tests for the full validate_schedule function."""

    def test_valid_schedule_passes(
        self, sample_valid_schedule, sample_busy_blocks, work_start, work_end, deadline
    ):
        """A schedule with no violations should return passed=True.

        STEPS:
        1. Call validate_schedule with sample_valid_schedule.
        2. Assert result["passed"] is True.
        3. Assert result["violations"] is empty.
        """
        pass  # TODO: implement

    def test_overlap_with_busy_block(
        self, sample_busy_blocks, work_start, work_end, deadline
    ):
        """An event that overlaps a busy block should produce an OVERLAP violation.

        STEPS:
        1. Create a schedule with one event overlapping sample_busy_blocks[0].
        2. Call validate_schedule.
        3. Assert one violation with type "OVERLAP".
        """
        pass  # TODO: implement

    def test_self_overlap_detected(
        self, sample_busy_blocks, work_start, work_end, deadline
    ):
        """Two proposed events overlapping each other → SELF_OVERLAP.

        STEPS:
        1. Create two events with overlapping time ranges.
        2. Assert a SELF_OVERLAP violation.
        """
        pass  # TODO: implement

    def test_out_of_hours_detected(
        self, sample_busy_blocks, work_start, work_end, deadline
    ):
        """An event outside working hours → OUT_OF_HOURS.

        STEPS:
        1. Create an event starting at 07:00 (before work_start).
        2. Assert an OUT_OF_HOURS violation.
        """
        pass  # TODO: implement

    def test_deadline_exceeded(
        self, sample_busy_blocks, work_start, work_end, deadline
    ):
        """An event ending after the deadline → DEADLINE_EXCEEDED.

        STEPS:
        1. Create an event ending 1 hour after deadline.
        2. Assert a DEADLINE_EXCEEDED violation.
        """
        pass  # TODO: implement

    def test_multiple_violations(self, sample_invalid_schedule, sample_busy_blocks, work_start, work_end, deadline):
        """A schedule with multiple issues should report all of them.

        STEPS:
        1. Use sample_invalid_schedule fixture.
        2. Assert result["passed"] is False.
        3. Assert len(result["violations"]) >= 3.
        """
        pass  # TODO: implement

    def test_empty_schedule_passes(
        self, sample_busy_blocks, work_start, work_end, deadline
    ):
        """An empty schedule has no violations.

        STEPS:
        1. Call validate_schedule with an empty list.
        2. Assert passed is True.
        """
        pass  # TODO: implement
