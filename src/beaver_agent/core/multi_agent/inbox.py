"""Shared task inbox with file-based persistence."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import structlog

from beaver_agent.core.multi_agent.protocols import Task, TaskStatus

logger = structlog.get_logger()

INBOX_VERSION = 1


class Inbox:
    """Thread-safe shared task inbox backed by a JSON file.

    All agents (Scheduler, Workers, Reviewer, Reporter) share the same
    inbox file as the source of truth for task state. File locking via
    ``threading.Lock`` provides safe concurrent access from multiple
    processes (the OS handles cross-process locking; the Python lock
    guards the in-memory copy).
    """

    def __init__(self, inbox_path: Path | None = None) -> None:
        if inbox_path is None:
            inbox_path = Path.home() / ".beaver" / "inbox" / "tasks.json"

        self._path = inbox_path
        self._lock = threading.Lock()
        self._tasks: dict[str, Task] = {}
        self._load()

    # ─── Persistence ────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load tasks from disk, creating the file if it does not exist."""
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                self._tasks = {
                    tid: Task(**tdata) for tid, tdata in raw.get("tasks", {}).items()
                }
                logger.info("inbox_loaded", path=str(self._path), count=len(self._tasks))
            except Exception as exc:
                logger.warning("inbox_load_failed", path=str(self._path), exc=exc)
                self._tasks = {}
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._save()

    def _save(self) -> None:
        """Write current task state to disk atomically."""
        payload = {
            "version": INBOX_VERSION,
            "tasks": {tid: t.model_dump() for tid, t in self._tasks.items()},
        }
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        tmp.replace(self._path)  # atomic on POSIX

    # ─── Task CRUD ──────────────────────────────────────────────────────────

    def submit(self, task: Task) -> Task:
        """Add a new task to the inbox. Returns the task with its assigned ID."""
        with self._lock:
            self._tasks[task.id] = task
            self._save()
        logger.debug("task_submitted", task_id=task.id, type=task.type.value)
        return task

    def submit_batch(self, tasks: list[Task]) -> list[Task]:
        """Submit multiple tasks at once."""
        with self._lock:
            for t in tasks:
                self._tasks[t.id] = t
            self._save()
        logger.debug("batch_submitted", count=len(tasks))
        return tasks

    def get(self, task_id: str) -> Task | None:
        """Retrieve a task by ID."""
        return self._tasks.get(task_id)

    def list_pending(self) -> list[Task]:
        """Return all pending (unassigned) tasks in FIFO order."""
        with self._lock:
            return [
                self._tasks[tid]
                for tid, t in self._tasks.items()
                if t.status == TaskStatus.PENDING
            ]

    def list_assigned(self) -> list[Task]:
        """Return all tasks assigned to any worker."""
        with self._lock:
            return [
                self._tasks[tid]
                for tid, t in self._tasks.items()
                if t.status == TaskStatus.ASSIGNED
            ]

    def list_done(self) -> list[Task]:
        """Return all completed tasks."""
        with self._lock:
            return [t for t in self._tasks.values() if t.status == TaskStatus.DONE]

    def list_failed(self) -> list[Task]:
        """Return all failed tasks."""
        with self._lock:
            return [t for t in self._tasks.values() if t.status == TaskStatus.FAILED]

    def claim_next(self, worker_id: str) -> Task | None:
        """Atomically claim the oldest pending task for a worker.

        Returns the claimed Task, or None if the queue is empty.
        """
        with self._lock:
            pending = sorted(
                [t for tid, t in self._tasks.items() if t.status == TaskStatus.PENDING],
                key=lambda t: t.created_at,
            )
            if not pending:
                return None
            task = pending[0]
            task.assign_to(worker_id)
            self._save()
        logger.info("task_claimed", task_id=task.id, worker_id=worker_id)
        return task

    def update(self, task: Task) -> None:
        """Update a task and persist to disk."""
        with self._lock:
            task.touch()
            self._tasks[task.id] = task
            self._save()

    def clear(self) -> int:
        """Remove all tasks. Returns the number removed."""
        with self._lock:
            count = len(self._tasks)
            self._tasks = {}
            self._save()
        return count
