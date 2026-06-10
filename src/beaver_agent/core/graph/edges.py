"""Beaver Agent LangGraph conditional edges.

Each function here is a "routing function" — it reads the current
state and returns the name of the next node.  LangGraph calls these
after every node to decide where to flow next.
"""

from __future__ import annotations

from beaver_agent.core.graph.state import AgentState


def should_retry(state: AgentState) -> str:
    """Route back to executor when reviewer says 'retry'.

    Transitions:
      reviewer → executor  (reviewer decision == "retry" AND tasks remain)
      reviewer → reporter (decision == "proceed" or "no_tasks")
    """
    decision = state.get("review_decision", "")
    pending = state.get("pending_tasks", [])

    if decision == "retry" and pending:
        # Increment iteration counter before re-entering executor
        return "__all__"  # tells LangGraph to re-enter (handled in graph.py)

    # Everything else goes to reporter
    return "reporter"


def should_reenter_executor(state: AgentState) -> str:
    """Used after the retry edge to bump the iteration counter.

    Returns "__root__" to indicate the state was already mutated in place
    and LangGraph should continue without an explicit node transition.
    """
    return "__root__"
