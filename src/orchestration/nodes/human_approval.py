# =============================================================================
# src/orchestration/nodes/human_approval.py — Human-in-the-loop pause point
# =============================================================================
# This node is a terminal waiting point where the graph pauses until the
# frontend sends back the user's approval or rejection.
#
# In LangGraph, this is typically implemented using interrupt_before or
# interrupt_after on this node, so the graph execution yields control
# back to the caller.
#
# READS FROM STATE:  user_approved
# WRITES TO STATE:   (nothing — the frontend sets user_approved externally)
# =============================================================================

from __future__ import annotations

from typing import Any

from src.orchestration.state import AgentState


def human_approval_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: pause for human approval.

    This node does nothing on its own.  The graph is configured with
    interrupt_before=["human_approval"] so execution pauses before
    entering this node.  The frontend then:
      1. Displays the schedule to the user.
      2. Collects approve/reject.
      3. Updates state["user_approved"].
      4. Resumes the graph.

    When the graph resumes and this node actually executes, it simply
    passes through.

    STEPS:
    1. Return {} — this is a passthrough node.
       The conditional edge after this node routes based on
       state["user_approved"].
    """
    return {}
