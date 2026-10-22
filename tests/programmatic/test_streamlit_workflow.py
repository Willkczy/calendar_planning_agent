"""Exercise the compatibility UI against the real local service in mock mode."""

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from config.settings import settings
from src.planning.store import PlanStore


@pytest.mark.parametrize("approve", [True, False])
def test_streamlit_persists_approved_or_rejected_plan(tmp_path, monkeypatch, approve):
    database = tmp_path / "streamlit.sqlite3"
    monkeypatch.setenv("PLANNER_DB_PATH", str(database))
    monkeypatch.setattr(settings, "CALENDAR_MODE", "mock")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    st.cache_resource.clear()
    try:
        app = AppTest.from_file("src/app.py", default_timeout=15).run()
        app.text_input[0].set_value("Build a personal portfolio")
        next(b for b in app.button if b.label == "Plan my schedule").click().run()
        assert not app.exception and not app.error
        next(b for b in app.button if b.label == "儲存並建立方案").click().run()
        assert not app.exception and not app.error
        assert len(app.radio[0].options) == 3
        action = "確認新增" if approve else "不採用"
        next(b for b in app.button if b.label == action).click().run()
        assert not app.exception and not app.error

        store = PlanStore(database)
        plan = store.list()[0]
        assert plan.status == ("completed" if approve else "rejected")
        assert len(store.mock_events(plan.calendar_id)) == (6 if approve else 0)
        assert len(store.write_records(plan.id)) == (6 if approve else 0)

        reopened = AppTest.from_file("src/app.py", default_timeout=15)
        reopened.query_params["plan"] = plan.id
        reopened.run()
        assert not reopened.exception and not reopened.error
        if approve:
            assert "已確認所有事件新增完成" in reopened.success[0].value
        else:
            assert "沒有新增日曆事件" in reopened.info[0].value
    finally:
        st.cache_resource.clear()
