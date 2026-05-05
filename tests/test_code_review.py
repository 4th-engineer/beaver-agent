"""Tests for Code Review Tool"""

import pytest
from unittest.mock import Mock, MagicMock
from beaver_agent.tools.code_review import CodeReviewTool, CodeReviewIssue


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    client = Mock()
    return client


@pytest.fixture
def mock_config():
    """Create a mock config object"""
    config = Mock()
    return config


@pytest.fixture
def code_review_tool(mock_config, mock_llm_client):
    """Create a CodeReviewTool instance with mocked dependencies"""
    return CodeReviewTool(mock_config, mock_llm_client)


class TestCodeReviewIssue:
    """Tests for CodeReviewIssue class"""

    def test_init_stores_fields(self):
        """Test that __init__ stores all fields"""
        issue = CodeReviewIssue(
            severity="major",
            line=42,
            message="Test issue",
            suggestion="Fix this"
        )
        assert issue.severity == "major"
        assert issue.line == 42
        assert issue.message == "Test issue"
        assert issue.suggestion == "Fix this"

    def test_init_optional_suggestion(self):
        """Test that suggestion is optional"""
        issue = CodeReviewIssue(
            severity="minor",
            line=10,
            message="Minor issue"
        )
        assert issue.suggestion is None

    def test_format_with_suggestion(self):
        """Test format() with suggestion"""
        issue = CodeReviewIssue(
            severity="major",
            line=42,
            message="Found bare except",
            suggestion="Use except Exception:"
        )
        result = issue.format()
        assert "🟠" in result
        assert "MAJOR" in result
        assert "42" in result
        assert "Found bare except" in result
        assert "Suggestion:" in result
        assert "Use except Exception:" in result

    def test_format_critical_severity(self):
        """Test format() with critical severity"""
        issue = CodeReviewIssue(
            severity="critical",
            line=1,
            message="Critical issue"
        )
        result = issue.format()
        assert "🔴" in result
        assert "CRITICAL" in result

    def test_format_minor_severity(self):
        """Test format() with minor severity"""
        issue = CodeReviewIssue(
            severity="minor",
            line=5,
            message="Minor issue"
        )
        result = issue.format()
        assert "🟡" in result
        assert "MINOR" in result

    def test_format_suggestion_severity(self):
        """Test format() with suggestion severity"""
        issue = CodeReviewIssue(
            severity="suggestion",
            line=None,
            message="Consider refactoring"
        )
        result = issue.format()
        assert "💡" in result
        assert "SUGGESTION" in result
        assert "Line" not in result  # No line number when line is None

    def test_format_no_line_number(self):
        """Test format() when line is None"""
        issue = CodeReviewIssue(
            severity="major",
            line=None,
            message="File-level issue"
        )
        result = issue.format()
        assert "Line" not in result
        assert "File-level issue" in result


class TestCodeReviewToolInit:
    """Tests for CodeReviewTool initialization"""

    def test_init_stores_config_and_llm(self, code_review_tool, mock_config, mock_llm_client):
        """Test that __init__ stores config and llm_client"""
        assert code_review_tool.config is mock_config
        assert code_review_tool.llm is mock_llm_client

    def test_init_docstring_present(self, code_review_tool):
        """Test that __init__ has a docstring"""
        assert CodeReviewTool.__init__.__doc__ is not None
        assert "Args:" in CodeReviewTool.__init__.__doc__


