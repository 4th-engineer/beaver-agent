"""Tests for eval metrics module — scorers and strategy constants."""

import pytest
from beaver_agent.core.eval.metrics import (
    ExactMatchScorer,
    SimilarityScorer,
    CodeExecutionScorer,
    CodeReviewScorer,
    get_scorer,
)
from beaver_agent.core.eval.prompting import (
    STRATEGY_MAP,
    CODE_GENERATION_STRATEGY,
    BUG_FIX_STRATEGY,
    CODE_REVIEW_STRATEGY,
    ARCHITECTURE_STRATEGY,
)


class TestExactMatchScorerEdgeCases:
    """Edge case tests for ExactMatchScorer."""

    def test_identical_with_whitespace_variation(self):
        """Leading/trailing whitespace differences are ignored."""
        scorer = ExactMatchScorer()
        score, details = scorer.score("  hello  ", "hello")
        assert score == 1.0
        assert details["exact_match"] is True

    def test_whitespace_only_strings_match(self):
        """Two whitespace-only strings are considered an exact match."""
        scorer = ExactMatchScorer()
        score, details = scorer.score("   ", " ")
        assert score == 1.0

    def test_empty_strings_match(self):
        """Two empty strings are considered an exact match."""
        scorer = ExactMatchScorer()
        score, details = scorer.score("", "")
        assert score == 1.0

    def test_case_sensitive(self):
        """Exact match is case-sensitive."""
        scorer = ExactMatchScorer()
        score, _ = scorer.score("Hello", "hello")
        assert score == 0.0

    def test_newline_handling(self):
        """Different newline representations do not match."""
        scorer = ExactMatchScorer()
        score, _ = scorer.score("line1\nline2", "line1\nline2")
        assert score == 1.0
        score, _ = scorer.score("line1\nline2", "line1\r\nline2")
        assert score == 0.0


class TestSimilarityScorerEdgeCases:
    """Edge case tests for SimilarityScorer."""

    def test_completely_different_strings(self):
        """Completely different strings return low similarity."""
        scorer = SimilarityScorer()
        score, details = scorer.score("abcdefgh", "ijklmnop")
        assert 0.0 <= score <= 0.3

    def test_partially_overlapping(self):
        """Partially overlapping strings return partial similarity."""
        scorer = SimilarityScorer()
        score, details = scorer.score("hello world", "hello")
        assert 0.3 < score < 1.0

    def test_whitespace_normalized(self):
        """Whitespace is included in similarity calculation."""
        scorer = SimilarityScorer()
        score1, _ = scorer.score("hello world", "helloworld")
        score2, _ = scorer.score("hello world", "hello world")
        assert score2 > score1

    def test_empty_prediction_vs_reference(self):
        """Empty prediction vs non-empty reference returns low similarity."""
        scorer = SimilarityScorer()
        score, _ = scorer.score("", "something")
        assert 0.0 <= score <= 0.2

    def test_empty_reference_vs_prediction(self):
        """Non-empty prediction vs empty reference returns low similarity."""
        scorer = SimilarityScorer()
        score, _ = scorer.score("something", "")
        assert 0.0 <= score <= 0.2

    def test_both_empty_returns_one(self):
        """Both strings empty returns similarity of 1.0."""
        scorer = SimilarityScorer()
        score, details = scorer.score("", "")
        assert score == 1.0
        assert details["similarity"] == 1.0


class TestCodeExecutionScorerEdgeCases:
    """Edge case tests for CodeExecutionScorer."""

    def test_multiple_test_cases_partial_pass(self):
        """Score reflects partial pass rate."""
        scorer = CodeExecutionScorer(
            [
                {"input": "x = 2", "expected": "2"},
                {"input": "x = 3", "expected": "3"},
                {"input": "x = 5", "expected": "99"},  # intentionally wrong
            ]
        )
        # code sets result=2, so only first test case passes
        code = "x = 2\nresult = x"
        score, details = scorer.score(code, "")
        assert score == pytest.approx(1 / 3)
        assert details["passed"] == 1
        assert details["total"] == 3

    def test_code_with_no_result_variable(self):
        """Code that runs but sets no 'result' fails the test."""
        scorer = CodeExecutionScorer([{"input": "", "expected": "42"}])
        code = "x = 42  # sets x, not result"
        score, details = scorer.score(code, "")
        # No error is raised by exec(); result just doesn't match
        assert score == 0.0
        assert details["passed"] == 0

    def test_runtime_error_captured_in_errors(self):
        """Runtime errors are captured in the errors list."""
        scorer = CodeExecutionScorer([{"input": "", "expected": ""}])
        code = "raise ValueError('test error')"
        score, details = scorer.score(code, "")
        assert score == 0.0
        assert len(details["errors"]) == 1
        # str(e) of ValueError gives the message, not "ValueError"
        assert "test error" in details["errors"][0]


