"""Optional research pipeline: critique, three heuristics, reviews, explanations.

The graph ends after proposal generation. Human decisions and durable writes
belong to PlanningService. The run/resume names remain compatibility adapters;
they do not claim to resume a checkpointed LangGraph execution.
"""

from __future__ import annotations

import datetime
import uuid
from config.settings import settings
from typing import Any

from langgraph.graph import StateGraph, END

from src.orchestration.state import AgentState

# --- Import node functions ---
from src.orchestration.nodes.fetch_events import fetch_events_node
from src.orchestration.nodes.decompose_goal import decompose_goal_node
from src.orchestration.nodes.decomposition_review import (
    decomposition_critic_node,
    revise_decomposition_node,
)
from src.orchestration.nodes.schedule_candidates import (
    deadline_first_node,
    min_fragmentation_node,
    energy_aware_node,
)
from src.orchestration.nodes.validate_candidates import validate_candidates_node
from src.orchestration.nodes.review_candidates import review_candidates_node
from src.orchestration.nodes.generate_rationales import generate_rationales_node
from src.orchestration.nodes.build_proposal import build_proposal_node
from src.orchestration.nodes.human_approval import human_approval_node
from src.orchestration.nodes.write_events import write_events_node


STRATEGY_TO_STATE_KEY = {
    "deadline_first": "candidate_deadline_first",
    "min_fragmentation": "candidate_min_fragmentation",
    "energy_aware": "candidate_energy_aware",
}


def _approval_decision(state: AgentState) -> str:
    """Return the write step only for an explicit strategy approval."""
    if state.get("user_approved") is True and state.get("selected_strategy"):
        return "write_events"
    return END


def _decomposition_review_decision(state: AgentState) -> str:
    """Route to one bounded decomposition revision only when requested."""
    if (
        state.get("decomposition_review_passed") is False
        and int(state.get("decomposition_revision_count", 0)) < 1
    ):
        return "revise_decomposition"
    return "fetch_events"


def _apply_node_updates(state: AgentState, updates: dict[str, Any]) -> None:
    """Apply node updates outside LangGraph while preserving reducer semantics."""
    trace_updates = updates.get("debug_trace")
    if trace_updates:
        state.setdefault("debug_trace", [])
        state["debug_trace"].extend(trace_updates)

    for key, value in updates.items():
        if key != "debug_trace":
            state[key] = value


def build_graph() -> Any:
    """Compile the optional research graph, ending at build_proposal."""
    graph = StateGraph(AgentState)

    graph.add_node("decompose_goal", decompose_goal_node)
    graph.add_node("decomposition_critic", decomposition_critic_node)
    graph.add_node("revise_decomposition", revise_decomposition_node)
    graph.add_node("fetch_events", fetch_events_node)
    graph.add_node("deadline_first", deadline_first_node)
    graph.add_node("min_fragmentation", min_fragmentation_node)
    graph.add_node("energy_aware", energy_aware_node)
    graph.add_node("validate_candidates", validate_candidates_node)
    graph.add_node("review_candidates", review_candidates_node)
    graph.add_node("generate_rationales", generate_rationales_node)
    graph.add_node("build_proposal", build_proposal_node)

    graph.set_entry_point("decompose_goal")

    graph.add_edge("decompose_goal", "decomposition_critic")
    graph.add_conditional_edges(
        "decomposition_critic",
        _decomposition_review_decision,
        {
            "revise_decomposition": "revise_decomposition",
            "fetch_events": "fetch_events",
        },
    )
    graph.add_edge("revise_decomposition", "fetch_events")

    graph.add_edge("fetch_events", "deadline_first")
    graph.add_edge("fetch_events", "min_fragmentation")
    graph.add_edge("fetch_events", "energy_aware")

    graph.add_edge("deadline_first", "validate_candidates")
    graph.add_edge("min_fragmentation", "validate_candidates")
    graph.add_edge("energy_aware", "validate_candidates")

    graph.add_edge("validate_candidates", "review_candidates")
    graph.add_edge("review_candidates", "generate_rationales")
    graph.add_edge("generate_rationales", "build_proposal")
    # Research graph only produces proposals. Durable approval and writing
    # belong to PlanningService; no pretend graph interrupt/manual resume pair.
    graph.add_edge("build_proposal", END)
    return graph.compile()


def run_graph_until_approval(
    graph: Any,
    user_inputs: dict[str, Any],
) -> AgentState:
    """Generate a research proposal with a stable plan ID and explicit timezone."""
    required_keys = {
        "goal",
        "deadline",
        "work_start",
        "work_end",
        "max_session_minutes",
        "energy_levels",
    }
    missing = required_keys - set(user_inputs)
    if missing:
        raise ValueError(
            f"run_graph_until_approval missing required user inputs: {sorted(missing)}"
        )

    deadline_input = user_inputs["deadline"]
    if isinstance(deadline_input, datetime.date):
        deadline_value = deadline_input.isoformat()
    else:
        deadline_value = str(deadline_input)

    work_start_input = user_inputs["work_start"]
    if isinstance(work_start_input, datetime.time):
        work_start_value = work_start_input.strftime("%H:%M")
    else:
        work_start_value = str(work_start_input)

    work_end_input = user_inputs["work_end"]
    if isinstance(work_end_input, datetime.time):
        work_end_value = work_end_input.strftime("%H:%M")
    else:
        work_end_value = str(work_end_input)

    initial_state: AgentState = {
        "plan_id": uuid.uuid4().hex,
        "timezone": str(user_inputs.get("timezone", settings.APP_TIMEZONE)),
        "goal": str(user_inputs["goal"]),
        "deadline": deadline_value,
        "context": str(user_inputs.get("context", "")),
        "work_start": work_start_value,
        "work_end": work_end_value,
        "max_session_minutes": int(user_inputs["max_session_minutes"]),
        "break_minutes": int(user_inputs.get("break_minutes", 10)),
        "energy_levels": dict(user_inputs["energy_levels"]),
        "selected_strategy": None,
        "user_approved": None,
        "decomposition_revised": False,
        "decomposition_revision_count": 0,
    }

    paused_state = graph.invoke(initial_state)
    if not isinstance(paused_state, dict):
        raise RuntimeError(
            "run_graph_until_approval expected graph.invoke(...) to return a state dict"
        )

    return paused_state


def resume_graph(
    graph: Any,
    paused_state: AgentState,
    approved: bool,
    selected_strategy: str | None = None,
) -> AgentState:
    """Compatibility adapter: apply a human decision, then use the durable writer."""
    _ = graph
    resumed_state: AgentState = dict(paused_state)
    resumed_state["user_approved"] = approved

    if approved:
        if selected_strategy not in STRATEGY_TO_STATE_KEY:
            raise ValueError(
                "resume_graph: approved=True requires a valid selected_strategy; "
                f"got {selected_strategy!r}"
            )

        resumed_state["selected_strategy"] = selected_strategy
        strategy_state_key = STRATEGY_TO_STATE_KEY[selected_strategy]
        if strategy_state_key not in resumed_state:
            raise ValueError(
                "resume_graph: selected strategy has no candidate schedule in state; "
                f"missing key {strategy_state_key!r}"
            )

        resumed_state["final_schedule"] = resumed_state[strategy_state_key]
    else:
        resumed_state["selected_strategy"] = None

    approval_updates = human_approval_node(resumed_state)
    _apply_node_updates(resumed_state, approval_updates)

    if _approval_decision(resumed_state) == "write_events":
        write_updates = write_events_node(resumed_state)
        _apply_node_updates(resumed_state, write_updates)

    return resumed_state