class TestCodeReviewToolReview:
    """Tests for CodeReviewTool.review()"""

    def test_review_calls_llm(self, code_review_tool, mock_llm_client):
        """Test that review() calls the LLM client"""
        mock_response = Mock()
        mock_response.content = "## Review\n\nAll good"
        mock_llm_client.review_code.return_value = mock_response

        result = code_review_tool.review("def foo(): pass", language="python")

        mock_llm_client.review_code.assert_called_once_with(
            code="def foo(): pass",
            language="python",
            file_path=None
        )
        assert "Review" in result

    def test_review_llm_returns_not_configured(self, code_review_tool, mock_llm_client):
        """Test that review() falls back to _basic_review when LLM not configured"""
        mock_response = Mock()
        mock_response.content = "not configured"
        mock_llm_client.review_code.return_value = mock_response

        result = code_review_tool.review("def foo(): pass", language="python")

        # Should fall back to basic review since content contains "not configured"
        assert "静态检查" in result or "代码审查" in result

    def test_review_empty_response(self, code_review_tool, mock_llm_client):
        """Test that review() falls back to _basic_review on empty response"""
        mock_response = Mock()
        mock_response.content = ""
        mock_llm_client.review_code.return_value = mock_response

        result = code_review_tool.review("x = 1", language="python")

        # Should fall back to basic review since content is empty
        assert "静态检查" in result or "代码审查" in result

    def test_review_exception_returns_error_message(self, code_review_tool, mock_llm_client):
        """Test that review() returns error message when LLM raises exception"""
        mock_llm_client.review_code.side_effect = RuntimeError("API error")

        result = code_review_tool.review("def foo(): pass", language="python")

        # Exception is caught and logged, returns error message
        assert "❌" in result
        assert "Code review failed" in result

    def test_review_with_file_path(self, code_review_tool, mock_llm_client):
        """Test that review() passes file_path to LLM"""
        mock_response = Mock()
        mock_response.content = "## Review\n\nAll good"
        mock_llm_client.review_code.return_value = mock_response

        code_review_tool.review("code", language="python", file_path="src/main.py")

        call_kwargs = mock_llm_client.review_code.call_args[1]
        assert call_kwargs["file_path"] == "src/main.py"

    def test_review_docstring_present(self, code_review_tool):
        """Test that review() has a docstring with Args/Returns sections"""
        assert CodeReviewTool.review.__doc__ is not None
        assert "Args:" in CodeReviewTool.review.__doc__
        assert "Returns:" in CodeReviewTool.review.__doc__


class TestCodeReviewToolBasicReview:
    """Tests for CodeReviewTool._basic_review()"""

    def test_basic_review_no_issues(self, code_review_tool):
        """Test _basic_review() with clean code"""
        code = "def foo():\n    return 42\n"

        result = code_review_tool._basic_review(code, "python", None)

        assert "未发现问题" in result or "✅" in result

    def test_basic_review_finds_todo(self, code_review_tool):
        """Test _basic_review() detects TODO comments"""
        code = "def foo():\n    # TODO: implement this\n    pass\n"

        result = code_review_tool._basic_review(code, "python", None)

        assert "TODO" in result or "发现问题" in result

    def test_basic_review_finds_bare_except(self, code_review_tool):
        """Test _basic_review() detects bare except clauses"""
        code = "try:\n    x = 1\nexcept:\n    pass\n"

        result = code_review_tool._basic_review(code, "python", None)

        assert "bare except" in result.lower() or "裸 except" in result or "发现问题" in result

    def test_basic_review_python_language(self, code_review_tool):
        """Test _basic_review() with python language"""
        code = "# TODO: fix this"
        result = code_review_tool._basic_review(code, "python", "test.py")
        assert "python" in result.lower()

    def test_basic_review_javascript_language(self, code_review_tool):
        """Test _basic_review() with javascript language"""
        code = "var x = 1;"
        result = code_review_tool._basic_review(code, "javascript", "test.js")
        # Should use JS checks, not Python checks
        assert "代码审查" in result

    def test_basic_review_typescript_language(self, code_review_tool):
        """Test _basic_review() with typescript language"""
        code = "const x = 1;"
        result = code_review_tool._basic_review(code, "typescript", "test.ts")
        assert "代码审查" in result

    def test_basic_review_generic_checks(self, code_review_tool):
        """Test _basic_review() runs generic checks for unknown languages"""
        code = "print('hello')"
        result = code_review_tool._basic_review(code, "unknown", None)
        # Generic checks run for any language
        assert "代码审查" in result

    def test_basic_review_file_path_in_result(self, code_review_tool):
        """Test _basic_review() includes file path in output"""
        code = "x = 1"
        result = code_review_tool._basic_review(code, "python", "src/test.py")
        assert "src/test.py" in result

    def test_basic_review_docstring_present(self, code_review_tool):
        """Test that _basic_review() has a docstring"""
        assert CodeReviewTool._basic_review.__doc__ is not None
        assert "Args:" in CodeReviewTool._basic_review.__doc__
        assert "Returns:" in CodeReviewTool._basic_review.__doc__
