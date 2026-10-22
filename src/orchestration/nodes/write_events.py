"""Research-graph compatibility: all approved writes use the application ledger."""
from src.planning.legacy import approve_graph_proposal
from src.orchestration.debug_trace import make_trace_event, trace_update


def write_events_node(state):
    plan = approve_graph_proposal(state)
    confirmed = [row["response"] for row in plan.write_results if row["status"] == "confirmed"]
    trace = make_trace_event("write_events", summary={"status":plan.status, "confirmed":len(confirmed)})
    return {"write_results":confirmed, "write_status":plan.status,
            "write_ledger":plan.write_results, **trace_update(trace)}
