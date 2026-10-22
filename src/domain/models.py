"""Validated API and storage contracts. Domain algorithms consume plain dicts."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.domain.tasks import validate_dag

Strategy = Literal["deadline_first", "min_fragmentation", "energy_aware"]
Level = Literal["low", "medium", "high"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Task(Contract):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    duration_minutes: int = Field(gt=0, le=480, strict=True)
    complexity: Level = "medium"
    depends_on: list[str] = Field(default_factory=list, max_length=100)


class Preferences(Contract):
    deadline: date
    timezone: str = "America/New_York"
    work_start: str = "09:00"
    work_end: str = "18:00"
    workdays: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4], min_length=1, max_length=7
    )
    max_session_minutes: int = Field(default=120, ge=15, le=480)
    break_minutes: int = Field(default=10, ge=0, le=120)
    energy_levels: dict[str, Level] = Field(
        default_factory=lambda: {
            "morning": "high",
            "afternoon": "medium",
            "evening": "low",
        }
    )

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Use a valid IANA timezone") from exc
        return value

    @model_validator(mode="after")
    def valid_windows(self):
        start, end = (
            time.fromisoformat(self.work_start),
            time.fromisoformat(self.work_end),
        )
        if start.tzinfo or end.tzinfo or start >= end:
            raise ValueError("Working hours must start and end on the same local day")
        self.work_start, self.work_end = start.strftime("%H:%M"), end.strftime("%H:%M")
        if any(day not in range(7) for day in self.workdays) or len(
            set(self.workdays)
        ) != len(self.workdays):
            raise ValueError("Workdays must be distinct weekdays (Monday=0)")
        if set(self.energy_levels) != {"morning", "afternoon", "evening"}:
            raise ValueError("Energy levels need morning, afternoon and evening")
        return self


class CreatePlan(Contract):
    goal: str = Field(min_length=3, max_length=2000)
    context: str = Field(default="", max_length=4000)
    preferences: Preferences


class DraftUpdate(Contract):
    revision: int = Field(ge=1)
    tasks: list[Task] = Field(min_length=1, max_length=100)
    preferences: Preferences

    @model_validator(mode="after")
    def valid_tasks(self):
        validate_dag([task.model_dump() for task in self.tasks])
        return self


class RevisionRequest(Contract):
    revision: int = Field(ge=1)


class ApprovalRequest(RevisionRequest):
    candidate_id: Strategy
    snapshot_hash: str = Field(min_length=64, max_length=64)
    acknowledged_violation_ids: list[str] = Field(default_factory=list)


class Candidate(Contract):
    id: Strategy
    events: list[dict]
    unscheduled: list[dict]
    validation: dict
    metrics: dict
    explanation: str
    explanation_source: Literal["rules"] = "rules"
    snapshot_hash: str


class Plan(Contract):
    id: str
    revision: int = 1
    goal: str
    context: str
    preferences: Preferences
    calendar_mode: Literal["mock", "live"]
    calendar_id: str
    status: Literal[
        "draft", "review", "needs_review", "writing", "partial", "completed", "rejected"
    ] = "draft"
    tasks: list[Task] = Field(default_factory=list)
    candidates: list[Candidate] = Field(default_factory=list)
    busy_blocks: list[dict] = Field(default_factory=list)
    calendar_snapshot_at: str | None = None
    selected_candidate: Strategy | None = None
    approval: dict | None = None
    write_results: list[dict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
