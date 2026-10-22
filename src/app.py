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
    st.set_page_config(page_title="日序 · Calendar Planning", layout="wide")
    st.title("日序 · Calendar Planning")
    st.caption(
        f"{'示範日曆' if settings.CALENDAR_MODE == 'mock' else settings.GOOGLE_CALENDAR_ID} · {settings.APP_TIMEZONE} · 計畫儲存於本機"
    )
    service = get_service()
    if st.sidebar.button("新的規劃"):
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
                with st.spinner("正在拆解目標…"):
                    service.decompose(plan.id, plan.revision)
                st.rerun()
            return
        plan = service.get(plan_id)
        st.subheader(plan.goal)
        st.caption(f"已保存 · v{plan.revision} · {plan.preferences.timezone}")
        if not plan.tasks:
            if st.button("繼續拆解目標"):
                service.decompose(plan.id, plan.revision)
                st.rerun()
            return
        if plan.status == "rejected":
            st.info("計畫已結束，沒有新增日曆事件。")
            return
        if plan.status in {"completed", "partial", "writing"}:
            if plan.status == "completed":
                st.success(
                    "已確認所有事件新增完成。"
                    + (
                        " Google Calendar 沒有變更。"
                        if plan.calendar_mode == "mock"
                        else ""
                    )
                )
            else:
                st.warning("寫入尚未全部確認。重試時會先核對已建立的事件。")
            st.dataframe(
                [
                    {k: r.get(k) for k in ("name", "status", "error")}
                    for r in plan.write_results
                ],
                hide_index=True,
            )
            if plan.status != "completed" and st.button("核對並繼續新增"):
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
                "確認任務名稱、估時與依賴後，再建立方案。完整的依賴編輯與週曆可使用 React 工作區。"
            )
            rows = st.data_editor(
                [task.model_dump() for task in plan.tasks],
                disabled=["id", "depends_on"],
                hide_index=True,
                key=f"tasks-{plan.id}-{plan.revision}",
            )
            deadline = st.date_input(
                "截止日期",
                value=plan.preferences.deadline,
                key=f"deadline-{plan.id}-{plan.revision}",
            )
            if st.button("儲存並建立方案", type="primary"):
                prefs = plan.preferences.model_copy(update={"deadline": deadline})
                updated = service.update(
                    plan.id,
                    DraftUpdate(
                        revision=plan.revision,
                        tasks=[Task.model_validate(row) for row in rows],
                        preferences=prefs,
                    ),
                )
                with st.spinner("正在讀取日曆並建立三種安排…"):
                    service.generate(plan.id, updated.revision)
                st.session_state.pop("edit_plan", None)
                st.rerun()
            return
        if plan.status == "needs_review":
            st.warning("日曆有新的變化。請重新檢視並逐項確認限制。")
        names = {
            "deadline_first": "提早完成",
            "min_fragmentation": "集中安排",
            "energy_aware": "配合精力",
        }
        selected = st.radio(
            "選擇方案",
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
            f"{candidate.metrics['scheduled_tasks']}/{candidate.metrics['total_tasks']} 項任務已排入 · {candidate.metrics['scheduled_minutes']} 分鐘"
        )
        from zoneinfo import ZoneInfo
        from datetime import datetime

        zone = ZoneInfo(plan.preferences.timezone)
        st.dataframe(
            [
                {
                    "任務": e["name"],
                    "開始": datetime.fromisoformat(e["start"])
                    .astimezone(zone)
                    .strftime("%m/%d %H:%M"),
                    "結束": datetime.fromisoformat(e["end"])
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
                f"我了解並接受：{issue['event_name']} — {issue['description']}",
                key=f"ack-{plan.id}-{plan.revision}-{selected}-{issue['id']}",
            ):
                acknowledged.append(issue["id"])
        if not plan.approval and st.button("調整任務"):
            st.session_state["edit_plan"] = plan.id
            st.rerun()
        st.caption(
            f"將新增 {len(candidate.events)} 個事件到 {'示範日曆（不會寫入 Google Calendar）' if plan.calendar_mode == 'mock' else plan.calendar_id}。"
        )
        if st.button(
            "確認新增",
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
        if not plan.approval and st.button("不採用"):
            service.reject(plan.id, plan.revision)
            st.rerun()
    except Exception as exc:
        st.error(_format_planning_error(exc))
        st.caption("已保存的內容仍保留。可從側欄重新開啟計畫。")


if __name__ == "__main__":
    main()
