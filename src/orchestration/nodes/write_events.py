# =============================================================================
# src/orchestration/nodes/write_events.py — Write approved events to calendar
# =============================================================================
# Called only after the user clicks "Approve".  Creates each proposed event
# on the user's Google Calendar (or mock calendar).
#
# READS FROM STATE:  final_schedule
# WRITES TO STATE:   write_results
# =============================================================================

from __future__ import annotations

from typing import Any

from config.settings import settings
from src.orchestration.state import AgentState


def write_events_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: write all approved events to the calendar.

    STEPS:
    1. Read final_schedule from state.
    2. Branch on settings.CALENDAR_MODE:
       a. "mock":
          - For each event, call mock_calendar.create_mock_event(
                event["name"], event["description"],
                parse(event["start"]), parse(event["end"])
            ).
       b. "live":
          - Call events.create_events_batch(final_schedule).
    3. Collect all API responses into a list.
    4. Return {"write_results": responses}.
    """
    pass  # TODO: implement
