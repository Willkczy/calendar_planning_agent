"""Streamlit compatibility UI using the same persistent service as the React app."""

from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from config.settings import settings
from src.domain.models import (
    ApprovalRequest,
    CreatePlan,
    DraftUpdate,
    Preferences,
    Task,
)
from src.frontend.intake_form import render_intake_form
from src.planning.service import PlanningService
from src.planning.store import PlanStore


@st.cache_resource
def get_service():
    return PlanningService(
        PlanStore(
            os.getenv("PLANNER_DB_PATH", str(PROJECT_ROOT / ".data/planner.sqlite3"))
        )
    )


def _format_planning_error(exc: Exception) -> str:
    """Return a user-facing message for planning failures."""
    current: BaseException | None = exc
    while current is not None:
        if "LLM API key is not set" in str(current):
            return (
                "LLM API key is not set. CALENDAR_MODE=mock skips Google Calendar "
                "credentials, but planning still needs an LLM unless "
                "LLM_PROVIDER=mock. Add LLM_API_KEY/GEMINI_API_KEY to .env or use "
                "LLM_PROVIDER=mock and try again."
            )
        if "ANTHROPIC_API_KEY is not set" in str(current):
            return (
                "ANTHROPIC_API_KEY is not set. Set LLM_API_KEY, ANTHROPIC_API_KEY, "
                "or use LLM_PROVIDER=mock and try again."
            )
        current = current.__cause__

    return f"Planning failed: {exc}"


