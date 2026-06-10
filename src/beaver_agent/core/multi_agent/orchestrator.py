"""Multi-agent orchestrator — LangGraph facade.

This module is the public API for multi-agent execution in beaver-agent.
It ships two backends:

* **langgraph** (default): uses ``beaver_agent.core.graph.graph.run_graph()``
* **legacy**:     the original Scheduler→WorkerPool→Reviewer→Reporter pipeline
                  (activated by passing ``backend="legacy"`` or when
                  ``LANGGRAPH_ENABLED=0`` is set in the environment).

The facade is thread-safe and holds no state — all state lives in the
LangGraph checkpointer SQLite file.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

__all__ = ["MultiAgentOrchestrator"]


class MultiAgentOrchestrator:
    """High-level orchestrator for the beaver-agent multi-agent pipeline.

    Attributes:
        backend:  "langgraph" (default) or "legacy".

    Example::

        orchestrator = MultiAgentOrchestrator()
        report = orchestrator.run("帮我审查 /tmp/foo.py 的代码")
        print(report)
    """

    def __init__(
        self,
        backend: str | None = None,
        **kwargs: Any,
    ) -> None:
        if backend is None:
            backend = os.getenv("LANGGRAPH_ENABLED", "langgraph").strip().lower()

        self._backend = backend
        self._legacy: Any = None   # lazy import

        if self._backend == "legacy":
            self._init_legacy(**kwargs)
        else:
            logger.info("orchestrator_init", backend="langgraph")

    # ─── Public API ────────────────────────────────────────────────────────────

    def run(self, user_input: str, timeout: float = 120.0) -> str:
        """End-to-end multi-agent execution for a user request.

        Args:
            user_input: Natural-language description of the task.
            timeout:    Max seconds to wait (passed through; not enforced at this level).

        Returns:
            A user-facing markdown report string.
        """
        if self._backend == "legacy":
            return self._legacy_run(user_input, timeout=timeout)

        return self._langgraph_run(user_input)

    def status(self) -> dict[str, Any]:
        """Return a snapshot of orchestration state.

        For the langgraph backend this returns the current checkpointer metadata.
        For the legacy backend it delegates to ``WorkerPool.status()``.
        """
        if self._backend == "legacy":
            return self._legacy.status()

        from beaver_agent.core.graph.checkpointer import get_checkpoint_dir
        checkpoint_dir = str(get_checkpoint_dir() or "not yet initialized")
        return {
            "backend": "langgraph",
            "checkpointer_dir": checkpoint_dir,
        }

    def shutdown(self) -> None:
        """Stop the legacy worker pool (no-op for langgraph backend)."""
        if self._backend == "legacy" and self._legacy is not None:
            self._legacy.shutdown()

    # ─── LangGraph backend ─────────────────────────────────────────────────────

    def _langgraph_run(self, user_input: str) -> str:
        from beaver_agent.core.graph.graph import run_graph

        result = run_graph(user_input)
        report = result.get("report", "")
        error  = result.get("error")

        if error and not report:
            return f"❌ {error}"

        return report

    # ─── Legacy backend ────────────────────────────────────────────────────────

    def _init_legacy(self, **kwargs: Any) -> None:
        logger.warning("orchestrator_using_legacy_backend")
        from beaver_agent.core.multi_agent.agent import (
            ReporterAgent,
            ReviewerAgent,
            SchedulerAgent,
        )
        from beaver_agent.core.multi_agent.bus import EventBus
        from beaver_agent.core.multi_agent.inbox import Inbox
        from beaver_agent.core.multi_agent.pool import WorkerPool

        inbox = kwargs.get("inbox") or Inbox()
        bus   = kwargs.get("bus")   or EventBus()

        self._legacy = _LegacyOrchestrator(
            scheduler=SchedulerAgent(inbox=inbox, bus=bus),
            pool=WorkerPool(inbox=inbox, bus=bus, **kwargs),
            reviewer=ReviewerAgent(inbox=inbox, bus=bus),
            reporter=ReporterAgent(inbox=inbox, bus=bus),
        )

    def _legacy_run(self, user_input: str, timeout: float) -> str:
        return self._legacy.run(user_input, timeout=timeout)


# ─── Legacy orchestrator (mirrors the original MultiAgentOrchestrator) ──────────


class _LegacyOrchestrator:
    """Thin wrapper around the old Scheduler/WorkerPool/Reviewer/Reporter pipeline."""

    def __init__(
        self,
        scheduler,  # SchedulerAgent
        pool,       # WorkerPool
        reviewer,   # ReviewerAgent
        reporter,   # ReporterAgent
    ) -> None:
        self.scheduler = scheduler
        self.pool      = pool
        self.reviewer  = reviewer
        self.reporter  = reporter

    def run(self, user_input: str, timeout: float = 120.0) -> str:

        tasks = self.scheduler.decompose(user_input)
        if not tasks:
            return "❌ 无法解析任务，请尝试更明确地描述需求。"

        self.pool.inbox.submit_batch(tasks)
        self.pool.start()

        done = self._wait_for_completion(timeout=timeout)

        from beaver_agent.core.multi_agent.protocols import Task as ProtoTask
        review_task = ProtoTask(input={"user_input": user_input})
        decision = self.reviewer.execute(review_task)

        report_task = ProtoTask(input={"decision": decision})
        report = self.reporter.execute(report_task)

        logger.info(
            "legacy_orchestrator_run_end",
            tasks_total=len(tasks),
            tasks_done=len(done),
            decision=decision.get("decision"),
        )
        return report.get("report", "任务执行完成，但没有生成报告。")

    def _wait_for_completion(self, timeout: float):
        import time as _time

        start = _time.monotonic()
        last  = -1

        while _time.monotonic() - start < timeout:
            pending  = len(self.pool.inbox.list_pending())
            assigned = len(self.pool.inbox.list_assigned())
            current  = pending + assigned

            if current != last:
                logger.debug("wait_progress", pending=pending, assigned=assigned)
                last = current

            if pending == 0 and assigned == 0:
                return self.pool.inbox.list_done()

            _time.sleep(0.5)

        logger.warning("wait_timeout", timeout=timeout)
        return self.pool.inbox.list_done()

    def shutdown(self) -> None:
        self.pool.shutdown()

    def status(self) -> dict[str, Any]:
        return {
            "backend": "legacy",
            "pool": self.pool.status(),
        }
