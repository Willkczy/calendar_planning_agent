# =============================================================================
# src/frontend/intake_form.py — User intake form
# =============================================================================
# Collects five fields from the user and returns them as a structured dict.
#
# STEPS TO COMPLETE:
# 1. Build the Streamlit form with the five fields listed below.
# 2. On submit, validate that required fields are present.
# 3. Package the fields into the UserInputs dict and return it.
# =============================================================================

from __future__ import annotations

import datetime
from typing import TypedDict

import streamlit as st


class UserInputs(TypedDict):
    """Structured dictionary returned by the intake form."""
    goal: str                       # Free-text goal description
    deadline: datetime.date         # Target completion date
    context: str                    # Optional background context
    work_start: datetime.time       # Preferred working hours — start
    work_end: datetime.time         # Preferred working hours — end
    max_session_minutes: int        # Maximum single-session length


def render_intake_form() -> UserInputs | None:
    """Render the intake form and return user inputs on submission.

    Returns None if the form has not been submitted yet.

    STEPS:
    1. Use st.form("intake_form") to group all fields together.
    2. Inside the form:
       a. st.text_input for the goal (required).
       b. st.date_input for the deadline, default = today + 14 days.
       c. st.text_area for background context (optional).
       d. Two st.time_input widgets for work_start and work_end.
          Default to 09:00 and 18:00.
       e. st.number_input for max_session_minutes,
          min=15, max=240, default=90, step=15.
       f. st.form_submit_button("Plan my schedule").
    3. On submit, if goal is empty show st.error and return None.
    4. If work_start >= work_end, show st.error and return None.
    5. If deadline <= today, show st.error and return None.
    6. Otherwise, construct and return a UserInputs dict.
    """
    pass  # TODO: implement
