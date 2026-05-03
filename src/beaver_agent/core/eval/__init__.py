"""Beaver Agent Evaluation Harness — 6 core components."""

from .harness import BeaverHarness
from .task import Task, Benchmark, TaskResult
from .runner import Runner
from .loader import BenchmarkRegistry, get_benchmark_registry, register_benchmark, list_benchmarks
from .metrics import Scorer, ExactMatchScorer, SimilarityScorer, CodeExecutionScorer, CodeReviewScorer, get_scorer

__all__ = [
    "BeaverHarness",
    "Task",
    "Benchmark",
    "TaskResult",
    "Runner",
    "BenchmarkRegistry",
    "get_benchmark_registry",
    "register_benchmark",
    "list_benchmarks",
    "Scorer",
    "ExactMatchScorer",
    "SimilarityScorer",
    "CodeExecutionScorer",
    "CodeReviewScorer",
    "get_scorer",
]
