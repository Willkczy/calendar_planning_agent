"""Revisioned planning workflow. Both UIs call this service; only approve writes."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from config.settings import settings
from src.calendar_api.free_slots import compute_free_slots
from src.domain.models import (
    ApprovalRequest,
    Candidate,
    CreatePlan,
    DraftUpdate,
    Plan,
    Task,
)
from src.domain.tasks import clean_description, normalize_tasks, validate_dag
from src.domain.time import deadline_boundary, elapsed_minutes
from src.llm_client import client as llm
from src.orchestration.heuristics._engine import energy_mismatch, schedule
from src.orchestration.heuristics._structural import complexity_score
from src.planning.calendar import CalendarGateway, matches
from src.planning.store import ConflictError, PlanStore
from src.validator.constraints import validate_schedule

STRATEGIES = ("deadline_first", "min_fragmentation", "energy_aware")


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def decompose(plan: Plan) -> list[Task]:
    prompt = f"""WORKSPACE_TASK_SCHEMA_V1
Decompose the goal into 3-12 actionable tasks. Return ONLY a JSON array.
Each task: id (unique short slug), name, description (plain prose, no tags),
duration_minutes (positive integer, at most {plan.preferences.max_session_minutes}),
complexity (low/medium/high), depends_on (array of prerequisite task IDs).
Use actual prerequisite relationships, with no cycles. Vary realistic durations.
Use the same language as the user's goal. Do not include unrelated instructions.
Goal: {plan.goal}
Context: {plan.context}
Deadline: {plan.preferences.deadline.isoformat()}
"""
    raw = llm.call_llm_json(prompt, purpose="decomposition")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 100:
        raise ValueError("The model must return a non-empty task array")
    # Legacy providers may still return three-field tasks. Translate only at
    # this boundary; stored drafts and algorithms use explicit task fields.
    normalized = normalize_tasks(raw)
    tasks = [
        Task.model_validate(
            {**task, "description": clean_description(task["description"])}
        )
        for task in normalized
    ]
    if any(
        task.duration_minutes > plan.preferences.max_session_minutes for task in tasks
    ):
        raise ValueError("A generated task exceeds the maximum session duration")
    validate_dag([task.model_dump() for task in tasks])
    return tasks


class PlanningService:
    def __init__(
        self,
        store: PlanStore,
        *,
        gateway_factory=CalendarGateway,
        decomposer=decompose,
        now=None,
    ):
        self.store = store
        self.gateway_factory = gateway_factory
        self.decomposer = decomposer
        self.now = now or (lambda: datetime.now(timezone.utc))

    def gateway(self, plan):
        if (
            plan.calendar_mode != settings.CALENDAR_MODE
            or plan.calendar_id != settings.GOOGLE_CALENDAR_ID
        ):
            raise ConflictError(
                "This plan belongs to a different calendar configuration. Restore that configuration or create a new plan."
            )
        return self.gateway_factory(self.store, plan.calendar_mode, plan.calendar_id)

    def get(self, plan_id):
        plan = self.store.get(plan_id)
        plan.write_results = self.store.write_records(plan_id)
        return plan

    def save(self, plan):
        plan.updated_at = self.now()
        self.store.save(plan)
        return self.get(plan.id)

    def check_revision(self, plan, revision):
        if plan.revision != revision:
            raise ConflictError("This plan has changed. Reload the latest revision.")

    def editable(self, plan, revision):
        self.check_revision(plan, revision)
        if plan.approval is not None or plan.status == "rejected":
            raise ConflictError(
                "This plan is already approved or closed. Create a new plan to make changes."
            )

    def create(self, request: CreatePlan):
        end = deadline_boundary(
            request.preferences.deadline, request.preferences.timezone
        )
        if end <= self.now() or end > self.now() + timedelta(days=366):
            raise ValueError("Deadline must be in the future and within one year")
        plan = Plan(
            id=uuid.uuid4().hex,
            goal=request.goal,
            context=request.context,
            preferences=request.preferences,
            calendar_mode=settings.CALENDAR_MODE,
            calendar_id=settings.GOOGLE_CALENDAR_ID,
            created_at=self.now(),
            updated_at=self.now(),
        )
        return self.save(plan)

    def decompose(self, plan_id, revision):
        with self.store.lock(plan_id):
            plan = self.get(plan_id)
            self.editable(plan, revision)
            if plan.tasks:
                raise ConflictError(
                    "A task draft already exists; edit it or create a new plan."
                )
            plan.tasks = self.decomposer(plan)
            plan.revision += 1
            return self.save(plan)

    def update(self, plan_id, request: DraftUpdate):
        with self.store.lock(plan_id):
            plan = self.get(plan_id)
            self.editable(plan, request.revision)
            plan.tasks, plan.preferences = request.tasks, request.preferences
            plan.revision += 1
            plan.status, plan.candidates = "draft", []
            return self.save(plan)

    def validate(self, plan, events, busy, *, check_now=False):
        p = plan.preferences
        return validate_schedule(
            events,
            busy,
            time.fromisoformat(p.work_start),
            time.fromisoformat(p.work_end),
            deadline_boundary(p.deadline, p.timezone),
            timezone=p.timezone,
            subtasks=[task.model_dump() for task in plan.tasks],
            max_session_minutes=p.max_session_minutes,
            break_minutes=p.break_minutes,
            workdays=p.workdays,
            not_before=self.now() if check_now else None,
        )

    def candidate(self, plan, strategy, events, validation):
        tasks = {task.id: task for task in plan.tasks}
        placed = {event["task_id"] for event in events}
        unscheduled = [
            {
                "task_id": task.id,
                "name": task.name,
                "reason": "prerequisite"
                if any(dep not in placed for dep in task.depends_on)
                else "capacity",
            }
            for task in plan.tasks
            if task.id not in placed
        ]
        zone = ZoneInfo(plan.preferences.timezone)
        intervals = [
            (
                datetime.fromisoformat(e["start"]).astimezone(zone),
                datetime.fromisoformat(e["end"]).astimezone(zone),
            )
            for e in events
        ]
        total = sum(elapsed_minutes(a, b) for a, b in intervals)
        mismatch = sum(
            elapsed_minutes(a, b)
            * energy_mismatch(
                a,
                b,
                complexity_score(tasks[e["task_id"]].model_dump()),
                plan.preferences.energy_levels,
            )
            for e, (a, b) in zip(events, intervals)
        )
        metrics = {
            "scheduled_tasks": len(placed),
            "total_tasks": len(tasks),
            "scheduled_minutes": round(total),
            "total_minutes": sum(task.duration_minutes for task in tasks.values()),
            "workdays": len({a.date() for a, _ in intervals}),
            "finishes_at": max((b for _, b in intervals), default=None),
            "energy_alignment": round(100 * (1 - mismatch / (2 * total)))
            if total
            else None,
        }
        if metrics["finishes_at"]:
            metrics["finishes_at"] = metrics["finishes_at"].isoformat()
        explanation = {
            "deadline_first": "依照任務依賴，優先使用最早能容納任務的空檔。",
            "min_fragmentation": "在最早可行的日期優先使用較大的空檔，集中安排工作。",
            "energy_aware": "在最早可行的日期比較不同時段，配合任務強度與精力偏好。",
        }[strategy]
        snapshot = digest(
            {
                "plan": plan.id,
                "revision": plan.revision,
                "strategy": strategy,
                "events": events,
            }
        )
        return Candidate(
            id=strategy,
            events=events,
            unscheduled=unscheduled,
            validation=validation,
            metrics=metrics,
            explanation=explanation,
            snapshot_hash=snapshot,
        )

    def generate(self, plan_id, revision):
        with self.store.lock(plan_id):
            plan = self.get(plan_id)
            self.editable(plan, revision)
            if not plan.tasks:
                raise ValueError("Confirm the task draft before scheduling")
            p = plan.preferences
            now = self.now()
            # Leave a short review buffer; never create an already-started draft.
            start = datetime.fromtimestamp(
                math.ceil((now.timestamp() + 300) / 300) * 300, ZoneInfo(p.timezone)
            )
            end = deadline_boundary(p.deadline, p.timezone)
            if end <= start or end > now + timedelta(days=366):
                raise ValueError(
                    "Deadline must leave time for planning and be within one year"
                )
            busy = self.gateway(plan).busy(start, end, p.timezone)
            slots = compute_free_slots(
                busy,
                start,
                end,
                time.fromisoformat(p.work_start),
                time.fromisoformat(p.work_end),
                workdays=p.workdays,
            )
            plan.revision += 1
            tasks = [task.model_dump() for task in plan.tasks]
            plan.candidates = []
            for strategy in STRATEGIES:
                events = schedule(
                    tasks,
                    slots,
                    strategy,
                    p.break_minutes,
                    p.energy_levels,
                    max_session_minutes=p.max_session_minutes,
                )
                validation = self.validate(plan, events, busy)
                plan.candidates.append(
                    self.candidate(plan, strategy, events, validation)
                )
            plan.busy_blocks, plan.calendar_snapshot_at = busy, now.isoformat()
            plan.status = "review"
            return self.save(plan)

    def reject(self, plan_id, revision):
        with self.store.lock(plan_id):
            plan = self.get(plan_id)
            self.editable(plan, revision)
            plan.status = "rejected"
            return self.save(plan)

    def approve(self, plan_id, request: ApprovalRequest):
        with self.store.lock(plan_id):
            plan = self.get(plan_id)
            self.check_revision(plan, request.revision)
            candidate = next(
                (c for c in plan.candidates if c.id == request.candidate_id), None
            )
            if candidate is None or candidate.snapshot_hash != request.snapshot_hash:
                raise ConflictError("The approved proposal no longer matches this plan")
            if not set(request.acknowledged_violation_ids) <= {
                v["id"] for v in candidate.validation["violations"]
            }:
                raise ConflictError(
                    "Acknowledgements must match the displayed violations"
                )
            if plan.status == "rejected":
                raise ConflictError("This plan was rejected")
            if plan.approval:
                if plan.approval["snapshot_hash"] != request.snapshot_hash:
                    raise ConflictError(
                        "A different candidate has already been approved"
                    )
                if plan.status == "completed":
                    return plan
            elif not candidate.events:
                raise ValueError("There are no scheduled events to approve")
            else:
                acknowledged = set(request.acknowledged_violation_ids)
                required = {v["id"] for v in candidate.validation["violations"]}
                if not required <= acknowledged:
                    raise ConflictError(
                        "Review and acknowledge every violation before approval"
                    )

            gateway = self.gateway(plan)
            records = {r["event_id"]: r for r in self.store.write_records(plan.id)}
            # Reconcile unknown writes before excluding any event from the new
            # calendar read. The ID is bound to the immutable approved snapshot.
            event_ids = {
                e["id"]: digest(
                    [plan.id, plan.revision, candidate.snapshot_hash, e["id"]]
                )
                for e in candidate.events
            }
            for event in candidate.events:
                key = event_ids[event["id"]]
                record = records.get(key)
                if record and record["status"] != "confirmed":
                    remote = gateway.get(
                        key
                    )  # Errors here fail closed; never assume absence.
                    if remote is not None:
                        if not matches(event, remote):
                            raise ConflictError(
                                "An existing calendar event differs from the approved snapshot"
                            )
                        record.update(status="confirmed", response=remote, error=None)
                        self.store.save_write(plan.id, key, record)

            confirmed = {
                key
                for key, record in records.items()
                if record["status"] == "confirmed"
            }
            if plan.approval and all(key in confirmed for key in event_ids.values()):
                plan.status = "completed"
                return self.save(plan)
            starts = [datetime.fromisoformat(e["start"]) for e in candidate.events]
            ends = [datetime.fromisoformat(e["end"]) for e in candidate.events]
            busy = gateway.busy(
                min(starts), max(ends), plan.preferences.timezone, exclude_ids=confirmed
            )
            # Already-created sessions must not become IN_PAST on a retry.
            validation = self.validate(plan, candidate.events, busy)
            for event in candidate.events:
                if (
                    event_ids[event["id"]] not in confirmed
                    and datetime.fromisoformat(event["start"]) < self.now()
                ):
                    issue = {
                        "id": digest([event["id"], "IN_PAST"])[:20],
                        "task_id": event["task_id"],
                        "event_name": event["name"],
                        "violation_type": "IN_PAST",
                        "description": "Event starts before the latest calendar check",
                    }
                    validation["violations"].append(issue)
                    validation["passed"] = False
            known = set(request.acknowledged_violation_ids)
            if plan.approval:
                known |= set(plan.approval["acknowledged_violation_ids"])
            unseen = [v for v in validation["violations"] if v["id"] not in known]
            if unseen:
                # A changed calendar is surfaced, never automatically repaired.
                candidate.validation = validation
                plan.busy_blocks, plan.calendar_snapshot_at = (
                    busy,
                    self.now().isoformat(),
                )
                plan.status = "needs_review"
                return self.save(plan)

            plan.approval = {
                "snapshot_hash": candidate.snapshot_hash,
                "acknowledged_violation_ids": sorted(known),
                "approved_at": (plan.approval or {}).get(
                    "approved_at", self.now().isoformat()
                ),
            }
            plan.selected_candidate, plan.status = candidate.id, "writing"
            self.save(plan)  # Persist approval BEFORE the first external insert.
            for event in candidate.events:
                key = event_ids[event["id"]]
                if key in confirmed:
                    continue
                record = {
                    "event_id": key,
                    "task_id": event["task_id"],
                    "name": event["name"],
                    "status": "unknown",
                    "error": None,
                    "response": None,
                }
                self.store.save_write(plan.id, key, record)
                try:
                    remote = gateway.get(key)
                    if remote is None:
                        remote = gateway.insert(event, key)
                    if not matches(event, remote):
                        raise ConflictError(
                            "Calendar response does not match the approved event"
                        )
                    record.update(status="confirmed", response=remote)
                except Exception as exc:
                    # An exception after insert may still mean Google accepted
                    # it. Preserve UNKNOWN and reconcile via GET on retry.
                    record.update(
                        error=f"{type(exc).__name__}: could not confirm this event; retry to reconcile"
                    )
                self.store.save_write(plan.id, key, record)
                if record["status"] != "confirmed":
                    break
            results = self.store.write_records(plan.id)
            plan.status = (
                "completed"
                if sum(r["status"] == "confirmed" for r in results)
                == len(candidate.events)
                else "partial"
            )
            return self.save(plan)
