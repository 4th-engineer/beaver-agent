"""Tests for BeaverHarness eval components: Runner, BenchmarkRegistry, PromptStrategy, and Scorers."""

import pytest

from beaver_agent.core.eval.harness import BeaverHarness
from beaver_agent.core.eval.runner import Runner
from beaver_agent.core.eval.task import Task, Benchmark, TaskResult
from beaver_agent.core.eval.loader import (
    BenchmarkRegistry,
    TaskLoader,
    get_benchmark_registry,
    register_benchmark,
    list_benchmarks,
)
from beaver_agent.core.eval.prompting import (
    PromptStrategy,
    get_strategy,
    CODE_GENERATION_STRATEGY,
)
from beaver_agent.core.eval.metrics import (
    ExactMatchScorer,
    SimilarityScorer,
    CodeExecutionScorer,
    CodeReviewScorer,
    get_scorer,
)


class TestTaskAndBenchmark:
    """Tests for Task and Benchmark classes."""

    def test_task_creation(self):
        """Test Task can be created with required fields"""
        task = Task(
            id="test-1",
            name="hello world task",
            prompt="Write a hello world function",
            reference="def hello(): return 'hello'",
            task_type="code_generation",
        )
        assert task.id == "test-1"
        assert task.name == "hello world task"
        assert task.prompt == "Write a hello world function"
        assert task.reference == "def hello(): return 'hello'"
        assert task.task_type == "code_generation"

    def test_benchmark_add_task(self):
        """Test adding tasks to a Benchmark"""
        bm = Benchmark(name="test-benchmark")
        task1 = Task(
            id="t1", name="task 1", prompt="p1", reference="r1", task_type="code_generation"
        )
        task2 = Task(id="t2", name="task 2", prompt="p2", reference="r2", task_type="bug_fix")
        bm.add_task(task1)
        bm.add_task(task2)
        assert len(bm.tasks) == 2
        assert bm.get_task("t1") == task1
        assert bm.get_task("t2") == task2

    def test_benchmark_get_task_not_found(self):
        """Test Benchmark.get_task returns None for unknown id"""
        bm = Benchmark(name="empty")
        assert bm.get_task("nonexistent") is None

    def test_benchmark_len(self):
        """Test Benchmark.__len__ returns correct task count"""
        bm = Benchmark(name="len-test")
        assert len(bm) == 0
        bm.add_task(Task(id="t1", name="t1", prompt="p1", task_type="code_generation"))
        assert len(bm) == 1
        bm.add_task(Task(id="t2", name="t2", prompt="p2", task_type="bug_fix"))
        assert len(bm) == 2

    def test_task_result_attributes(self):
        """Test TaskResult dataclass fields and default values"""
        # All fields present
        result_full = TaskResult(
            task_id="test-1",
            success=True,
            prediction="hello world",
            score=0.95,
            metrics={"accuracy": 0.9, "latency_ms": 150},
            error=None,
            duration_ms=250.5,
        )
        assert result_full.task_id == "test-1"
        assert result_full.success is True
        assert result_full.prediction == "hello world"
        assert result_full.score == 0.95
        assert result_full.metrics == {"accuracy": 0.9, "latency_ms": 150}
        assert result_full.error is None
        assert result_full.duration_ms == 250.5

        # Defaults: metrics={}, error=None, duration_ms=0.0
        result_minimal = TaskResult(
            task_id="test-2",
            success=False,
            prediction="",
            score=0.0,
        )
        assert result_minimal.metrics == {}
        assert result_minimal.error is None
        assert result_minimal.duration_ms == 0.0


class TestBenchmarkRegistry:
    """Tests for BenchmarkRegistry and related loader functions."""

    def test_registry_register_and_get(self):
        """Test registering and retrieving a benchmark"""
        registry = BenchmarkRegistry()
        bm = Benchmark(name="test-reg")
        result = registry.register(bm)
        # register returns self for chaining
        assert result is registry
        assert registry.get("test-reg") == bm
        assert registry.get("nonexistent") is None

    def test_registry_list_benchmarks(self):
        """Test listing all registered benchmarks"""
        registry = BenchmarkRegistry()
        registry.register(Benchmark(name="a"))
        registry.register(Benchmark(name="b"))
        names = registry.list_benchmarks()
        assert set(names) == {"a", "b"}

    def test_get_benchmark_registry_singleton(self):
        """Test get_benchmark_registry returns the global singleton"""
        registry = get_benchmark_registry()
        assert registry is get_benchmark_registry()

    def test_register_benchmark_convenience_function(self, tmp_path):
        """Test register_benchmark convenience function"""
        # Create a temp JSON benchmark file
        import json

        benchmark_file = tmp_path / "test.json"
        benchmark_file.write_text(
            json.dumps(
                {
                    "name": "convenience-test",
                    "tasks": [
                        {
                            "id": "t1",
                            "name": "t1",
                            "prompt": "p1",
                            "reference": "r1",
                            "task_type": "code_generation",
                        }
                    ],
                }
            )
        )
        bm = TaskLoader.from_harness_format(str(benchmark_file))
        register_benchmark(bm)
        assert get_benchmark_registry().get("convenience-test") == bm

    def test_list_benchmarks_after_registration(self):
        """Test list_benchmarks returns all registered names"""
        names_before = set(list_benchmarks())
        bm = Benchmark(name="list-test")
        register_benchmark(bm)
        names_after = set(list_benchmarks())
        assert "list-test" in names_after - names_before


