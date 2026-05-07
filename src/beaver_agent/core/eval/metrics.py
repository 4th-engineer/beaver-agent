"""Component 4: Scoring / Metrics — how to evaluate predictions."""

from abc import ABC, abstractmethod
import difflib

import structlog

logger = structlog.get_logger()

__all__ = [
    "Scorer",
    "ExactMatchScorer",
    "SimilarityScorer",
    "CodeExecutionScorer",
    "CodeReviewScorer",
    "get_scorer",
]


class Scorer(ABC):
    """Base class for all scoring strategies."""

    @abstractmethod
    def score(self, prediction: str, reference: str, context: dict = None) -> tuple[float, dict]:
        """
        Returns (score, details_dict).
        Score is 0.0-1.0 for most scorers.
        """
        raise NotImplementedError


class ExactMatchScorer(Scorer):
    """Binary exact match - 1.0 if identical, 0.0 otherwise."""

    def score(self, prediction: str, reference: str, context: dict = None) -> tuple[float, dict]:
        """Score prediction against reference using exact string match.

        Args:
            prediction: The predicted output string.
            reference: The expected/reference output string.
            context: Optional context dictionary (unused, for API compatibility).

        Returns:
            A tuple of (score, details) where score is 1.0 for exact match, 0.0 otherwise.
            details contains {"exact_match": bool}.
        """
        match = prediction.strip() == reference.strip()
        return (1.0 if match else 0.0), {"exact_match": match}


class SimilarityScorer(Scorer):
    """Levenshtein-based string similarity."""

    def score(self, prediction: str, reference: str, context: dict = None) -> tuple[float, dict]:
        """Score prediction against reference using string similarity.

        Args:
            prediction: The predicted output string.
            reference: The expected/reference output string.
            context: Optional context dictionary (unused, for API compatibility).

        Returns:
            A tuple of (score, details) where score is 0.0-1.0 based on Levenshtein similarity.
            details contains {"similarity": float}.
        """
        ratio = difflib.SequenceMatcher(None, prediction.strip(), reference.strip()).ratio()
        return ratio, {"similarity": ratio}


class CodeExecutionScorer(Scorer):
    """Execute generated code and check if it passes test cases."""

    def __init__(self, test_cases: list[dict]):
        """Initialize the CodeExecutionScorer with test cases.

        Args:
            test_cases: List of test case dicts, each containing:
                - "input": Input value or code snippet (optional for some scorers)
                - "expected": Expected result string to compare against
                Example: ``[{"input": "2+2", "expected": "4"}]``
        """
        self.test_cases = test_cases

    def score(self, prediction: str, reference: str, context: dict = None) -> tuple[float, dict]:
        """Execute generated code and score against expected test results.

        Args:
            prediction: Python code to execute.
            reference: Expected result string (unused, test_cases define expectations).
            context: Optional dict that may contain "test_cases" key with test definitions.

        Returns:
            A tuple of (score, details) where score is passed/total test cases (0.0-1.0).
            details contains {"passed": int, "total": int, "errors": list[str]}.
        """
        passed = 0
        errors = []
        for tc in self.test_cases:
            try:
                local_vars = {}
                exec(prediction, {}, local_vars)
                result = local_vars.get("result", None)
                if str(result) == str(tc.get("expected", "")):
                    passed += 1
            except Exception as e:
                logger.warning("code_execution_scoring_failed", exc_info=e)
                errors.append(str(e))
        score = passed / len(self.test_cases) if self.test_cases else 0.0
        return score, {"passed": passed, "total": len(self.test_cases), "errors": errors}


class CodeReviewScorer(Scorer):
    """Score code review quality by checking for key elements."""

    def score(self, prediction: str, reference: str, context: dict = None) -> tuple[float, dict]:
        """Score code review quality by keyword coverage.

        Args:
            prediction: The code review text to evaluate.
            reference: Expected keywords or reference text (unused).
            context: Optional context dictionary (unused, for API compatibility).

        Returns:
            A tuple of (score, details) where score is keyword coverage ratio (0.0-1.0).
            details contains {"keyword_coverage": float, "keywords_found": int}.
        """
        keywords = ["bug", "security", "performance", "readability", "issue", "recommend"]
        found = sum(1 for kw in keywords if kw.lower() in prediction.lower())
        coverage = found / len(keywords)
        return coverage, {"keyword_coverage": coverage, "keywords_found": found}


def get_scorer(task_type: str) -> Scorer:
    """Factory function that returns the appropriate Scorer for a task type.

    Args:
        task_type: The type of task to score. Supported values:
            - "code_generation": Uses SimilarityScorer (Levenshtein-based)
            - "bug_fix": Uses ExactMatchScorer (binary pass/fail)
            - "code_review": Uses CodeReviewScorer (keyword coverage)
            - "architecture": Uses SimilarityScorer (Levenshtein-based)

    Returns:
        A Scorer instance appropriate for the given task type.
        Defaults to SimilarityScorer if task_type is not recognized.

    Example:
        >>> scorer = get_scorer("code_generation")
        >>> score, details = scorer.score("def foo(): pass", "def foo(): pass")
        >>> print(score)
        1.0
    """
    return {
        "code_generation": SimilarityScorer(),
        "bug_fix": ExactMatchScorer(),
        "code_review": CodeReviewScorer(),
        "architecture": SimilarityScorer(),
    }.get(task_type, SimilarityScorer())
