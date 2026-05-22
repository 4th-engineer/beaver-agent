"""Base agent classes for multi-agent orchestration."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import structlog

from beaver_agent.core.multi_agent.protocols import Task, TaskStatus, WorkerInfo

logger = structlog.get_logger()

__all__ = [
    "Agent",
    "SchedulerAgent",
    "WorkerAgent",
    "ReviewerAgent",
    "ReporterAgent",
]


class Agent(ABC):
    """Abstract base for all agents in the multi-agent system."""

    def __init__(
        self,
        agent_id: Optional[str] = None,
        inbox: Optional["Inbox"] = None,  # type: ignore[name-defined]
        bus: Optional["EventBus"] = None,  # type: ignore[name-defined]
    ) -> None:
        from beaver_agent.core.multi_agent.inbox import Inbox
        from beaver_agent.core.multi_agent.bus import EventBus

        self.agent_id = agent_id or f"{self.role}_{os.getpid()}"
        self.inbox = inbox or Inbox()
        self.bus = bus or EventBus()
        self.info = WorkerInfo(id=self.agent_id, role=self.role)
        self._stop_event = threading.Event()

    @property
    @abstractmethod
    def role(self) -> str:
        """Agent role string (scheduler, worker, reviewer, reporter)."""

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the agent (can be blocking or background thread)."""
        logger.info("agent_started", agent_id=self.agent_id, role=self.role)
        self.bus.publish("agent_started", {"agent_id": self.agent_id, "role": self.role})

    def stop(self) -> None:
        """Signal the agent to stop gracefully."""
        self._stop_event.set()
        self.info.status = "stopped"
        logger.info("agent_stopped", agent_id=self.agent_id)
        self.bus.publish("agent_stopped", {"agent_id": self.agent_id})

    def is_stopped(self) -> bool:
        """Check if stop has been requested."""
        return self._stop_event.is_set()

    # ─── Task handling ──────────────────────────────────────────────────────

    @abstractmethod
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a single task and return a result dict."""

    def execute_batch(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """Execute multiple tasks sequentially."""
        return [self.execute(t) for t in tasks]


# ─── Scheduler ────────────────────────────────────────────────────────────────


class SchedulerAgent(Agent):
    """Decomposes a user request into tasks and submits them to the inbox.

    This is the entry point for multi-agent execution. It replaces the
    original BeaverAgent intent_parser + task_planner flow.
    """

    role = "scheduler"

    # Intent → TaskType mapping
    INTENT_TO_TASKTYPE = {
        "code_generation": "code_generation",
        "code_review": "code_review",
        "debug": "debug",
        "github_operation": "github_operation",
        "file_operation": "file_operation",
        "terminal_operation": "terminal_operation",
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._intent_parser = self._load_intent_parser()
        self._task_planner = self._load_task_planner()

    def _load_intent_parser(self) -> Any:
        """Lazily import to avoid circular deps."""
        from beaver_agent.core.intent_parser import IntentParser
        return IntentParser()

    def _load_task_planner(self) -> Any:
        from beaver_agent.core.task_planner import TaskPlanner
        return TaskPlanner()

    def decompose(self, user_input: str) -> List[Task]:
        """Turn a user request into a list of executable tasks.

        1. Parse intent
        2. Plan sub-tasks using TaskPlanner
        3. Wrap each sub-task as a Task and assign types
        """
        intent = self._intent_parser.parse(user_input)
        planned = self._task_planner.plan(user_input, intent)

        tasks: List[Task] = []
        for p in planned:
            from beaver_agent.core.multi_agent.protocols import TaskType

            tt = self.INTENT_TO_TASKTYPE.get(intent, TaskType.UNKNOWN)
            task = Task(
                type=TaskType(tt),
                input={
                    "user_input": user_input,
                    "intent": intent,
                    "tool": p.get("tool"),
                    "action": p.get("action"),
                    "params": p.get("params", {}),
                },
            )
            tasks.append(task)

        logger.info("decomposed", agent_id=self.agent_id, intent=intent, task_count=len(tasks))
        return tasks

    def execute(self, task: Task) -> Dict[str, Any]:
        """Scheduler doesn't execute tasks — it only decomposes them."""
        raise NotImplementedError("Scheduler.execute is not used; call decompose() instead")


# ─── Worker ──────────────────────────────────────────────────────────────────