class TestTaskLoader:
    """Tests for TaskLoader JSON loading."""

    def test_from_dict_list(self):
        """Test loading tasks from a list of dicts"""
        tasks_data = [
            {
                "id": "d1",
                "name": "task d1",
                "prompt": "p1",
                "reference": "r1",
                "task_type": "code_generation",
            },
            {
                "id": "d2",
                "name": "task d2",
                "prompt": "p2",
                "reference": "r2",
                "task_type": "bug_fix",
            },
        ]
        tasks = TaskLoader.from_dict_list(tasks_data)
        assert len(tasks) == 2
        assert tasks[0].id == "d1"
        assert tasks[1].task_type == "bug_fix"

    def test_from_harness_format(self, tmp_path):
        """Test loading a complete benchmark from JSON"""
        import json

        benchmark_file = tmp_path / "mbpp_sample.json"
        benchmark_file.write_text(
            json.dumps(
                {
                    "name": "mbpp",
                    "description": "MBPP benchmark subset",
                    "tasks": [
                        {
                            "id": "mbpp-1",
                            "name": "return 42",
                            "prompt": "Write a function that returns 42",
                            "reference": "def answer(): return 42",
                            "task_type": "code_generation",
                        },
                        {
                            "id": "mbpp-2",
                            "name": "return hello",
                            "prompt": "Write a function that returns 'hello'",
                            "reference": "def greet(): return 'hello'",
                            "task_type": "code_generation",
                        },
                    ],
                }
            )
        )
        bm = TaskLoader.from_harness_format(str(benchmark_file))
        assert bm.name == "mbpp"
        assert len(bm.tasks) == 2
        assert bm.tasks[0].id == "mbpp-1"


class TestPromptStrategy:
    """Tests for PromptStrategy and get_strategy."""

    def test_build_prompt(self):
        """Test building system and user prompts"""
        strategy = PromptStrategy(
            name="test",
            system_template="You are an expert programmer.",
            user_template="Write code: {prompt}",
        )
        system, user = strategy.build("a sum function")
        assert system == "You are an expert programmer."
        assert user == "Write code: a sum function"

    def test_build_prompt_with_few_shot(self):
        """Test building prompts with few-shot examples"""
        strategy = PromptStrategy(
            name="test",
            system_template="You are an expert.",
            user_template="Task: {prompt}",
            few_shot_examples=[
                {"input": "double 2", "output": "4"},
                {"input": "double 3", "output": "6"},
            ],
        )
        system, user = strategy.build("double 4")
        assert "Example:" in user
        assert "double 2" in user
        assert "Now you:" in user

    def test_get_strategy_code_generation(self):
        """Test get_strategy returns correct strategy for code_generation"""
        strategy = get_strategy("code_generation")
        assert strategy.name == "code_generation"
        assert "expert Python programmer" in strategy.system_template

    def test_get_strategy_bug_fix(self):
        """Test get_strategy returns correct strategy for bug_fix"""
        strategy = get_strategy("bug_fix")
        assert strategy.name == "bug_fix"
        assert "debugger" in strategy.system_template

    def test_get_strategy_unknown_defaults_to_code_generation(self):
        """Test get_strategy defaults to code_generation for unknown types"""
        strategy = get_strategy("unknown_type")
        assert strategy.name == "code_generation"


class TestExactMatchScorer:
    """Tests for ExactMatchScorer."""

    def test_exact_match_positive(self):
        """Test exact match when strings are identical"""
        scorer = ExactMatchScorer()
        score, details = scorer.score("def foo(): pass", "def foo(): pass")
        assert score == 1.0
        assert details["exact_match"] is True

    def test_exact_match_negative(self):
        """Test exact match when strings differ"""
        scorer = ExactMatchScorer()
        score, details = scorer.score("def foo(): pass", "def bar(): pass")
        assert score == 0.0
        assert details["exact_match"] is False

    def test_exact_match_strips_whitespace(self):
        """Test exact match ignores leading/trailing whitespace"""
        scorer = ExactMatchScorer()
        score, details = scorer.score("  def foo(): pass  ", "def foo(): pass")
        assert score == 1.0


