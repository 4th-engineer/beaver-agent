"""Multi-Agent communication protocols and data models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task lifecycle status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    """Supported task types for worker agents."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUG = "debug"
    GITHUB_OPERATION = "github_operation"
    FILE_OPERATION = "file_operation"
    TERMINAL_OPERATION = "terminal_operation"
    CODE_ANALYSIS = "code_analysis"
    UNKNOWN = "unknown"


class Task(BaseModel):
    """A unit of work in the shared inbox."""

    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    type: TaskType = TaskType.UNKNOWN
    status: TaskStatus = TaskStatus.PENDING
    assignee: str | None = None  # worker id
    input: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    attempt: int = 0

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow().isoformat()

    def assign_to(self, worker_id: str) -> None:
        """Assign this task to a worker."""
        self.assignee = worker_id
        self.status = TaskStatus.ASSIGNED
        self.touch()

    def start(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.attempt += 1
        self.touch()

    def complete(self, result: dict[str, Any]) -> None:
        """Mark task as done with result."""
        self.result = result
        self.status = TaskStatus.DONE
        self.touch()

    def fail(self, error: str) -> None:
        """Mark task as failed with error message."""
        self.error = error
        self.status = TaskStatus.FAILED
        self.touch()


class WorkerInfo(BaseModel):
    """Metadata for a worker agent."""

    id: str = Field(default_factory=lambda: f"worker_{uuid.uuid4().hex[:8]}")
    role: str = "worker"  # scheduler | worker | reviewer | reporter
    status: str = "idle"  # idle | busy | stopped
    current_task_id: str | None = None
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    tasks_completed: int = 0
    tasks_failed: int = 0


class Message(BaseModel):
    """Agent-to-agent message."""

    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    from_agent: str
    to_agent: str  # "*" means broadcast
    type: str  # task_assigned | task_result | ping | pong | stop
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Pydantic needs to resolve forward references before runtime instantiation
Task.model_rebuild()
WorkerInfo.model_rebuild()
Message.model_rebuild()
