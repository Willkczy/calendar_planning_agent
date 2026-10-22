"""Cross-layer regression tests for revisioned planning and add-only recovery."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.models import ApprovalRequest, CreatePlan, DraftUpdate, Task
from src.planning.calendar import CalendarGateway
from src.planning.service import PlanningService
from src.planning.store import ConflictError, PlanStore

NOW = datetime(2026, 10, 26, 8, tzinfo=timezone.utc)


class FaultCalendar(CalendarGateway):
    def __init__(self, store):
        super().__init__(store, "mock", "test")
        self.blocks = []
        self.inserts = 0
        self.fail_on = None
        self.lose_response = False
        self.read_fails = False

    def busy(self, start, end, timezone, exclude_ids=()):
        if self.read_fails:
            raise RuntimeError("calendar unavailable")
        return self.blocks

    def insert(self, event, event_id):
        self.inserts += 1
        if self.inserts == self.fail_on and not self.lose_response:
            raise TimeoutError("not inserted")
        result = super().insert(event, event_id)
        if self.inserts == self.fail_on:
            raise TimeoutError("inserted but response lost")
        return result


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr("config.settings.settings.CALENDAR_MODE", "mock")
    monkeypatch.setattr("config.settings.settings.LLM_PROVIDER", "mock")
    store = PlanStore(tmp_path / "plans.sqlite3")
    calendar = FaultCalendar(store)
    service = PlanningService(
        store, gateway_factory=lambda *_: calendar, now=lambda: NOW
    )
    return service, calendar


def proposal(service):
    plan = service.create(
        CreatePlan(
            goal="準備作品集", preferences={"deadline": "2026-11-06", "timezone": "UTC"}
        )
    )
    plan = service.decompose(plan.id, plan.revision)
    return service.generate(plan.id, plan.revision)


def approval(plan, candidate=None, ack=()):
    candidate = candidate or plan.candidates[0]
    return ApprovalRequest(
        revision=plan.revision,
        candidate_id=candidate.id,
        snapshot_hash=candidate.snapshot_hash,
        acknowledged_violation_ids=list(ack),
    )


def test_persist_reload_edit_invalidate_old_approval(setup):
    service, calendar = setup
    plan = proposal(service)
    old = approval(plan)
    tasks = list(plan.tasks)
    tasks[0] = tasks[0].model_copy(
        update={"name": "改名後仍是相同任務", "duration_minutes": 25}
    )
    edited = service.update(
        plan.id,
        DraftUpdate(revision=plan.revision, tasks=tasks, preferences=plan.preferences),
    )
    reopened = PlanningService(PlanStore(service.store.path)).get(plan.id)
    assert reopened.tasks[0].id == plan.tasks[0].id
    assert reopened.tasks[0].duration_minutes == 25
    assert reopened.candidates == []
    assert edited.revision > plan.revision
    with pytest.raises(ConflictError):
        service.approve(plan.id, old)
    assert calendar.inserts == 0


def test_repeated_approval_is_idempotent_across_service_instances(setup):
    service, calendar = setup
    plan = proposal(service)
    request = approval(plan)
    first = service.approve(plan.id, request)
    second_service = PlanningService(
        PlanStore(service.store.path),
        gateway_factory=lambda *_: calendar,
        now=lambda: NOW,
    )
    second = second_service.approve(plan.id, request)
    assert first.status == second.status == "completed"
    assert calendar.inserts == len(plan.tasks)
    assert all(r["status"] == "confirmed" for r in second.write_results)
    with pytest.raises(ConflictError):
        second_service.approve(plan.id, approval(plan, plan.candidates[1]))


@pytest.mark.parametrize("lost_response", [False, True])
def test_partial_write_recovery_and_lost_response(setup, lost_response):
    service, calendar = setup
    plan = proposal(service)
    calendar.fail_on, calendar.lose_response = 2, lost_response
    request = approval(plan)
    partial = service.approve(plan.id, request)
    assert partial.status == "partial"
    assert [r["status"] for r in partial.write_results] == ["confirmed", "unknown"]
    assert service.get(plan.id).approval is not None
    final = service.approve(plan.id, request)
    assert final.status == "completed"
    assert len(calendar.store.mock_events("test")) == len(plan.tasks)
    assert calendar.inserts == len(plan.tasks) + (0 if lost_response else 1)


def test_new_calendar_conflict_requires_specific_acknowledgment(setup):
    service, calendar = setup
    plan = proposal(service)
    event = plan.candidates[0].events[0]
    calendar.blocks = [{"start": event["start"], "end": event["end"]}]
    changed = service.approve(plan.id, approval(plan))
    assert changed.status == "needs_review"
    assert calendar.inserts == 0
    issues = changed.candidates[0].validation["violations"]
    assert any(v["violation_type"] == "OVERLAP" for v in issues)
    with pytest.raises(ConflictError):
        service.approve(plan.id, approval(changed))
    final = service.approve(plan.id, approval(changed, ack=[v["id"] for v in issues]))
    assert final.status == "completed"


def test_read_failure_never_looks_like_free_calendar(setup):
    service, calendar = setup
    plan = proposal(service)
    calendar.read_fails = True
    with pytest.raises(RuntimeError):
        service.approve(plan.id, approval(plan))
    assert calendar.inserts == 0
    assert service.get(plan.id).status == "review"


def test_reject_has_zero_writes_and_cannot_be_approved(setup):
    service, calendar = setup
    plan = proposal(service)
    assert service.reject(plan.id, plan.revision).status == "rejected"
    with pytest.raises(ConflictError):
        service.approve(plan.id, approval(plan))
    assert calendar.inserts == 0


def test_snapshot_tampering_and_concurrent_mutation_rejected(setup):
    service, calendar = setup
    plan = proposal(service)
    request = approval(plan).model_copy(update={"snapshot_hash": "0" * 64})
    with pytest.raises(ConflictError):
        service.approve(plan.id, request)
    with service.store.lock(plan.id), pytest.raises(ConflictError):
        service.generate(plan.id, plan.revision)
    assert calendar.inserts == 0


def test_overlong_prerequisite_is_not_dropped_from_dependency_graph(setup):
    service, _ = setup
    plan = proposal(service)
    tasks = [
        Task(id="a", name="Prerequisite", duration_minutes=180),
        Task(id="b", name="Dependent", duration_minutes=30, depends_on=["a"]),
    ]
    plan = service.update(
        plan.id,
        DraftUpdate(revision=plan.revision, tasks=tasks, preferences=plan.preferences),
    )
    plan = service.generate(plan.id, plan.revision)
    assert all(
        not c.events and len(c.unscheduled) == 2 and not c.validation["passed"]
        for c in plan.candidates
    )
    with pytest.raises(ValueError, match="no scheduled events"):
        service.approve(plan.id, approval(plan))


def test_mock_insert_is_persisted_and_becomes_busy(setup):
    service, _ = setup
    plan = proposal(service)
    gateway = CalendarGateway(service.store, "mock", "primary")
    event = plan.candidates[0].events[0]
    result = gateway.insert(event, "a" * 64)
    reopened = CalendarGateway(PlanStore(service.store.path), "mock", "primary")
    assert reopened.get(result["id"]) == result
    blocks = reopened.busy(NOW, NOW + timedelta(days=1), "UTC")
    assert {"start": event["start"], "end": event["end"]} in blocks


def test_api_end_to_end_and_revision_conflict(setup):
    service, calendar = setup
    client = TestClient(create_app(service))
    created = client.post(
        "/api/plans",
        json={
            "goal": "新的計畫",
            "preferences": {"deadline": "2026-11-06", "timezone": "UTC"},
        },
    )
    assert created.status_code == 201
    plan = created.json()
    plan = client.post(
        f"/api/plans/{plan['id']}/decompose", json={"revision": plan["revision"]}
    ).json()
    plan = client.post(
        f"/api/plans/{plan['id']}/generate", json={"revision": plan["revision"]}
    ).json()
    assert plan["status"] == "review"
    assert len(plan["candidates"]) == 3
    assert client.get(f"/api/plans/{plan['id']}").json() == plan
    assert (
        client.post(f"/api/plans/{plan['id']}/reject", json={"revision": 1}).status_code
        == 409
    )
    assert calendar.inserts == 0
    assert (
        client.post(
            "/api/plans", headers={"Origin": "https://untrusted.example"}, json={}
        ).status_code
        == 403
    )
    assert (
        client.get("/api/plans", headers={"Host": "untrusted.example"}).status_code
        == 400
    )


def test_invalid_dag_is_a_validation_error(setup):
    service, _ = setup
    plan = proposal(service)
    client = TestClient(create_app(service))
    tasks = [
        {"id": "a", "name": "A", "duration_minutes": 30, "depends_on": ["b"]},
        {"id": "b", "name": "B", "duration_minutes": 30, "depends_on": ["a"]},
    ]
    response = client.put(
        f"/api/plans/{plan.id}/draft",
        json={
            "revision": plan.revision,
            "tasks": tasks,
            "preferences": plan.preferences.model_dump(mode="json"),
        },
    )
    assert response.status_code == 422
    assert service.get(plan.id).revision == plan.revision


def test_one_logical_llm_call_and_zero_calls_to_regenerate(setup, monkeypatch):
    from src.llm_client import client

    service, _ = setup
    original = client.call_llm_json
    calls = []

    def counted(*args, **kwargs):
        calls.append(kwargs.get("purpose"))
        return original(*args, **kwargs)

    monkeypatch.setattr(client, "call_llm_json", counted)
    plan = proposal(service)
    service.generate(plan.id, plan.revision)
    assert calls == ["decomposition"]


def test_mode_change_cannot_write_to_a_saved_live_calendar(setup, monkeypatch):
    service, calendar = setup
    plan = proposal(service)
    monkeypatch.setattr("config.settings.settings.CALENDAR_MODE", "live")
    with pytest.raises(ConflictError, match="different calendar configuration"):
        service.approve(plan.id, approval(plan))
    assert calendar.inserts == 0


def test_uncertain_lookup_error_is_not_retried_as_insert(setup, monkeypatch):
    service, calendar = setup
    plan = proposal(service)
    calendar.fail_on, calendar.lose_response = 1, True
    service.approve(plan.id, approval(plan))
    assert calendar.inserts == 1

    def unavailable(_id):
        raise TimeoutError("cannot read event")

    monkeypatch.setattr(calendar, "get", unavailable)
    with pytest.raises(TimeoutError):
        service.approve(plan.id, approval(plan))
    assert calendar.inserts == 1
