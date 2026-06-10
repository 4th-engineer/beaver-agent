"""Beaver Agent LangGraph nodes — one per logical Agent role.

Each node is a pure function ``(state: AgentState) -> AgentState``.
They are deliberately free of I/O at the type level so they are
unit-testable without mocking LangGraph internals.
"""

from __future__ import annotations

import structlog

from beaver_agent.core.graph.state import AgentState
from beaver_agent.core.intent_parser import IntentParser
from beaver_agent.core.multi_agent.protocols import Task, TaskStatus, TaskType
from beaver_agent.core.task_planner import TaskPlanner
from beaver_agent.core.tool_router import ToolRouter

logger = structlog.get_logger(__name__)

# ─── Intent → TaskType mapping (mirrors old SchedulerAgent) ────────────────────

_INTENT_TO_TT: dict[str, TaskType] = {
    "code_generation": TaskType.CODE_GENERATION,
    "code_review": TaskType.CODE_REVIEW,
    "debug": TaskType.DEBUG,
    "github_operation": TaskType.GITHUB_OPERATION,
    "file_operation": TaskType.FILE_OPERATION,
    "terminal_operation": TaskType.TERMINAL_OPERATION,
}


# ──────────────────────────────────────────────────────────────────────────────
# SCHEDULER NODE
# ──────────────────────────────────────────────────────────────────────────────

def scheduler_node(state: AgentState) -> AgentState:
    """Decompose the user request into a task list.

    Reads:  ``state["user_input"]``
    Writes: ``state["intent"]``, ``state["pending_tasks"]``

    Raises:
        ValueError if no tasks can be extracted.
    """
    user_input = state["user_input"]
    intent_parser = IntentParser()
    task_planner = TaskPlanner()

    intent = intent_parser.parse(user_input)
    planned = task_planner.plan(user_input, intent)

    if not planned:
        raise ValueError(f"No tasks generated for intent={intent!r}. Provide a more specific request.")

    tasks: list[Task] = []
    for p in planned:
        tt = _INTENT_TO_TT.get(intent, TaskType.UNKNOWN)
        task = Task(
            type=tt,
            input={
                "user_input": user_input,
                "intent": intent,
                "tool": p.get("tool"),
                "action": p.get("action"),
                "params": p.get("params", {}),
            },
        )
        tasks.append(task)

    logger.info("scheduler_node_done", intent=intent, task_count=len(tasks))

    return {
        **state,
        "intent": intent,
        "pending_tasks": tasks,
        "running_tasks": [],
        "done_tasks": [],
        "failed_tasks": [],
        "review_decision": "",
        "report": "",
    }


# ──────────────────────────────────────────────────────────────────────────────
# EXECUTOR NODE
# ──────────────────────────────────────────────────────────────────────────────

def executor_node(state: AgentState) -> AgentState:
    """Run all pending tasks in parallel and update task lists.

    This node replaces the WorkerPool polling loop with a single synchronous
    pass. The LangGraph loop (not this node) provides iteration — this node
    is called once per iteration round.

    Reads:  ``state["pending_tasks"]``
    Writes: ``state["pending_tasks"]`` (shrinks to []), ``state["running_tasks"]``,
            ``state["done_tasks"]``, ``state["failed_tasks"]``
    """
    pending = list(state["pending_tasks"])
    if not pending:
        return state  # nothing to do

    router = _build_router()
    done: list[Task] = []
    failed: list[Task] = []

    for task in pending:
        task.status = TaskStatus.RUNNING
        try:
            tool_task = {
                "tool": task.input.get("tool"),
                "action": task.input.get("action"),
                "params": task.input.get("params", {}),
            }
            result = router.route(tool_task)
            task.complete({"result": result, "tool": tool_task["tool"]})
            done.append(task)
            logger.debug("task_done_in_executor", task_id=task.id, tool=tool_task["tool"])
        except Exception as exc:  # noqa: PERF203
            task.fail(str(exc))
            failed.append(task)
            logger.error("task_failed_in_executor", task_id=task.id, exc=exc)

    return {
        **state,
        "pending_tasks": [],
        "running_tasks": [],
        "done_tasks": list(state["done_tasks"]) + done,
        "failed_tasks": list(state["failed_tasks"]) + failed,
    }


def _build_router() -> ToolRouter:
    from beaver_agent.core.config import BeaverConfig
    return ToolRouter(BeaverConfig.from_env())


# ──────────────────────────────────────────────────────────────────────────────
# REVIEWER NODE
# ──────────────────────────────────────────────────────────────────────────────

def reviewer_node(state: AgentState) -> AgentState:
    """Inspect task outcomes and set ``state["review_decision"]``.

    Decision rules (mirrors old ReviewerAgent):
      - ``"proceed"``  — at least 50 % of tasks succeeded
      - ``"retry"``    — fewer than 50 % succeeded but iterations remain
      - ``"no_tasks"`` — no tasks were executed at all

    Reads:  ``state["done_tasks"]``, ``state["failed_tasks"]``,
            ``state["iteration"]``, ``state["max_iterations"]``
    Writes: ``state["review_decision"]``
    """
    done = list(state["done_tasks"])
    failed = list(state["failed_tasks"])
    total = len(done) + len(failed)

    iteration = state["iteration"]
    max_iter = state["max_iterations"]

    if total == 0:
        decision = "no_tasks"
        logger.info("reviewer_decision", decision=decision)
        return {**state, "review_decision": decision}

    success_rate = len(done) / total
    if success_rate >= 0.5:
        decision = "proceed"
    elif iteration < max_iter:
        decision = "retry"
    else:
        decision = "proceed"  # forced proceed on final iteration
        logger.warning("reviewer_max_iterations_reached", iteration=iteration)

    logger.info(
        "reviewer_decision",
        decision=decision,
        success_rate=success_rate,
        done=len(done),
        failed=len(failed),
    )
    return {**state, "review_decision": decision}


# ──────────────────────────────────────────────────────────────────────────────
# REPORTER NODE
# ──────────────────────────────────────────────────────────────────────────────

def reporter_node(state: AgentState) -> AgentState:
    """Format task results into a user-facing markdown report.

    Reads:  ``state["done_tasks"]``, ``state["failed_tasks"]``
    Writes: ``state["report"]``
    """
    done = list(state["done_tasks"])
    failed = list(state["failed_tasks"])

    lines = ["## 📋 任务执行报告\n"]
    lines.append(f"**完成**: {len(done)} | **失败**: {len(failed)}\n")

    if done:
        lines.append("\n### ✅ 完成的任务\n")
        for t in done:
            tool = t.input.get("tool", "?")
            res = t.result or {}
            summary = res.get("result", {}).get("summary", "OK") if isinstance(res.get("result"), dict) else str(res.get("result", "OK"))
            lines.append(f"- **{tool}**: {summary}")

    if failed:
        lines.append("\n### ❌ 失败的任务\n")
        for t in failed:
            tool = t.input.get("tool", "?")
            lines.append(f"- **{tool}**: {t.error}")

    report = "\n".join(lines)
    logger.info("report_generated", done=len(done), failed=len(failed))
    return {**state, "report": report}
