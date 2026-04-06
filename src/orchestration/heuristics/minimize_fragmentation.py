# =============================================================================
# src/orchestration/heuristics/minimize_fragmentation.py — Minimise fragmentation
# =============================================================================
# Places subtasks in the LARGEST available time blocks first to avoid
# scattering short sessions across the calendar.
#
# This is a pure function with no LLM or API calls — fully unit-testable.
# =============================================================================

from __future__ import annotations

import datetime
from typing import Any

from src.orchestration.state import Subtask, ProposedEvent


def schedule_min_fragmentation(
    subtasks: list[Subtask],
    free_slots: list[dict[str, str]],
) -> list[ProposedEvent]:
    """Schedule subtasks by placing them in the largest free slots.

    Args:
        subtasks: Ordered list of subtasks from goal decomposition.
        free_slots: Chronologically sorted list of
                    {"start": <ISO>, "end": <ISO>} free-slot dicts.

    Returns:
        List of ProposedEvent dicts.

    ALGORITHM:
    1. Parse all free_slot start/end strings into datetime objects.
    2. Sort free slots by duration DESCENDING (largest first).
    3. Sort subtasks by duration_minutes DESCENDING (longest first).
    4. For each subtask (longest first):
       a. Find the first slot large enough to hold it.
       b. Place the subtask at the START of that slot.
       c. Split the remaining slot time back into the pool.
       d. Re-sort the slot pool by duration descending.
    5. After all subtasks are assigned, re-sort the ProposedEvents
       chronologically (by start time) before returning.

    RATIONALE:
    By pairing the longest subtasks with the largest slots, we minimise
    the number of small leftover fragments in the calendar.

    EDGE CASES:
    - Same as deadline_first: handle unplaceable subtasks gracefully.
    """
    pass  # TODO: implement
