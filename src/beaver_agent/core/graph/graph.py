"""Beaver Agent LangGraph — StateGraph builder and entry point.

Usage::

    from beaver_agent.core.graph import build_graph, run_graph

    graph = build_graph()
    result = graph.invoke({"user_input": "帮我审查这个文件的代码"})
    print(result["report"])
"""

from __future__ import annotations

from typing import Literal

import structlog

from beaver_agent.core.graph.checkpointer import get_checkpointer
from beaver_agent.core.graph.nodes import (
    executor_node,
    reporter_node,
    reviewer_node,
    scheduler_node,
)
from beaver_agent.core.graph.state import AgentState, make_initial_state

logger = structlog.get_logger(__name__)


def build_graph(
    checkpointer=None,
    *,
    interrupt_before: list[str] | None = None,
    interrupt_after: list[str] | None = None,
):
    """Build the Beaver Agent StateGraph.

    Args:
        checkpointer:   A LangGraph ``Checkpointer`` instance.
                        Defaults to ``SqliteSaver`` via ``get_checkpointer()``.
        interrupt_before: Node names to interrupt BEFORE (for human-in-the-loop).
        interrupt_after:  Node names to interrupt AFTER (for human-in-the-loop).

    Returns:
        A compiled ``langgraph.graph.StateGraph`` ready for ``.invoke()``.
    """
    from langgraph.graph import StateGraph

    builder = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    builder.add_node("scheduler", _wrap_scheduler(scheduler_node))
    builder.add_node("executor",   _wrap_executor(executor_node))
    builder.add_node("reviewer",   reviewer_node)
    builder.add_node("reporter",   reporter_node)

    # ── Edges ────────────────────────────────────────────────────────────────────
    # Linear flow: scheduler → executor → reviewer → reporter
    builder.add_edge("__start__", "scheduler")
    builder.add_edge("scheduler", "executor")
    builder.add_edge("reviewer",  "reporter")
    builder.add_edge("reporter",  "__end__")

    # Conditional: reviewer can loop back to executor (retry) or go to reporter
    builder.add_conditional_edges(
        "reviewer",
        _retry_router,
        {
            "executor":  "executor",   # retry → bump iteration, re-enter executor
            "reporter":  "reporter",   # proceed / no_tasks → final report
        },
    )

    # ── Checkpointer & interrupts ──────────────────────────────────────────────
    if checkpointer is None:
        checkpointer = get_checkpointer()

    compiled = builder.compile(checkpointer=checkpointer)

    if interrupt_before:
        compiled = compiled.interrupt_before(interrupt_before)
    if interrupt_after:
        compiled = compiled.interrupt_after(interrupt_after)

    logger.info("graph_built", nodes=4)
    return compiled


def _wrap_scheduler(node_fn):
    """Wrap scheduler so a ValueError from it routes to __end__ with an error report."""
    def wrapper(state: AgentState) -> AgentState:
        try:
            return node_fn(state)
        except ValueError as exc:
            logger.error("scheduler_node_failed", exc=exc)
            return {
                **state,
                "report": f"❌ 无法解析任务：{exc}",
                "error": str(exc),
            }
    return wrapper


def _wrap_executor(node_fn):
    """Wrap executor to increment iteration counter on each retry loop."""
    def wrapper(state: AgentState) -> AgentState:
        prev = state.get("iteration", 0)
        result = node_fn(state)
        # If pending_tasks are back, this was a retry — bump iteration
        if result.get("pending_tasks"):
            result["iteration"] = prev + 1
        return result
    return wrapper


def _retry_router(state: AgentState) -> Literal["executor", "reporter"]:
    """Conditional edge router — mirrors should_retry() logic inline."""
    decision = state.get("review_decision", "")
    pending  = state.get("pending_tasks", [])

    if decision == "retry" and pending:
        return "executor"
    return "reporter"


# ──────────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────────

def run_graph(user_input: str, thread_id: str | None = None) -> AgentState:
    """Run the Beaver Agent graph for a single user request.

    Args:
        user_input: The natural-language request.
        thread_id:  Checkpoint thread ID (defaults to a uuid — one-off run).

    Returns:
        The full final ``AgentState`` dict.  The user-facing output is
        ``state["report"]``; ``state["error"]`` is set on fatal failures.
    """
    import uuid

    if thread_id is None:
        thread_id = str(uuid.uuid4())[:8]

    graph = build_graph()
    initial = make_initial_state(user_input)

    config = {"configurable": {"thread_id": thread_id}}

    logger.info("graph_invoked", thread_id=thread_id, input_preview=user_input[:80])

    try:
        result: AgentState = graph.invoke(initial, config=config)
    except Exception as exc:
        logger.error("graph_invoke_failed", thread_id=thread_id, exc=exc)
        return {
            **initial,
            "report": f"❌ Graph execution failed: {exc}",
            "error": str(exc),
        }

    logger.info(
        "graph_completed",
        thread_id=thread_id,
        report_preview=result.get("report", "")[:80],
    )
    return result