class WorkerAgent(Agent):
    """Pulls tasks from the inbox and executes them using Beaver's tool router.

    Workers run in a persistent pool. Each worker:
    - Polls the inbox for the oldest PENDING task
    - Executes it via the tool router
    - Writes the result back to the inbox
    - Repeats until stopped
    """

    role = "worker"

    def __init__(self, tool_router: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tool_router = tool_router
        self._poll_interval = 1.0  # seconds between inbox polls
        self._poll_thread: Optional[threading.Thread] = None

    def _get_tool_router(self) -> Any:
        """Lazily build tool router (needs config)."""
        if self._tool_router is None:
            from beaver_agent.core.config import BeaverConfig
            from beaver_agent.core.tool_router import ToolRouter
            cfg = BeaverConfig.from_env()
            self._tool_router = ToolRouter(cfg)
        return self._tool_router

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the worker background polling loop."""
        super().start()
        self.info.status = "idle"
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self) -> None:
        """Stop polling and mark worker as stopped."""
        super().stop()
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=5.0)

    # ─── Polling loop ───────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        """Continuously poll the inbox for work until stopped."""
        while not self.is_stopped():
            task = self.inbox.claim_next(self.agent_id)
            if task is None:
                time.sleep(self._poll_interval)
                continue

            self.info.status = "busy"
            self.info.current_task_id = task.id
            self._run_task(task)

            self.info.status = "idle"
            self.info.current_task_id = None

    def _run_task(self, task: Task) -> None:
        """Execute one task end-to-end."""
        tool_router = self._get_tool_router()

        task.start()
        self.inbox.update(task)

        try:
            tool_task = {
                "tool": task.input.get("tool"),
                "action": task.input.get("action"),
                "params": task.input.get("params", {}),
            }
            result = tool_router.route(tool_task)

            task.complete({"result": result, "tool": tool_task["tool"]})
            self.info.tasks_completed += 1
            logger.info("task_done", task_id=task.id, worker_id=self.agent_id)

        except Exception as exc:
            task.fail(str(exc))
            self.info.tasks_failed += 1
            logger.error("task_failed", task_id=task.id, worker_id=self.agent_id, exc=exc)

        self.inbox.update(task)
        self.bus.publish("task_done", {"task_id": task.id, "worker_id": self.agent_id})

    # ─── Task execution interface (required by ABC) ─────────────────────────

    def execute(self, task: Task) -> Dict[str, Any]:
        """Synchronously execute a single task (used for direct dispatch)."""
        self._run_task(task)
        return task.result or {"error": task.error}


# ─── Reviewer ────────────────────────────────────────────────────────────────


class ReviewerAgent(Agent):
    """Collects worker results and makes a go/no-go decision.

    After all workers have completed their tasks, the Reviewer inspects
    the inbox for DONE tasks, evaluates success/failure rates, and decides
    whether to:
    - Proceed to reporting (all tasks succeeded)
    - Retry failed tasks
    - Escalate by raising an error
    """

    role = "reviewer"

    def __init__(self, min_success_rate: float = 0.5, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._min_success_rate = min_success_rate

    def execute(self, task: Task) -> Dict[str, Any]:
        """Review task outcomes and return a decision."""
        done = self.inbox.list_done()
        failed = self.inbox.list_failed()

        total = len(done) + len(failed)
        if total == 0:
            return {"decision": "no_tasks", "summary": "No tasks were executed."}

        success_rate = len(done) / total if total > 0 else 0.0
        all_errors = [t.error for t in failed if t.error]

        if success_rate >= self._min_success_rate:
            decision = "proceed"
            summary = f"{len(done)}/{total} tasks succeeded."
        else:
            decision = "retry"
            summary = f"Only {len(done)}/{total} tasks succeeded. Retrying."

        logger.info(
            "review_decision",
            decision=decision,
            success_rate=success_rate,
            done=len(done),
            failed=len(failed),
        )

        return {
            "decision": decision,
            "summary": summary,
            "success_rate": success_rate,
            "done_count": len(done),
            "failed_count": len(failed),
            "errors": all_errors,
        }


# ─── Reporter ───────────────────────────────────────────────────────────────


class ReporterAgent(Agent):
    """Formats task results into a human-readable response for the user."""

    role = "reporter"

    def execute(self, task: Task) -> Dict[str, Any]:
        """Build a user-facing report from all completed tasks."""
        done = self.inbox.list_done()
        failed = self.inbox.list_failed()

        lines = [f"## 📋 任务执行报告\n"]
        lines.append(f"**完成**: {len(done)} | **失败**: {len(failed)}\n")

        if done:
            lines.append("\n### ✅ 完成的任务\n")
            for t in done:
                tool = t.input.get("tool", "?")
                res = t.result or {}
                lines.append(f"- **{tool}**: {res.get('result', {}).get('summary', 'OK')}")

        if failed:
            lines.append("\n### ❌ 失败的任务\n")
            for t in failed:
                tool = t.input.get("tool", "?")
                lines.append(f"- **{tool}**: {t.error}")

        report = "\n".join(lines)
        logger.info("report_generated", done=len(done), failed=len(failed))
        return {"report": report, "done": len(done), "failed": len(failed)}
