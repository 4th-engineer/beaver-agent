"""Multi-agent orchestrator — wires together Scheduler, WorkerPool, Reviewer, Reporter."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import structlog

from beaver_agent.core.multi_agent.agent import (
    Agent,
    ReporterAgent,
    ReviewerAgent,
    SchedulerAgent,
)
from beaver_agent.core.multi_agent.bus import EventBus
from beaver_agent.core.multi_agent.inbox import Inbox
from beaver_agent.core.multi_agent.pool import WorkerPool
from beaver_agent.core.multi_agent.protocols import Task

logger = structlog.get_logger()

__all__ = ["MultiAgentOrchestrator"]


class MultiAgentOrchestrator:
    """Coordinates Scheduler → WorkerPool → Reviewer → Reporter pipeline.

    Usage::

        orchestrator = MultiAgentOrchestrator()
        response = orchestrator.run("帮我分析这个项目的结构")
    """

    def __init__(
        self,
        inbox: Optional[Inbox] = None,
        bus: Optional[EventBus] = None,
        min_workers: int = 1,
        max_workers: Optional[int] = None,
    ) -> None:
        self.inbox = inbox or Inbox()
        self.bus = bus or EventBus()

        self.scheduler = SchedulerAgent(inbox=self.inbox, bus=self.bus)
        self.pool = WorkerPool(
            inbox=self.inbox,
            bus=self.bus,
            min_workers=min_workers,
            max_workers=max_workers,
        )
        self.reviewer = ReviewerAgent(inbox=self.inbox, bus=self.bus)
        self.reporter = ReporterAgent(inbox=self.inbox, bus=self.bus)

    # ─── Public API ──────────────────────────────────────────────────────────

    def run(self, user_input: str, timeout: float = 120.0) -> str:
        """End-to-end multi-agent execution for a user request.

        1. Scheduler decomposes the request into tasks
        2. Tasks are submitted to the shared inbox
        3. WorkerPool pulls and executes them in parallel
        4. Reviewer evaluates outcomes
        5. Reporter formats the final user-facing response
        """
        logger.info("orchestrator_run_start", input_preview=user_input[:80])

        # Step 1: Decompose
        tasks = self.scheduler.decompose(user_input)
        if not tasks:
            return "我没有解析到具体任务，请尝试更明确地描述你的需求。"

        self.inbox.submit_batch(tasks)
        self.pool.start()

        # Step 2: Wait for workers to drain the queue
        done = self._wait_for_completion(timeout=timeout)

        # Step 3: Review
        from beaver_agent.core.multi_agent.protocols import Task as ProtoTask

        review_task = ProtoTask(
            input={"user_input": user_input},
            type=ProtoTask.type,  # dummy, not used
        )
        decision = self.reviewer.execute(review_task)

        # Step 4: Report
        report_task = ProtoTask(input={"decision": decision})
        report = self.reporter.execute(report_task)

        logger.info(
            "orchestrator_run_end",
            tasks_total=len(tasks),
            tasks_done=len(done),
            decision=decision.get("decision"),
        )

        return report.get("report", "任务执行完成，但没有生成报告。")

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _wait_for_completion(self, timeout: float) -> List[Task]:
        """Block until all submitted tasks are terminal (done/failed) or timeout."""
        start = time.monotonic()
        last_pending_count = -1

        while time.monotonic() - start < timeout:
            pending = len(self.inbox.list_pending())
            assigned = len(self.inbox.list_assigned())

            # Log progress only when something changes
            current = pending + assigned
            if current != last_pending_count:
                logger.debug("wait_progress", pending=pending, assigned=assigned)
                last_pending_count = current

            if pending == 0 and assigned == 0:
                return self.inbox.list_done()

            time.sleep(0.5)

        logger.warning("wait_timeout", timeout=timeout)
        return self.inbox.list_done()

    def shutdown(self) -> None:
        """Stop the worker pool and release resources."""
        self.pool.shutdown()

    def status(self) -> Dict[str, Any]:
        """Return a snapshot of the entire orchestration state."""
        return {
            "inbox": {
                "pending": len(self.inbox.list_pending()),
                "assigned": len(self.inbox.list_assigned()),
                "done": len(self.inbox.list_done()),
                "failed": len(self.inbox.list_failed()),
            },
            "pool": self.pool.status(),
        }
