"""Beaver Agent shared state for LangGraph StateGraph."""

from __future__ import annotations

from typing import TypedDict

from beaver_agent.core.multi_agent.protocols import Task


class AgentState(TypedDict):
    """LangGraph shared state — single source of truth for the entire graph.

    Tracks the full lifecycle of a multi-agent task from user input through
    decomposition, parallel execution, review, and final reporting.

    Attributes:
        user_input:      Raw user request string.
        intent:          Parsed intent label (e.g. "code_generation").
        pending_tasks:   Tasks queued for execution (FIFO inbox).
        running_tasks:   Tasks currently being executed by workers.
        done_tasks:      Tasks that completed successfully.
        failed_tasks:    Tasks that raised an exception.
        review_decision: One of "proceed" | "retry" | "no_tasks".
        report:          Human-readable report string (final output).
        iteration:       Current execution round (starts at 0).
        max_iterations:  Guard against infinite retry loops.
        error:           Fatal error message if the graph reached an un-recoverable state.
    """

    user_input: str
    intent: str
    pending_tasks: list[Task]
    running_tasks: list[Task]
    done_tasks: list[Task]
    failed_tasks: list[Task]
    review_decision: str
    report: str
    iteration: int
    max_iterations: int
    error: str | None


def make_initial_state(user_input: str, max_iterations: int = 5) -> AgentState:
    """Factory for a fresh AgentState at the start of a request.

    Args:
        user_input:      The raw user query.
        max_iterations: Guard value — scheduler is not re-entered more than this many times.

    Returns:
        A TypedDict optimised for direct LangGraph state updates.
    """
    return AgentState(
        user_input=user_input,
        intent="",                     # filled by scheduler_node
        pending_tasks=[],              # filled by scheduler_node
        running_tasks=[],              # filled by executor_node
        done_tasks=[],                 # filled by executor_node
        failed_tasks=[],               # filled by executor_node
        review_decision="",            # filled by reviewer_node
        report="",                     # filled by reporter_node
        iteration=0,
        max_iterations=max_iterations,
        error=None,
    )
