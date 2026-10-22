"""Earliest-day energy matching, including boundaries inside a free slot."""

from src.orchestration.heuristics._engine import schedule, period


def _classify_slot_by_time(slot_start):
    return period(slot_start)


def schedule_energy_aware(
    subtasks, free_slots, user_energy_levels=None, work_start="09:00", break_minutes=0
):
    return schedule(
        subtasks, free_slots, "energy_aware", break_minutes, user_energy_levels
    )
