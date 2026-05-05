"""Beaver Agent - AI Coding Assistant"""

__version__ = "0.1.0"

from beaver_agent.core.agent import BeaverAgent
from beaver_agent.core.config import BeaverConfig, load_config
from beaver_agent.core.llm_client import LLMClient, LLMResponse
from beaver_agent.core.data_store import DataStore, get_data_store, init_data_store
from beaver_agent.core.tool_router import ToolRouter
from beaver_agent.core.intent_parser import IntentParser
from beaver_agent.core.task_planner import TaskPlanner
from beaver_agent.core.skill_manager import SkillManager, Skill
from beaver_agent.core.mcp_manager import MCPManager, MCPTool
from beaver_agent.core.memory.session import SessionMemory
from beaver_agent.core.memory.long_term import LongTermMemory, MemoryCategory, MemoryEntry, MemoryQuery
from beaver_agent.core.eval.harness import BeaverHarness
from beaver_agent.core.eval.task import Task, Benchmark, TaskResult
from beaver_agent.core.eval.runner import Runner
from beaver_agent.core.eval.loader import BenchmarkRegistry, TaskLoader, get_benchmark_registry
from beaver_agent.core.eval.metrics import (
    Scorer,
    ExactMatchScorer,
    SimilarityScorer,
    CodeExecutionScorer,
    CodeReviewScorer,
    get_scorer,
)
from beaver_agent.core.eval.prompting import PromptStrategy, get_strategy
from beaver_agent.core.eval.adapter import BeaverAdapter, OpenAIAdapter, MiniMaxAdapter

__all__ = [
    # Version
    "__version__",
    # Core agent
    "BeaverAgent",
    # Configuration
    "BeaverConfig",
    "load_config",
    # LLM
    "LLMClient",
    "LLMResponse",
    # Data store
    "DataStore",
    "get_data_store",
    "init_data_store",
    # Tool routing
    "ToolRouter",
    # Intent / task parsing
    "IntentParser",
    "TaskPlanner",
    # Skills
    "SkillManager",
    "Skill",
    # MCP
    "MCPManager",
    "MCPTool",
    # Memory
    "SessionMemory",
    "LongTermMemory",
    "MemoryCategory",
    "MemoryEntry",
    "MemoryQuery",
    # Eval harness
    "BeaverHarness",
    "Task",
    "Benchmark",
    "TaskResult",
    "Runner",
    "BenchmarkRegistry",
    "TaskLoader",
    "get_benchmark_registry",
    # Eval metrics
    "Scorer",
    "ExactMatchScorer",
    "SimilarityScorer",
    "CodeExecutionScorer",
    "CodeReviewScorer",
    "get_scorer",
    # Eval prompting
    "PromptStrategy",
    "get_strategy",
    # Eval adapters
    "BeaverAdapter",
    "OpenAIAdapter",
    "MiniMaxAdapter",
]
