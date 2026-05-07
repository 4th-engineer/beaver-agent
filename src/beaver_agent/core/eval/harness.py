"""BeaverHarness — orchestrates all 6 components into a unified evaluation API."""

from typing import Any, Optional

import structlog

from .task import Task, Benchmark, TaskResult
from .adapter import ModelAdapter
from .runner import Runner
from .loader import get_benchmark_registry

logger = structlog.get_logger()

__all__ = ["BeaverHarness"]


class BeaverHarness:
    """Unified evaluation harness combining all 6 components:

    1. Task/Benchmark Definition — Task, Benchmark, TaskResult
    2. Model Adapter            — ModelAdapter (BeaverAdapter, OpenAIAdapter, ...)
    3. Prompting Strategy       — PromptStrategy per task type
    4. Scoring/Metrics         — Scorer subclasses + get_scorer()
    5. Data Loader             — TaskLoader + BenchmarkRegistry
    6. Runner/Evaluator        — Runner.run_benchmark() + summarize_results()
    """

    def __init__(
        self,
        adapter: ModelAdapter,
        max_workers: int = 4,
        benchmark_dir: Optional[str] = None,
    ):
        """Initialize the BeaverHarness evaluation runner.

        Args:
            adapter: ModelAdapter instance (BeaverAdapter, OpenAIAdapter, or MiniMaxAdapter)
                used to execute LLM calls for each task.
            max_workers: Maximum number of parallel task executions. Defaults to 4.
            benchmark_dir: Optional path to a benchmark directory. If provided, the
                BenchmarkRegistry will load all benchmark tasks from YAML files in
                that directory at initialization. Defaults to None (no benchmarks loaded).

        Example:
            >>> from beaver_agent.core.eval import BeaverHarness, BeaverAdapter
            >>> harness = BeaverHarness(BeaverAdapter(), max_workers=4)
        """
        self.adapter = adapter
        self.runner = Runner(adapter, max_workers=max_workers)
        self.registry = get_benchmark_registry()

        if benchmark_dir:
            logger.debug("loading_benchmarks_from_dir", dir_path=benchmark_dir)
            self.registry.load_from_directory(benchmark_dir)

    def add_task(self, task: Task) -> "BeaverHarness":
        """Add a single task to an in-memory ephemeral benchmark.

        Args:
            task: The Task instance to add to the ephemeral benchmark.

        Returns:
            self — for method chaining (builder pattern).

        Example:
            >>> harness.add_task(Task(id="t1", ...))
            <BeaverHarness>
        """
        if "ephemeral" not in self.registry.list_benchmarks():
            logger.debug("creating_ephemeral_benchmark")
            self.registry.register(Benchmark(name="ephemeral"))
        self.registry.get("ephemeral").add_task(task)
        logger.debug("task_added_to_ephemeral", task_id=task.id)
        return self

    def load_benchmarks(self, dir_path: str) -> "BeaverHarness":
        """Load all .json benchmarks from a directory.

        Args:
            dir_path: Absolute or relative path to a directory containing
                benchmark .json files. Files are loaded by BenchmarkRegistry.

        Returns:
            self — for method chaining (builder pattern).

        Example:
            >>> harness.load_benchmarks("benchmarks/")
        """
        logger.debug("loading_benchmarks", dir_path=dir_path)
        self.registry.load_from_directory(dir_path)
        return self

    def register_benchmark(self, benchmark: Benchmark) -> "BeaverHarness":
        """Register a benchmark with the internal registry.

        Args:
            benchmark: The Benchmark instance to register.

        Returns:
            self — for method chaining.
        """
        self.registry.register(benchmark)
        return self

    def run(
        self,
        benchmark_name: str,
        summarize: bool = True,
    ) -> dict[str, Any] | list[TaskResult]:
        """Run a named benchmark and optionally summarize results.

        Args:
            benchmark_name: Name of the benchmark to run (must be registered).
            summarize: If True, return a summary dict; if False, return raw TaskResult list.

        Returns:
            A summary dict (if summarize=True) or a list of TaskResult objects.
        """
        logger.info("running_benchmark", benchmark_name=benchmark_name, summarize=summarize)
        results = self.runner.run_benchmark(benchmark_name)
        if summarize:
            summary = self.runner.summarize_results(results)
            logger.info("benchmark_completed", benchmark_name=benchmark_name, result_count=len(results))
            return summary
        logger.info("benchmark_completed_raw", benchmark_name=benchmark_name, result_count=len(results))
        return results

    def run_single(self, task: Task) -> TaskResult:
        """Run one task immediately and return its result.

        Args:
            task: The Task to execute (contains prompt, reference, task_type).

        Returns:
            A TaskResult with prediction, score, metrics, and duration.
            On exception, returns TaskResult with success=False and error message.

        Raises:
            See Runner.run_task for task-level exceptions that may propagate.
        """
        logger.debug("running_single_task", task_id=task.id, task_type=task.task_type)
        result = self.runner.run_task(task)
        logger.debug("single_task_completed", task_id=task.id, success=result.success, score=result.score)
        return result

    def list_benchmarks(self) -> list[str]:
        """List all registered benchmark names.

        Returns:
            A list of benchmark name strings.
        """
        return self.registry.list_benchmarks()

    def benchmark_info(self, name: str) -> dict[str, Any]:
        """Get metadata for a registered benchmark.

        Args:
            name: The benchmark name to look up.

        Returns:
            A dict with name, description, task_count, and task_types; or empty dict if not found.
        """
        bm = self.registry.get(name)
        if not bm:
            return {}
        return {
            "name": bm.name,
            "description": bm.description,
            "task_count": len(bm.tasks),
            "task_types": list(set(t.task_type for t in bm.tasks)),
        }
