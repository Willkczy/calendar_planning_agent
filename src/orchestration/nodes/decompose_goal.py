# =============================================================================
# src/orchestration/nodes/decompose_goal.py — Goal decomposition node
# =============================================================================
# Calls the LLM to break the user's goal into concrete subtasks.
# This is the FIRST node in the graph and the most critical for quality.
#
# READS FROM STATE:  goal, deadline, context, max_session_minutes
# WRITES TO STATE:   subtasks
# =============================================================================

from __future__ import annotations

import json
from typing import Any

from src.llm_client.client import call_llm_json
from src.orchestration.state import AgentState, Subtask


# ---------------------------------------------------------------------------
# Prompt template for goal decomposition
# ---------------------------------------------------------------------------
DECOMPOSITION_PROMPT = """You are an expert project planner. Given a user's goal, deadline, and context, \
decompose the goal into a list of concrete, actionable subtasks.

RULES:
- Return ONLY a JSON array — no markdown, no code fences, no preamble.
- Each element must be an object with exactly three fields:
    "name"             (string): short title for the subtask
    "description"      (string): 1–2 sentences describing what the work involves
    "duration_minutes" (integer): estimated focused-work time in minutes
- Subtasks must reflect genuine domain knowledge, be ordered logically, and
  be sized realistically for focused work sessions.
- No single subtask should exceed {max_session} minutes.
- The total estimated time should be achievable before the deadline.
- Avoid generic filler tasks like "review progress" unless truly needed.

USER GOAL: {goal}
DEADLINE: {deadline}
BACKGROUND CONTEXT: {context}
MAX SESSION LENGTH: {max_session} minutes
"""


def decompose_goal_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: decompose the user's goal into subtasks via LLM.

    STEPS:
    1. Format DECOMPOSITION_PROMPT with state values.
    2. Call call_llm_json(prompt) — this returns a parsed Python object.
       a. The LLM client handles retries internally (up to 2 retries).
    3. Validate that the response is a list of dicts with the required keys.
       a. For each item, ensure "name" is a non-empty string.
       b. Ensure "duration_minutes" is a positive integer.
       c. Ensure "duration_minutes" <= state["max_session_minutes"].
          If it exceeds, split it or cap it (implementation choice).
    4. Convert each dict into a Subtask TypedDict.
    5. Return {"subtasks": subtasks_list}.

    ERROR HANDLING:
    - If call_llm_json raises after all retries, raise a clear error
      that app.py can catch and display to the user.
    """
    pass  # TODO: implement
