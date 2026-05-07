"""Component 5: Data Loader — loading and parsing benchmark datasets."""

import json
import structlog
from pathlib import Path

from .task import Task, Benchmark

logger = structlog.get_logger()

__all__ = [
    "TaskLoader",
    "BenchmarkRegistry",
    "get_benchmark_registry",
    "register_benchmark",
    "list_benchmarks",
]


class TaskLoader:
    """Loads tasks from various sources (JSON, YAML, Python dict)."""

    @staticmethod
    def from_json_file(path: str) -> list[Task]:
        """Load tasks from a JSON file."""
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            logger.error("task_loader_file_read_failed", path=path, exc_info=e)
            return []
        return [Task(**item) for item in data.get("tasks", [])]

    @staticmethod
    def from_dict_list(tasks_data: list[dict]) -> list[Task]:
        """Load tasks from a list of dictionaries."""
        return [Task(**td) for td in tasks_data]

    @staticmethod
    def from_harness_format(file_path: str) -> Benchmark:
        """Load a complete benchmark from a single JSON file."""
        try:
            with open(file_path) as f:
                data = json.load(f)
        except Exception as e:
            logger.error("harness_format_file_read_failed", path=file_path, exc_info=e)
            raise
        benchmark = Benchmark(
            name=data.get("name", "benchmark"),
            description=data.get("description", ""),
        )
        for td in data.get("tasks", []):
            benchmark.add_task(Task(**td))
        return benchmark


class BenchmarkRegistry:
    """Discovers and registers built-in + custom benchmarks."""

    def __init__(self) -> None:
        """Initialize BenchmarkRegistry with empty internal benchmark map."""
        self._benchmarks: dict[str, Benchmark] = {}

    def register(self, benchmark: Benchmark) -> "BenchmarkRegistry":
        """Register a benchmark with the global registry.

        Args:
            benchmark: The Benchmark instance to register.

        Returns:
            self, to allow method chaining.

        Example:
            >>> registry = BenchmarkRegistry()
            >>> registry.register(my_benchmark)
        """
        self._benchmarks[benchmark.name] = benchmark
        return self

    def get(self, name: str) -> Benchmark | None:
        """Retrieve a registered benchmark by name.

        Args:
            name: The name of the benchmark to retrieve.

        Returns:
            The Benchmark if found, otherwise None.
        """
        return self._benchmarks.get(name)

    def list_benchmarks(self) -> list[str]:
        """List all registered benchmark names.

        Returns:
            A list of benchmark names currently in the registry.
        """
        return list(self._benchmarks.keys())

    def load_from_directory(self, dir_path: str) -> "BenchmarkRegistry":
        """Load all .json benchmark files from a directory."""
        p = Path(dir_path)
        for fp in p.glob("*.json"):
            try:
                bm = TaskLoader.from_harness_format(str(fp))
                self.register(bm)
            except Exception as e:
                logger.warning("skipped_invalid_benchmark_file", path=str(fp), exc_info=e)
        return self


# Global registry
_benchmark_registry = BenchmarkRegistry()


def get_benchmark_registry() -> BenchmarkRegistry:
    """Get the global BenchmarkRegistry singleton instance.

    Returns:
        The global BenchmarkRegistry used for storing and retrieving
        registered benchmarks across the application.

    Example:
        >>> registry = get_benchmark_registry()
        >>> names = registry.list_benchmarks()
    """
    return _benchmark_registry


def register_benchmark(benchmark: Benchmark) -> None:
    """Register a benchmark with the global registry (convenience function).

    Args:
        benchmark: The Benchmark instance to register.

    Returns:
        None. The benchmark is registered in the global BenchmarkRegistry
        singleton and can be retrieved via ``get_benchmark_registry()`` or
        ``list_benchmarks()``.

    Example:
        >>> register_benchmark(my_benchmark)
    """
    _benchmark_registry.register(benchmark)


def list_benchmarks() -> list[str]:
    """List all benchmark names registered in the global registry.

    Returns:
        A list of all registered benchmark names.

    Example:
        >>> names = list_benchmarks()
        >>> print(names)
        ['humaneval', 'mbpp', 'custom']
    """
    return _benchmark_registry.list_benchmarks()
