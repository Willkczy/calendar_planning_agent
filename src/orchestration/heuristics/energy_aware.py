# =============================================================================
# src/orchestration/heuristics/energy_aware.py — Energy-aware scheduling
# =============================================================================
# Places cognitively demanding subtasks in MORNING slots and lighter tasks
# in AFTERNOON slots, based on the assumption that morning hours are better
# for deep work.
#
# This is a pure function with no LLM or API calls — fully unit-testable.
# =============================================================================

from __future__ import annotations

import datetime
from typing import Any

from src.orchestration.state import Subtask, ProposedEvent


# Define the boundary between "morning" and "afternoon"
_MORNING_END = datetime.time(12, 0)


def schedule_energy_aware(
    subtasks: list[Subtask],
    free_slots: list[dict[str, str]],
    work_start: str = "09:00",
) -> list[ProposedEvent]:
    """Schedule subtasks with energy-level awareness.

    Args:
        subtasks: Ordered list of subtasks from goal decomposition.
        free_slots: Chronologically sorted list of
                    {"start": <ISO>, "end": <ISO>} free-slot dicts.
        work_start: User's working hours start as "HH:MM".

    Returns:
        List of ProposedEvent dicts.

    ALGORITHM:
    1. Classify subtasks into "heavy" and "light":
       - Heavy: duration_minutes >= 60 (deep-work tasks).
       - Light: duration_minutes < 60 (admin / review tasks).
       (You can refine this heuristic — e.g. also use keywords in the
        name/description to infer cognitive load.)

    2. Split free slots into morning_slots (start < 12:00) and
       afternoon_slots (start >= 12:00).

    3. Schedule heavy subtasks into morning_slots first (earliest first).
       If morning slots run out, spill into afternoon slots.

    4. Schedule light subtasks into afternoon_slots first (earliest first).
       If afternoon slots run out, spill into remaining morning slots.

    5. Handle slot splitting the same way as the other heuristics.

    6. Sort final list chronologically and return.

    EDGE CASES:
    - All slots are in the morning → schedule everything there.
    - All subtasks are heavy → same as deadline_first within mornings.
    """
    pass  # TODO: implement
