"""Beaver Agent Evaluation Harness — 6 core components."""

from .harness import BeaverHarness
from .task import Task, Benchmark, TaskResult
from .runner import Runner
from .loader import BenchmarkRegistry, TaskLoader, get_benchmark_registry, register_benchmark, list_benchmarks
from .metrics import Scorer, ExactMatchScorer, SimilarityScorer, CodeExecutionScorer, CodeReviewScorer, get_scorer
from .adapter import ModelAdapter, BeaverAdapter, OpenAIAdapter, MiniMaxAdapter
from .prompting import (
    PromptStrategy,
    get_strategy,
    CODE_GENERATION_STRATEGY,
    BUG_FIX_STRATEGY,
    CODE_REVIEW_STRATEGY,
    ARCHITECTURE_STRATEGY,
    STRATEGY_MAP,
)

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
