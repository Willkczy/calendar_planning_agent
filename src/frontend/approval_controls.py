# =============================================================================
# src/frontend/approval_controls.py — Approve / Reject buttons
# =============================================================================
# Renders the approve and reject buttons and returns the user's decision.
#
# STEPS TO COMPLETE:
# 1. Display two clearly labelled buttons side by side.
# 2. Return the user's choice so app.py can resume the graph.
# =============================================================================

from __future__ import annotations

import streamlit as st


def render_approval_buttons() -> str | None:
    """Render approve/reject buttons and return the user's decision.

    Returns:
        "approve" if the user clicked Approve,
        "reject"  if the user clicked Reject,
        None      if neither button has been pressed yet.

    STEPS:
    1. Create two columns with st.columns(2).
    2. In the left column, place st.button("✅ Approve & Write to Calendar",
       type="primary").
    3. In the right column, place st.button("❌ Reject — Don't change anything").
    4. Return the corresponding string, or None if no press detected.
    """
    pass  # TODO: implement
