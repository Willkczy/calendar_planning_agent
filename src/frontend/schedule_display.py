# =============================================================================
# src/frontend/schedule_display.py — Proposed schedule & rationale rendering
# =============================================================================
# Once the agent produces a proposed schedule, this module displays it in
# the Streamlit UI as a readable table/list and shows the LLM rationale.
#
# STEPS TO COMPLETE:
# 1. Implement render_schedule to display events as a styled table.
# 2. Implement render_rationale to display the LLM explanation.
# 3. Implement render_violation_warning for unresolved constraint issues.
# =============================================================================

from __future__ import annotations

from typing import Any

import streamlit as st


def render_schedule(schedule: list[dict[str, Any]]) -> None:
    """Display the proposed event schedule as a table/list.

    Args:
        schedule: List of event dicts, each with keys:
            - name (str): subtask name
            - description (str): short description
            - start (str): ISO 8601 datetime string
            - end (str): ISO 8601 datetime string

    STEPS:
    1. Convert the list of dicts to a pandas DataFrame (optional but nice).
    2. Format start/end into human-readable strings
       e.g. "Mon Apr 07 · 09:00–10:30".
    3. Render with st.dataframe() or st.table(), or iterate with st.write()
       for a card-style layout.
    4. Group events by date for readability.
    """
    pass  # TODO: implement


def render_rationale(rationale: str) -> None:
    """Display the LLM-generated rationale explaining scheduling decisions.

    Args:
        rationale: Plain-language explanation string from the LLM.

    STEPS:
    1. Use st.subheader("Why this schedule?") or similar heading.
    2. Render the rationale text with st.markdown() or st.info().
    """
    pass  # TODO: implement


def render_violation_warning(violations: list[dict[str, Any]]) -> None:
    """Show a warning banner when unresolved constraint violations exist.

    Args:
        violations: List of violation dicts from the validator, each with:
            - event_name (str)
            - violation_type (str): "OVERLAP" | "OUT_OF_HOURS" | "DEADLINE_EXCEEDED"
            - description (str)

    STEPS:
    1. Use st.warning() with a header like "⚠️ Some constraints could not be resolved".
    2. List each violation: event_name — violation_type — description.
    """
    pass  # TODO: implement
