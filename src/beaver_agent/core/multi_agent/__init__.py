"""Multi-Agent orchestration package.

Submodules
----------
protocols : Task, WorkerInfo, Message, TaskStatus, TaskType
inbox     : Shared file-backed task inbox (thread-safe)
bus       : In-process event bus for agent-to-agent signals
agent     : Agent base class + Scheduler/Worker/Reviewer/Reporter
pool      : Worker pool manager
orchestrator : End-to-end multi-agent pipeline coordinator
"""

from beaver_agent.core.multi_agent.protocols import (
    Message,
    Task,
    TaskStatus,
    TaskType,
    WorkerInfo,
)
from beaver_agent.core.multi_agent.inbox import Inbox
from beaver_agent.core.multi_agent.bus import EventBus
from beaver_agent.core.multi_agent.agent import (
    Agent,
    SchedulerAgent,
    WorkerAgent,
    ReviewerAgent,
    ReporterAgent,
)
from beaver_agent.core.multi_agent.pool import WorkerPool
from beaver_agent.core.multi_agent.orchestrator import MultiAgentOrchestrator

__all__ = [
    # Protocols
    "Task",
    "TaskStatus",
    "TaskType",
    "WorkerInfo",
    "Message",
    # Core
    "Inbox",
    "EventBus",
    # Agents
    "Agent",
    "SchedulerAgent",
    "WorkerAgent",
    "ReviewerAgent",
    "ReporterAgent",
    # Pool
    "WorkerPool",
    # Orchestrator
    "MultiAgentOrchestrator",
]
