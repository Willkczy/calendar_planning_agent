"""Earliest-fit strategy, sharing the pure scheduling engine."""

from src.orchestration.heuristics._engine import schedule


def schedule_deadline_first(subtasks, free_slots, break_minutes=0):
    return schedule(subtasks, free_slots, "deadline_first", break_minutes)