def main():
    st.set_page_config(page_title="Calendar Planning Agent", layout="wide")
    st.title("Calendar Planning Agent")
    st.caption(
        f"{'Demo calendar' if settings.CALENDAR_MODE == 'mock' else settings.GOOGLE_CALENDAR_ID} · {settings.APP_TIMEZONE} · Plans saved locally"
    )
    service = get_service()
    if st.sidebar.button("New plan"):
        st.query_params.clear()
        st.session_state.pop("edit_plan", None)
        st.rerun()
    for saved in service.store.list():
        if st.sidebar.button(saved.goal, key=saved.id):
            st.query_params["plan"] = saved.id
            st.session_state.pop("edit_plan", None)
            st.rerun()
    try:
        plan_id = st.query_params.get("plan")
        if not plan_id:
            inputs = render_intake_form()
            if inputs:
                prefs = Preferences(
                    deadline=inputs["deadline"],
                    timezone=settings.APP_TIMEZONE,
                    work_start=inputs["work_start"].strftime("%H:%M"),
                    work_end=inputs["work_end"].strftime("%H:%M"),
                    max_session_minutes=inputs["max_session_minutes"],
                    break_minutes=inputs["break_minutes"],
                    energy_levels=inputs["energy_levels"],
                )
                plan = service.create(
                    CreatePlan(
                        goal=inputs["goal"],
                        context=inputs["context"],
                        preferences=prefs,
                    )
                )
                st.query_params["plan"] = plan.id
                with st.spinner("Breaking down your goal…"):
                    service.decompose(plan.id, plan.revision)
                st.rerun()
            return
        plan = service.get(plan_id)
        st.subheader(plan.goal)
        st.caption(f"Saved · v{plan.revision} · {plan.preferences.timezone}")
        if not plan.tasks:
            if st.button("Continue task breakdown"):
                service.decompose(plan.id, plan.revision)
                st.rerun()
            return
        if plan.status == "rejected":
            st.info("This plan is closed. No calendar events were added.")
            return
        if plan.status in {"completed", "partial", "writing"}:
            if plan.status == "completed":
                st.success(
                    "All events have been added and confirmed."
                    + (
                        " Google Calendar has not changed."
                        if plan.calendar_mode == "mock"
                        else ""
                    )
                )
            else:
                st.warning(
                    "Some writes are unconfirmed. Retry checks existing events before continuing."
                )
            st.dataframe(
                [
                    {k: r.get(k) for k in ("name", "status", "error")}
                    for r in plan.write_results
                ],
                hide_index=True,
            )
            if plan.status != "completed" and st.button("Verify and continue"):
                candidate = next(
                    c for c in plan.candidates if c.id == plan.selected_candidate
                )
                service.approve(
                    plan.id,
                    ApprovalRequest(
                        revision=plan.revision,
                        candidate_id=candidate.id,
                        snapshot_hash=candidate.snapshot_hash,
                        acknowledged_violation_ids=[
                            v["id"] for v in candidate.validation["violations"]
                        ],
                    ),
                )
                st.rerun()
            return
        if plan.status == "draft" or st.session_state.get("edit_plan") == plan.id:
            st.info(
                "Review task names, estimates, and prerequisites before building schedules. The web workspace offers full dependency editing and a week view."
            )
            rows = st.data_editor(
                [task.model_dump() for task in plan.tasks],
                disabled=["id", "depends_on"],
                hide_index=True,
                key=f"tasks-{plan.id}-{plan.revision}",
            )
            deadline = st.date_input(
                "Deadline",
                value=plan.preferences.deadline,
                key=f"deadline-{plan.id}-{plan.revision}",
            )
            if st.button("Save and build schedules", type="primary"):
                prefs = plan.preferences.model_copy(update={"deadline": deadline})
                updated = service.update(
                    plan.id,
                    DraftUpdate(
                        revision=plan.revision,
                        tasks=[Task.model_validate(row) for row in rows],
                        preferences=prefs,
                    ),
                )
                with st.spinner("Reading your calendar and building three schedules…"):
                    service.generate(plan.id, updated.revision)
                st.session_state.pop("edit_plan", None)
                st.rerun()
            return
        if plan.status == "needs_review":
            st.warning(
                "Your calendar has changed. Please review and acknowledge each issue."
            )
        names = {
            "deadline_first": "Finish early",
            "min_fragmentation": "Group work",
            "energy_aware": "Match energy",
        }
        selected = st.radio(
            "Choose a schedule",
            [c.id for c in plan.candidates],
            format_func=lambda key: names[key],
            horizontal=True,
            index=next(
                (
                    i
                    for i, c in enumerate(plan.candidates)
                    if c.id == plan.selected_candidate
                ),
                0,
            ),
            disabled=plan.approval is not None,
        )
        candidate = next(c for c in plan.candidates if c.id == selected)
        st.write(candidate.explanation)
        st.caption(
            f"{candidate.metrics['scheduled_tasks']}/{candidate.metrics['total_tasks']} tasks scheduled · {candidate.metrics['scheduled_minutes']} minutes"
        )
        from zoneinfo import ZoneInfo
        from datetime import datetime

        zone = ZoneInfo(plan.preferences.timezone)
        st.dataframe(
            [
                {
                    "Task": e["name"],
                    "Start": datetime.fromisoformat(e["start"])
                    .astimezone(zone)
                    .strftime("%m/%d %H:%M"),
                    "End": datetime.fromisoformat(e["end"])
                    .astimezone(zone)
                    .strftime("%m/%d %H:%M"),
                }
                for e in candidate.events
            ],
            hide_index=True,
        )
        acknowledged = []
        for issue in candidate.validation["violations"]:
            if st.checkbox(
                f"I understand and accept: {issue['event_name']} — {issue['description']}",
                key=f"ack-{plan.id}-{plan.revision}-{selected}-{issue['id']}",
            ):
                acknowledged.append(issue["id"])
        if not plan.approval and st.button("Edit tasks"):
            st.session_state["edit_plan"] = plan.id
            st.rerun()
        st.caption(
            f"Add {len(candidate.events)} events to {'the demo calendar (no changes to Google Calendar)' if plan.calendar_mode == 'mock' else plan.calendar_id}."
        )
        if st.button(
            "Add events",
            type="primary",
            disabled=not candidate.events
            or len(acknowledged) != len(candidate.validation["violations"]),
        ):
            service.approve(
                plan.id,
                ApprovalRequest(
                    revision=plan.revision,
                    candidate_id=selected,
                    snapshot_hash=candidate.snapshot_hash,
                    acknowledged_violation_ids=acknowledged,
                ),
            )
            st.rerun()
        if not plan.approval and st.button("Reject plan"):
            service.reject(plan.id, plan.revision)
            st.rerun()
    except Exception as exc:
        st.error(_format_planning_error(exc))
        st.caption("Your saved plan is retained. Reopen it from the sidebar.")


if __name__ == "__main__":
    main()
