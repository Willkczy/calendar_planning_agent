"""Largest available block on the earliest feasible day."""

from src.orchestration.heuristics._engine import schedule


def schedule_min_fragmentation(subtasks, free_slots, break_minutes=0):
    return schedule(subtasks, free_slots, "min_fragmentation", break_minutes)