class TestSimilarityScorer:
    """Tests for SimilarityScorer."""

    def test_similarity_identical(self):
        """Test similarity is 1.0 for identical strings"""
        scorer = SimilarityScorer()
        score, details = scorer.score("hello world", "hello world")
        assert score == 1.0
        assert details["similarity"] == 1.0

    def test_similarity_different(self):
        """Test similarity is lower for different strings"""
        scorer = SimilarityScorer()
        score, details = scorer.score("hello", "world")
        assert 0.0 <= score <= 1.0
        assert "similarity" in details


class TestCodeExecutionScorer:
    """Tests for CodeExecutionScorer."""

    def test_code_execution_pass(self):
        """Test code execution with passing test case"""
        scorer = CodeExecutionScorer([{"input": "2+2", "expected": "4"}])
        code = "result = 2 + 2"
        score, details = scorer.score(code, "")
        assert score == 1.0
        assert details["passed"] == 1
        assert details["total"] == 1
        assert details["errors"] == []

    def test_code_execution_fail(self):
        """Test code execution with failing test case"""
        scorer = CodeExecutionScorer([{"input": "2+2", "expected": "5"}])
        code = "result = 2 + 2"
        score, details = scorer.score(code, "")
        assert score == 0.0
        assert details["passed"] == 0
        assert details["total"] == 1

    def test_code_execution_syntax_error(self):
        """Test code execution handles syntax errors gracefully"""
        scorer = CodeExecutionScorer([{"input": "", "expected": ""}])
        code = "this is not valid python {{{{"
        score, details = scorer.score(code, "")
        assert score == 0.0
        assert len(details["errors"]) > 0

    def test_code_execution_empty_test_cases(self):
        """Test code execution with no test cases returns 0.0"""
        scorer = CodeExecutionScorer([])
        score, details = scorer.score("result = 1", "")
        assert score == 0.0
        assert details["total"] == 0


class TestCodeReviewScorer:
    """Tests for CodeReviewScorer."""

    def test_code_review_with_keywords(self):
        """Test code review scores higher when keywords are present"""
        scorer = CodeReviewScorer()
        review = "This code has a security issue and a performance bug. I recommend fixing the readability problem."
        score, details = scorer.score(review, "")
        assert details["keywords_found"] >= 4
        assert score > 0.0

    def test_code_review_without_keywords(self):
        """Test code review scores 0 when no keywords present"""
        scorer = CodeReviewScorer()
        review = "This code looks fine."
        score, details = scorer.score(review, "")
        assert details["keywords_found"] == 0
        assert score == 0.0


class TestGetScorer:
    """Tests for get_scorer factory function."""

    def test_get_scorer_code_generation(self):
        """Test get_scorer returns SimilarityScorer for code_generation"""
        scorer = get_scorer("code_generation")
        assert isinstance(scorer, SimilarityScorer)

    def test_get_scorer_bug_fix(self):
        """Test get_scorer returns ExactMatchScorer for bug_fix"""
        scorer = get_scorer("bug_fix")
        assert isinstance(scorer, ExactMatchScorer)

    def test_get_scorer_code_review(self):
        """Test get_scorer returns CodeReviewScorer for code_review"""
        scorer = get_scorer("code_review")
        assert isinstance(scorer, CodeReviewScorer)

    def test_get_scorer_unknown_defaults_to_similarity(self):
        """Test get_scorer defaults to SimilarityScorer for unknown types"""
        scorer = get_scorer("completely_unknown_task")
        assert isinstance(scorer, SimilarityScorer)


