# =============================================================================
# src/orchestration/nodes/build_proposal.py — Assemble the final proposal
# =============================================================================
# Packages the validated schedule and rationale into the format expected
# by the frontend.
#
# READS FROM STATE:  final_schedule, rationale, validation_result
# WRITES TO STATE:   (no new keys — just ensures data is clean for display)
# =============================================================================

from __future__ import annotations

from typing import Any

from src.orchestration.state import AgentState


def build_proposal_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: assemble the proposal for the frontend.

    STEPS:
    1. Read final_schedule and rationale from state.
    2. Optionally sort final_schedule chronologically by start time.
    3. If validation_result["passed"] is False, keep the violations
       in state so the frontend can show a warning.
    4. Return {} (state is already fully populated at this point).
       Or return any final cleanup fields if needed.
    """
    pass  # TODO: implement
