"""Beaver Agent Evaluation Harness — 6 core components."""

from .adapter import BeaverAdapter, MiniMaxAdapter, ModelAdapter, OpenAIAdapter
from .harness import BeaverHarness
from .loader import (
    BenchmarkRegistry,
    TaskLoader,
    get_benchmark_registry,
    list_benchmarks,
    register_benchmark,
)
from .metrics import (
    CodeExecutionScorer,
    CodeReviewScorer,
    ExactMatchScorer,
    Scorer,
    SimilarityScorer,
    get_scorer,
)
from .prompting import (
    ARCHITECTURE_STRATEGY,
    BUG_FIX_STRATEGY,
    CODE_GENERATION_STRATEGY,
    CODE_REVIEW_STRATEGY,
    STRATEGY_MAP,
    PromptStrategy,
    get_strategy,
)
from .runner import Runner
from .task import Benchmark, Task, TaskResult

__all__ = [
    "BeaverHarness",
    "Task",
    "Benchmark",
    "TaskResult",
    "Runner",
    "BenchmarkRegistry",
    "TaskLoader",
    "get_benchmark_registry",
    "register_benchmark",
    "list_benchmarks",
    "Scorer",
    "ExactMatchScorer",
    "SimilarityScorer",
    "CodeExecutionScorer",
    "CodeReviewScorer",
    "get_scorer",
    "ModelAdapter",
    "BeaverAdapter",
    "OpenAIAdapter",
    "MiniMaxAdapter",
    "PromptStrategy",
    "get_strategy",
    "CODE_GENERATION_STRATEGY",
    "BUG_FIX_STRATEGY",
    "CODE_REVIEW_STRATEGY",
    "ARCHITECTURE_STRATEGY",
    "STRATEGY_MAP",
]
