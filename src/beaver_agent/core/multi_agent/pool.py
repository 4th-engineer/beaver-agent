"""Persistent worker pool manager for multi-agent execution."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

import os

import structlog

from beaver_agent.core.multi_agent.agent import WorkerAgent
from beaver_agent.core.multi_agent.bus import EventBus
from beaver_agent.core.multi_agent.inbox import Inbox

logger = structlog.get_logger()

__all__ = ["WorkerPool"]


class WorkerPool:
    """Manages a pool of persistent WorkerAgent instances.

    The pool grows on demand up to ``max_workers`` and shrinks to ``min_workers``
    when idle. Workers are daemons that poll the shared inbox continuously.
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
        self.min_workers = min_workers
        # Default: scale with CPU cores (no hard cap)
        self.max_workers = max_workers if max_workers is not None else (os.cpu_count() or 4)

        self._workers: Dict[str, WorkerAgent] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # Keep min_workers running at all times
        self._scale_up_to_min()

    # ─── Pool scaling ────────────────────────────────────────────────────────

    def _scale_up_to_min(self) -> None:
        """Ensure at least min_workers are running."""
        self._ensure_count(self.min_workers)

    def _ensure_count(self, target: int) -> List[WorkerAgent]:
        """Grow the pool to ``target`` workers if below the limit."""
        started: List[WorkerAgent] = []
        with self._lock:
            while len(self._workers) < target:
                worker = WorkerAgent(inbox=self.inbox, bus=self.bus)
                self._workers[worker.agent_id] = worker
                started.append(worker)

        for w in started:
            w.start()
            logger.info("worker_added", worker_id=w.agent_id, pool_size=len(self._workers))

        return started

    def _add_worker(self) -> Optional[WorkerAgent]:
        """Add one worker if below max_workers. Returns the new worker or None."""
        with self._lock:
            if len(self._workers) >= self.max_workers:
                return None
            worker = WorkerAgent(inbox=self.inbox, bus=self.bus)
            self._workers[worker.agent_id] = worker

        worker.start()
        logger.info("worker_added_on_demand", worker_id=worker.agent_id, pool_size=len(self._workers))
        return worker

    def _remove_worker(self, worker_id: str) -> None:
        """Stop and remove a specific worker."""
        with self._lock:
            worker = self._workers.pop(worker_id, None)

        if worker:
            worker.stop()
            logger.info("worker_removed", worker_id=worker_id, pool_size=len(self._workers))

    def _cleanup_idle(self) -> None:
        """Remove workers above min_workers if they have been idle too long."""
        with self._lock:
            idle_workers = [
                wid
                for wid, w in self._workers.items()
                if w.info.status == "idle"
            ]
            excess = len(self._workers) - self.min_workers
            to_remove = idle_workers[:excess]

        for wid in to_remove:
            self._remove_worker(wid)

    # ─── Lifecycle ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the pool (called automatically by __init__)."""
        logger.info(
            "pool_started",
            min_workers=self.min_workers,
            max_workers=self.max_workers,
            workers=len(self._workers),
        )

    def shutdown(self, timeout: float = 10.0) -> None:
        """Stop all workers gracefully and wait for them to finish."""
        self._stop_event.set()

        with self._lock:
            worker_ids = list(self._workers.keys())

        for wid in worker_ids:
            self._remove_worker(wid)

        logger.info("pool_shutdown", workers_shutdown=len(worker_ids))

    # ─── Status ─────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Return a snapshot of pool health."""
        with self._lock:
            return {
                "pool_size": len(self._workers),
                "min_workers": self.min_workers,
                "max_workers": self.max_workers,
                "workers": [
                    {
                        "id": w.agent_id,
                        "status": w.info.status,
                        "current_task_id": w.info.current_task_id,
                        "tasks_completed": w.info.tasks_completed,
                        "tasks_failed": w.info.tasks_failed,
                    }
                    for w in self._workers.values()
                ],
            }

    def stats(self) -> Dict[str, int]:
        """Return aggregate stats across all workers."""
        with self._lock:
            return {
                "total_workers": len(self._workers),
                "busy_workers": sum(1 for w in self._workers.values() if w.info.status == "busy"),
                "idle_workers": sum(1 for w in self._workers.values() if w.info.status == "idle"),
                "total_completed": sum(w.info.tasks_completed for w in self._workers.values()),
                "total_failed": sum(w.info.tasks_failed for w in self._workers.values()),
            }
