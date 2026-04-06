# =============================================================================
# src/orchestration/nodes/generate_rationale.py — LLM rationale generation
# =============================================================================
# Calls the LLM to produce a human-readable explanation of how the goal
# was decomposed and how the schedule was chosen.
#
# READS FROM STATE:  subtasks, final_schedule (or selected_candidate),
#                     goal, context
# WRITES TO STATE:   rationale
# =============================================================================

from __future__ import annotations

from typing import Any

from src.llm_client.client import call_llm_text
from src.orchestration.state import AgentState


RATIONALE_PROMPT = """You are explaining a project schedule to the user.

The user wanted to achieve: {goal}
Context: {context}

The goal was broken into these subtasks (with estimated durations):
{subtasks_summary}

The final scheduled events are:
{schedule_summary}

Write 2–3 sentences explaining:
1. Why the goal was broken down this way.
2. How the scheduling decisions were made given the user's calendar constraints.

Be concise, specific, and helpful.
"""


def generate_rationale_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: generate a plain-language rationale via LLM.

    STEPS:
    1. Build subtasks_summary: a formatted string listing each subtask
       name and duration, e.g. "- Set up dev env (30 min)".
    2. Build schedule_summary: a formatted string listing each event's
       name, date, and time range.
    3. Format RATIONALE_PROMPT with the above + goal + context.
    4. Call call_llm_text(prompt) to get the rationale string.
    5. Store the selected_candidate as final_schedule (it's the one that
       passed validation or the best-effort one).
    6. Return {"rationale": rationale_text, "final_schedule": schedule}.
    """
    pass  # TODO: implement
