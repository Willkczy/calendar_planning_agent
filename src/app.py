# =============================================================================
# src/app.py — Streamlit application entry point
# =============================================================================
# Run with:  streamlit run src/app.py
#
# This file wires together the frontend components and the orchestration
# backend. It manages Streamlit session state to hold the LangGraph execution
# state across user interactions (form submit → agent runs → user approves).
#
# STEPS TO COMPLETE:
# 1. Initialise session-state keys on first load (see _init_session_state).
# 2. Render the intake form; on submit, package inputs and kick off the graph.
# 3. While the graph is running, show a spinner / loading state.
# 4. Once the graph reaches the human-approval node, display the schedule
#    and rationale, then render approve/reject buttons.
# 5. On approve → resume graph → write events → show success.
# 6. On reject  → reset session → show "no changes made".
# =============================================================================

import streamlit as st

from src.frontend.intake_form import render_intake_form
from src.frontend.schedule_display import render_schedule, render_rationale
from src.frontend.approval_controls import render_approval_buttons
from src.orchestration.graph import build_graph, run_graph_until_approval, resume_graph


def _init_session_state() -> None:
    """Ensure all required keys exist in st.session_state.

    STEPS:
    1. Set default values for:
       - "graph_state"  → None   (holds paused LangGraph state)
       - "phase"        → "intake"  (one of: intake | running | review | done)
       - "result"       → None   (final result message to display)
    2. Any additional keys your modules need can be added here.
    """
    pass  # TODO: implement


def main() -> None:
    """Top-level Streamlit page layout and control flow.

    STEPS:
    1. Call st.set_page_config with a title and layout.
    2. Call _init_session_state().
    3. Branch on st.session_state["phase"]:

       "intake":
         a. Call render_intake_form() — returns a dict of user inputs or None.
         b. If the form was submitted, set phase to "running", store inputs.
         c. Call st.rerun() so the spinner appears on next render cycle.

       "running":
         a. Show st.spinner("Agent is planning your schedule…").
         b. Build the LangGraph graph via build_graph().
         c. Call run_graph_until_approval(graph, user_inputs).
         d. Store the returned paused state in session_state["graph_state"].
         e. Set phase to "review" and st.rerun().

       "review":
         a. Extract the proposed schedule and rationale from graph_state.
         b. Call render_schedule(schedule).
         c. Call render_rationale(rationale).
         d. If the graph_state contains unresolved violations, show a warning.
         e. Call render_approval_buttons() — returns "approve", "reject", or None.
         f. If "approve": set phase to "done", call resume_graph(graph_state, approved=True).
         g. If "reject":  set phase to "done", store rejection message.
         h. st.rerun().

       "done":
         a. Display st.session_state["result"] (success or rejection message).
         b. Offer a "Start over" button that resets session state.
    """
    pass  # TODO: implement


if __name__ == "__main__":
    main()
