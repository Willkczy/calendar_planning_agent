# =============================================================================
# src/orchestration/state.py — LangGraph state definition
# =============================================================================
# Defines the TypedDict that flows through every node of the graph.  Every
# field is documented so implementers know exactly what each node reads and
# writes.
#
# STEPS TO COMPLETE:
# 1. Review the fields below.  Add or adjust types as needed when you
#    implement individual nodes.
# =============================================================================

from __future__ import annotations

import datetime
from typing import Any, TypedDict


class Subtask(TypedDict):
    """A single subtask produced by goal decomposition."""
    name: str                   # Short title, e.g. "Set up React dev environment"
    description: str            # 1–2 sentence description of the work
    duration_minutes: int       # Estimated duration in minutes


class ProposedEvent(TypedDict):
    """A scheduled calendar event proposed by a heuristic."""
    name: str                   # Subtask name
    description: str            # Subtask description
    start: str                  # ISO 8601 datetime string
    end: str                    # ISO 8601 datetime string


class Violation(TypedDict):
    """A single constraint violation found by the validator."""
    event_name: str             # Which event is in violation
    violation_type: str         # "OVERLAP" | "SELF_OVERLAP" | "OUT_OF_HOURS" | "DEADLINE_EXCEEDED"
    description: str            # Human-readable description


class ValidationResult(TypedDict):
    """Output of the deterministic validator."""
    passed: bool
    violations: list[Violation]


class AgentState(TypedDict, total=False):
    """Full state carried through the LangGraph directed graph.

    Fields are populated progressively by different nodes.
    'total=False' means fields are optional — nodes only set what they own.
    """

    # --- User inputs (set once at the start) ---
    goal: str
    deadline: str                               # ISO date string
    context: str
    work_start: str                             # "HH:MM"
    work_end: str                               # "HH:MM"
    max_session_minutes: int

    # --- Calendar data (set by fetch_events node) ---
    busy_blocks: list[dict[str, str]]           # [{"start": ..., "end": ...}]
    free_slots: list[dict[str, str]]            # [{"start": ..., "end": ...}]

    # --- Goal decomposition (set by decompose_goal node) ---
    subtasks: list[Subtask]

    # --- Candidate schedules (set by the three heuristic branches) ---
    candidate_deadline_first: list[ProposedEvent]
    candidate_min_fragmentation: list[ProposedEvent]
    candidate_energy_aware: list[ProposedEvent]

    # --- Scoring (set by score_candidates node) ---
    selected_candidate: list[ProposedEvent]
    candidate_scores: dict[str, int]            # heuristic_name → violation count

    # --- Validation & repair (set by validator / repair loop) ---
    validation_result: ValidationResult
    repair_iteration: int
    repair_history: list[ValidationResult]      # for debugging

    # --- Final output (set by rationale & proposal nodes) ---
    final_schedule: list[ProposedEvent]
    rationale: str

    # --- Human approval (set by approval node / frontend) ---
    user_approved: bool | None                  # None = awaiting decision

    # --- Write result ---
    write_results: list[dict[str, Any]]         # API responses from event creation