class TestCodeReviewScorerEdgeCases:
    """Edge case tests for CodeReviewScorer."""

    def test_all_keywords_found(self):
        """Score is 1.0 when all keywords are present."""
        scorer = CodeReviewScorer()
        review = "This has a bug and a security issue and performance problem and readability issue. I recommend fixing it."
        score, details = scorer.score(review, "")
        assert score == 1.0
        assert details["keywords_found"] == 6

    def test_partial_keyword_coverage(self):
        """Score reflects proportion of keywords found."""
        scorer = CodeReviewScorer()
        review = "This has a bug and a security issue."
        score, details = scorer.score(review, "")
        assert 0.0 < score < 1.0
        assert details["keywords_found"] == 3  # bug, security, issue

    def test_case_insensitive(self):
        """Keyword matching is case-insensitive."""
        scorer = CodeReviewScorer()
        score1, _ = scorer.score("this has a BUG", "")
        score2, _ = scorer.score("this has a bug", "")
        assert score1 == score2

    def test_empty_review(self):
        """Empty review scores 0."""
        scorer = CodeReviewScorer()
        score, details = scorer.score("", "")
        assert score == 0.0
        assert details["keywords_found"] == 0


class TestStrategyMap:
    """Tests for STRATEGY_MAP dictionary and built-in strategy constants."""

    def test_strategy_map_has_all_types(self):
        """STRATEGY_MAP contains entries for all 4 task types."""
        assert set(STRATEGY_MAP.keys()) == {
            "code_generation",
            "bug_fix",
            "code_review",
            "architecture",
        }

    def test_code_generation_strategy_fields(self):
        """CODE_GENERATION_STRATEGY has correct name and non-empty template."""
        assert CODE_GENERATION_STRATEGY.name == "code_generation"
        assert len(CODE_GENERATION_STRATEGY.system_template) > 0
        assert "expert Python programmer" in CODE_GENERATION_STRATEGY.system_template

    def test_bug_fix_strategy_fields(self):
        """BUG_FIX_STRATEGY has correct name and non-empty template."""
        assert BUG_FIX_STRATEGY.name == "bug_fix"
        assert len(BUG_FIX_STRATEGY.system_template) > 0
        assert "debugger" in BUG_FIX_STRATEGY.system_template

    def test_code_review_strategy_fields(self):
        """CODE_REVIEW_STRATEGY has correct name and non-empty template."""
        assert CODE_REVIEW_STRATEGY.name == "code_review"
        assert len(CODE_REVIEW_STRATEGY.system_template) > 0
        assert "reviewer" in CODE_REVIEW_STRATEGY.system_template

    def test_architecture_strategy_fields(self):
        """ARCHITECTURE_STRATEGY has correct name and non-empty template."""
        assert ARCHITECTURE_STRATEGY.name == "architecture"
        assert len(ARCHITECTURE_STRATEGY.system_template) > 0
        assert "architect" in ARCHITECTURE_STRATEGY.system_template

    def test_strategy_constants_are_singletons(self):
        """Built-in strategies are the same objects as map values."""
        assert CODE_GENERATION_STRATEGY is STRATEGY_MAP["code_generation"]
        assert BUG_FIX_STRATEGY is STRATEGY_MAP["bug_fix"]
        assert CODE_REVIEW_STRATEGY is STRATEGY_MAP["code_review"]
        assert ARCHITECTURE_STRATEGY is STRATEGY_MAP["architecture"]

    def test_architecture_strategy_in_map(self):
        """ARCHITECTURE_STRATEGY is present in STRATEGY_MAP (was missing from get_scorer map)."""
        assert "architecture" in STRATEGY_MAP

    def test_get_scorer_architecture_defaults_to_similarity(self):
        """get_scorer returns SimilarityScorer for architecture."""
        scorer = get_scorer("architecture")
        assert isinstance(scorer, SimilarityScorer)
