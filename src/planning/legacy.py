"""Compatibility for research graph proposals; approval uses the same ledger."""

from collections import defaultdict, deque
from datetime import datetime, timezone
import os
from pathlib import Path

from config.settings import settings
from src.domain.models import ApprovalRequest, Plan, Preferences, Task
from src.domain.tasks import clean_description, normalize_tasks
from src.planning.service import PlanningService
from src.planning.store import PlanStore


def approve_graph_proposal(state):
    if state.get("user_approved") is not True or not state.get("plan_id"):
        raise ValueError(
            "Calendar writes require an approved plan with a stable plan_id"
        )
    service = PlanningService(
        PlanStore(
            os.getenv(
                "PLANNER_DB_PATH",
                str(Path(__file__).resolve().parents[2] / ".data/planner.sqlite3"),
            )
        )
    )
    strategy = state["selected_strategy"]
    with service.store.lock(state["plan_id"]):
        try:
            plan = service.get(state["plan_id"])
        except KeyError:
            tasks = [
                Task.model_validate(
                    {**task, "description": clean_description(task["description"])}
                )
                for task in normalize_tasks(state["subtasks"])
            ]
            now = datetime.now(timezone.utc)
            plan = Plan(
                id=state["plan_id"],
                goal=state["goal"],
                context=state.get("context", ""),
                tasks=tasks,
                preferences=Preferences(
                    deadline=state["deadline"][:10],
                    timezone=state.get("timezone", settings.APP_TIMEZONE),
                    work_start=state["work_start"],
                    work_end=state["work_end"],
                    max_session_minutes=state["max_session_minutes"],
                    break_minutes=state.get("break_minutes", 0),
                    energy_levels=state["energy_levels"],
                ),
                calendar_mode=settings.CALENDAR_MODE,
                calendar_id=settings.GOOGLE_CALENDAR_ID,
                created_at=now,
                updated_at=now,
                status="review",
            )
            names = defaultdict(deque)
            for task in tasks:
                names[task.name].append(task.id)
            events = []
            for event in state["final_schedule"]:
                task_id = event.get("task_id") or names[event["name"]].popleft()
                events.append(
                    {**event, "id": f"{task_id}-1", "task_id": task_id, "segment_id": 1}
                )
            validation = service.validate(plan, events, state.get("busy_blocks", []))
            plan.candidates = [service.candidate(plan, strategy, events, validation)]
            service.save(plan)
    candidate = next(c for c in plan.candidates if c.id == strategy)
    return service.approve(
        plan.id,
        ApprovalRequest(
            revision=plan.revision,
            candidate_id=strategy,
            snapshot_hash=candidate.snapshot_hash,
            acknowledged_violation_ids=state.get("acknowledged_violation_ids", []),
        ),
    )
