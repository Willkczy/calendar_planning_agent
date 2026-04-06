# =============================================================================
# src/orchestration/nodes/score_candidates.py — Score and select best candidate
# =============================================================================
# Runs the deterministic validator on each of the three candidate schedules
# and selects the one with the fewest constraint violations.
#
# READS FROM STATE:  candidate_deadline_first, candidate_min_fragmentation,
#                     candidate_energy_aware, busy_blocks, work_start,
#                     work_end, deadline
# WRITES TO STATE:   selected_candidate, candidate_scores, validation_result
# =============================================================================

from __future__ import annotations

from typing import Any

from src.orchestration.state import AgentState
from src.validator.constraints import validate_schedule


def score_candidates_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: score all three candidates and pick the best.

    STEPS:
    1. Build the validation inputs from state:
       - busy_blocks  = state["busy_blocks"]
       - work_start   = parse state["work_start"]
       - work_end     = parse state["work_end"]
       - deadline_dt  = parse state["deadline"]

    2. For each candidate:
       a. result = validate_schedule(candidate, busy_blocks, work_start, work_end, deadline_dt)
       b. Store the violation count: len(result["violations"])

    3. Build candidate_scores dict:
       {"deadline_first": <count>, "min_fragmentation": <count>, "energy_aware": <count>}

    4. Select the candidate with the lowest violation count.
       Break ties by preferring deadline_first > min_frag > energy_aware.

    5. Run validate_schedule on the selected candidate to get its full report.

    6. Return {
           "selected_candidate": best_candidate,
           "candidate_scores": scores_dict,
           "validation_result": validation_report,
       }
    """
    pass  # TODO: implement
