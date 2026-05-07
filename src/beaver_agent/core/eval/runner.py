"""Component 6: Runner / Evaluator — orchestrates task execution and result collection."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import structlog

from .task import Task, TaskResult
from .adapter import ModelAdapter
from .prompting import get_strategy
from .metrics import get_scorer
from .loader import get_benchmark_registry

logger = structlog.get_logger()

__all__ = ["Runner"]


class Runner:
    """Executes tasks through the adapter and collects results."""

    def __init__(
        self,
        adapter: ModelAdapter,
        max_workers: int = 4,
        timeout_per_task: int = 120,
    ):
        """Initialize the Runner with a model adapter and execution settings.

        Args:
            adapter: A ModelAdapter instance (e.g., BeaverAdapter) used to
                generate LLM responses for each task.
            max_workers: Maximum number of tasks to run concurrently (default: 4).
            timeout_per_task: Per-task timeout in seconds (default: 120). Tasks
                that exceed this limit return a TaskResult with an error.

        Attributes:
            adapter: The model adapter used for generation.
            max_workers: Concurrency limit for task execution.
            timeout: Per-task timeout in seconds.
        """
        self.adapter = adapter
        self.max_workers = max_workers
        self.timeout = timeout_per_task

    def run_task(self, task: Task) -> TaskResult:
        """Run a single task and return the result.

        Args:
            task: The Task to execute (contains prompt, reference, task_type).

        Returns:
            A TaskResult with prediction, score, metrics, and duration.
            On exception, returns TaskResult with success=False and error message.
        """
        start = time.time()
        try:
            # Build prompt using strategy
            strategy = get_strategy(task.task_type)
            system_prompt, user_prompt = strategy.build(task.prompt)

            # Generate via adapter
            full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
            prediction = self.adapter.generate(full_prompt)

            # Score
            scorer = get_scorer(task.task_type)
            score, metric_details = scorer.score(prediction, task.reference)

            duration_ms = (time.time() - start) * 1000
            return TaskResult(
                task_id=task.id,
                success=True,
                prediction=prediction,
                score=score,
                metrics=metric_details,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.error("task_execution_failed", task_id=task.id, exc_info=e)
            return TaskResult(
                task_id=task.id,
                success=False,
                prediction="",
                score=0.0,
                error=str(e),
                duration_ms=duration_ms,
            )

    def run_benchmark(self, benchmark_name: str) -> list[TaskResult]:
        """Run all tasks in a benchmark with per-task timeout.

        Args:
            benchmark_name: Name of the benchmark to run (must be registered).

        Returns:
            A list of TaskResult objects, one per task in the benchmark.

        Raises:
            ValueError: If the benchmark is not found in the registry.
        """
        registry = get_benchmark_registry()
        benchmark = registry.get(benchmark_name)
        if not benchmark:
            raise ValueError(f"Benchmark '{benchmark_name}' not found")

        logger.info("benchmark_started", benchmark=benchmark_name, task_count=len(benchmark.tasks))
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.run_task, task): task for task in benchmark.tasks}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result(timeout=self.timeout)
                    results.append(result)
                except TimeoutError:
                    logger.warning("task_timeout", task_id=task.id, timeout_s=self.timeout)
                    results.append(TaskResult(
                        task_id=task.id,
                        success=False,
                        prediction="",
                        score=0.0,
                        error=f"Task timed out after {self.timeout}s",
                        duration_ms=self.timeout * 1000,
                    ))

        logger.info("benchmark_completed", benchmark=benchmark_name, result_count=len(results))
        return results

    def summarize_results(self, results: list[TaskResult]) -> dict[str, Any]:
        """Aggregate results into a summary dict.

        Args:
            results: List of TaskResult objects from a benchmark run.

        Returns:
            A dict with keys: total, passed, failed, pass_rate, avg_score,
            avg_duration_ms, and results (the original list).
        """
        total = len(results)
        passed = sum(1 for r in results if r.success)
        avg_score = sum(r.score for r in results) / total if total else 0.0
        avg_duration = sum(r.duration_ms for r in results) / total if total else 0.0

        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total else 0.0,
            "avg_score": avg_score,
            "avg_duration_ms": avg_duration,
            "results": results,
        }
