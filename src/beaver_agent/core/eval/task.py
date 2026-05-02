"""Component 1: Task / Benchmark Definition."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """Single evaluation task definition.

    Attributes:
        id: Unique identifier for this task.
        name: Human-readable name for the task.
        task_type: Type of task — one of "code_generation", "bug_fix",
            "code_review", or "architecture".
        prompt: The prompt/text to send to the LLM for evaluation.
        reference: Expected/reference answer or solution (optional).
        metadata: Additional task metadata such as difficulty, tags, etc.
    """
    id: str
    name: str
    task_type: str  # "code_generation" | "bug_fix" | "code_review" | "architecture"
    prompt: str
    reference: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of running a single task.

    Attributes:
        task_id: ID of the task that was run.
        success: Whether the task passed (True) or failed (False).
        prediction: The LLM's output/response for this task.
        score: Numeric score (0.0–1.0) assigned by the scorer.
        metrics: Dict of per-metric scores (e.g., {"accuracy": 0.9}).
        error: Error message string if execution failed, otherwise None.
        duration_ms: Elapsed time in milliseconds for task execution.
    """
    task_id: str
    success: bool
    prediction: str
    score: float
    metrics: dict = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class Benchmark:
    """Collection of tasks forming a benchmark suite.

    Attributes:
        name: Name of the benchmark (e.g., "HumanEval", "MBPP").
        description: Brief description of what this benchmark evaluates.
        tasks: List of Task instances in this benchmark.
    """
    name: str
    description: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> "Benchmark":
        """Add a task to the benchmark.

        Args:
            task: The Task instance to add.

        Returns:
            self for method chaining.
        """
        self.tasks.append(task)
        return self

    def __len__(self) -> int:
        return len(self.tasks)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by its ID.

        Args:
            task_id: Unique identifier of the task to find.

        Returns:
            The Task if found, otherwise None.
        """
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None