class TestRunner:
    """Tests for Runner class (mock adapter, no real LLM calls)."""

    def test_runner_initialization(self):
        """Test Runner initializes with correct defaults"""

        class FakeAdapter:
            def generate(self, prompt):
                return "mock response"

        runner = Runner(FakeAdapter())
        assert runner.max_workers == 4
        assert runner.timeout == 120

    def test_runner_with_custom_workers_and_timeout(self):
        """Test Runner accepts custom max_workers and timeout"""

        class FakeAdapter:
            def generate(self, prompt):
                return "mock"

        runner = Runner(FakeAdapter(), max_workers=8, timeout_per_task=60)
        assert runner.max_workers == 8
        assert runner.timeout == 60

    def test_summarize_results(self):
        """Test summarize_results aggregates correctly"""

        class FakeAdapter:
            def generate(self, prompt):
                return "response"

        runner = Runner(FakeAdapter())
        results = [
            TaskResult(
                task_id="t1",
                success=True,
                prediction="p1",
                score=1.0,
                metrics={},
                duration_ms=100.0,
            ),
            TaskResult(
                task_id="t2",
                success=True,
                prediction="p2",
                score=0.5,
                metrics={},
                duration_ms=200.0,
            ),
            TaskResult(
                task_id="t3",
                success=False,
                prediction="",
                score=0.0,
                error="failed",
                duration_ms=50.0,
            ),
        ]
        summary = runner.summarize_results(results)
        assert summary["total"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["pass_rate"] == pytest.approx(2 / 3)
        assert summary["avg_score"] == pytest.approx((1.0 + 0.5 + 0.0) / 3)
        assert summary["avg_duration_ms"] == pytest.approx((100.0 + 200.0 + 50.0) / 3)


class TestBeaverHarness:
    """Tests for BeaverHarness (mock adapter, no real LLM calls)."""

    def test_harness_initialization(self):
        """Test BeaverHarness initializes correctly"""

        class FakeAdapter:
            def generate(self, prompt):
                return "mock"

        harness = BeaverHarness(FakeAdapter())
        assert harness.adapter is not None
        assert harness.registry is not None

    def test_add_task_returns_self_for_chaining(self):
        """Test add_task returns self (builder pattern)"""

        class FakeAdapter:
            def generate(self, prompt):
                return "mock"

        harness = BeaverHarness(FakeAdapter())
        task = Task(id="t1", name="t1", prompt="p1", reference="r1", task_type="code_generation")
        result = harness.add_task(task)
        assert result is harness

    def test_load_benchmarks_from_directory(self, tmp_path):
        """Test load_benchmarks loads JSON files from a directory"""
        import json

        # Create a benchmark JSON file with all required Task fields
        benchmark_file = tmp_path / "mini.json"
        benchmark_file.write_text(
            json.dumps(
                {
                    "name": "mini",
                    "tasks": [
                        {
                            "id": "m1",
                            "name": "m1",
                            "prompt": "p1",
                            "reference": "r1",
                            "task_type": "code_generation",
                        }
                    ],
                }
            )
        )

        class FakeAdapter:
            def generate(self, prompt):
                return "mock"

        harness = BeaverHarness(FakeAdapter())
        harness.load_benchmarks(str(tmp_path))
        assert "mini" in harness.registry.list_benchmarks()

    def test_run_single_returns_task_result(self):
        """Test run_single executes a task and returns a TaskResult"""

        class FakeAdapter:
            def generate(self, prompt):
                return "hello world"

        harness = BeaverHarness(FakeAdapter())
        task = Task(
            id="single-1",
            name="single task",
            prompt="Say hello",
            reference="hello world",
            task_type="code_generation",
        )
        result = harness.run_single(task)
        assert isinstance(result, TaskResult)
        assert result.task_id == "single-1"
        assert result.success is True
        assert "hello" in result.prediction.lower()

    def test_run_single_with_failing_adapter_returns_failed_result(self):
        """Test run_single returns failed TaskResult when adapter raises"""

        class BrokenAdapter:
            def generate(self, prompt):
                raise RuntimeError("adapter broken")

        harness = BeaverHarness(BrokenAdapter())
        task = Task(
            id="broken-1",
            name="broken task",
            prompt="This will fail",
            reference="something",
            task_type="code_generation",
        )
        result = harness.run_single(task)
        assert isinstance(result, TaskResult)
        assert result.success is False
        assert "adapter broken" in result.error

    def test_benchmark_info_returns_metadata(self):
        """Test benchmark_info returns name, description, task_count, task_types"""

        class FakeAdapter:
            def generate(self, prompt):
                return "mock"

        harness = BeaverHarness(FakeAdapter())
        # Register a dedicated benchmark to avoid interference from other tests
        bm = Benchmark(name="info-test-bm")
        bm.add_task(
            Task(id="b1-t1", name="t1", prompt="p1", reference="r1", task_type="code_generation")
        )
        bm.add_task(Task(id="b1-t2", name="t2", prompt="p2", reference="r2", task_type="bug_fix"))
        harness.register_benchmark(bm)

        info = harness.benchmark_info("info-test-bm")
        assert info["name"] == "info-test-bm"
        assert info["task_count"] == 2
        assert set(info["task_types"]) == {"code_generation", "bug_fix"}

    def test_benchmark_info_unknown_returns_empty_dict(self):
        """Test benchmark_info returns empty dict for unknown benchmark"""

        class FakeAdapter:
            def generate(self, prompt):
                return "mock"

        harness = BeaverHarness(FakeAdapter())
        info = harness.benchmark_info("nonexistent")
        assert info == {}
