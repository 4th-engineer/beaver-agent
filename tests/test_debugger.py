"""Tests for Debugger Tool"""

import pytest
from unittest.mock import Mock, MagicMock
from beaver_agent.tools.debugger import DebuggerTool


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
def debugger_tool(mock_config, mock_llm_client):
    """Create a DebuggerTool instance with mocked dependencies"""
    return DebuggerTool(mock_config, mock_llm_client)


class TestDebuggerToolInit:
    """Tests for DebuggerTool initialization"""

    def test_init_stores_config_and_llm(self, debugger_tool, mock_config, mock_llm_client):
        """Test that __init__ stores config and llm_client"""
        assert debugger_tool.config is mock_config
        assert debugger_tool.llm is mock_llm_client

    def test_init_docstring_present(self, debugger_tool):
        """Test that __init__ has a docstring"""
        assert DebuggerTool.__init__.__doc__ is not None
        assert "Args:" in DebuggerTool.__init__.__doc__


class TestAnalyze:
    """Tests for analyze() public method"""

    def test_analyze_with_error_calls_llm(self, debugger_tool, mock_llm_client):
        """Test that analyze() with error calls LLM debug_code"""
        mock_llm_client.debug_code.return_value = Mock(content="Fix the null reference")
        result = debugger_tool.analyze("code", error="NullReferenceException")

        mock_llm_client.debug_code.assert_called_once()
        call_args = mock_llm_client.debug_code.call_args
        assert call_args.kwargs["code"] == "code"
        assert call_args.kwargs["error"] == "NullReferenceException"
        assert call_args.kwargs["language"] == "python"
        assert "NullReferenceException" in result

    def test_analyze_without_error_calls_llm_chat(self, debugger_tool, mock_llm_client):
        """Test that analyze() without error calls LLM chat for code health"""
        mock_llm_client.chat.return_value = Mock(content="Code looks good")
        result = debugger_tool.analyze("code = 1", language="python")

        mock_llm_client.chat.assert_called_once()
        assert "python" in mock_llm_client.chat.call_args[0][0]
        assert "looks good" in result

    def test_analyze_with_custom_language(self, debugger_tool, mock_llm_client):
        """Test that analyze() passes language to LLM"""
        mock_llm_client.debug_code.return_value = Mock(content="Fix JS error")
        debugger_tool.analyze("const x", error="ReferenceError", language="javascript")

        call_args = mock_llm_client.debug_code.call_args
        assert call_args.kwargs["language"] == "javascript"

    def test_analyze_llm_not_configured_falls_back(self, debugger_tool, mock_llm_client):
        """Test that analyze() falls back to basic when LLM returns not configured"""
        mock_llm_client.debug_code.return_value = Mock(content="LLM not configured")
        result = debugger_tool.analyze("code", error="KeyError: 'x'")

        assert "KeyError" in result
        assert "Index out of range" in result or "Key not found in dictionary" in result

    def test_analyze_empty_response_falls_back(self, debugger_tool, mock_llm_client):
        """Test that analyze() falls back to basic when LLM returns empty content"""
        mock_llm_client.debug_code.return_value = Mock(content="")
        result = debugger_tool.analyze("code", error="TypeError")

        assert "TypeError" in result

    def test_analyze_exception_returns_error_string(self, debugger_tool, mock_llm_client):
        """Test that analyze() returns error string on exception"""
        mock_llm_client.debug_code.side_effect = RuntimeError("LLM unavailable")
        result = debugger_tool.analyze("code", error="SomeError")

        assert "❌" in result or "failed" in result.lower()


class TestSuggestFixes:
    """Tests for suggest_fixes() public method"""

    def test_suggest_fixes_calls_llm_chat(self, debugger_tool, mock_llm_client):
        """Test that suggest_fixes() calls LLM chat"""
        mock_llm_client.chat.return_value = Mock(content="Root cause: missing null check")
        result = debugger_tool.suggest_fixes("def foo(x): return x.id", "AttributeError: x is None")

        mock_llm_client.chat.assert_called_once()
        prompt = mock_llm_client.chat.call_args[0][0]
        assert "foo" in prompt
        assert "AttributeError" in prompt

    def test_suggest_fixes_with_custom_language(self, debugger_tool, mock_llm_client):
        """Test that suggest_fixes() passes language in prompt"""
        mock_llm_client.chat.return_value = Mock(content="Fix the JS error")
        debugger_tool.suggest_fixes("const x", "ReferenceError", language="javascript")

        prompt = mock_llm_client.chat.call_args[0][0]
        assert "javascript" in prompt

    def test_suggest_fixes_returns_llm_response(self, debugger_tool, mock_llm_client):
        """Test that suggest_fixes() returns LLM response content"""
        expected = "Root cause: off-by-one error\nFixed code:\ndef foo(n): return range(1, n+1)"
        mock_llm_client.chat.return_value = Mock(content=expected)
        result = debugger_tool.suggest_fixes("range(1, n)", "IndexError")

        assert result == expected

    def test_suggest_fixes_exception_returns_error_string(self, debugger_tool, mock_llm_client):
        """Test that suggest_fixes() returns error string on exception"""
        mock_llm_client.chat.side_effect = IOError("Network failure")
        result = debugger_tool.suggest_fixes("code", "issue")

        assert "❌" in result or "failed" in result.lower()


class TestBasicErrorAnalysis:
    """Tests for _basic_error_analysis() fallback method"""

    def test_detects_index_error(self, debugger_tool):
        """Test IndexError detection and English fix"""
        result = debugger_tool._basic_error_analysis("IndexError: list index out of range")
        assert "IndexError" in result
        assert "Index out of range" in result

    def test_detects_key_error(self, debugger_tool):
        """Test KeyError detection and English fix"""
        result = debugger_tool._basic_error_analysis("KeyError: 'missing_key'")
        assert "KeyError" in result
        assert "Key not found in dictionary" in result

    def test_detects_attribute_error(self, debugger_tool):
        """Test AttributeError detection and English fix"""
        result = debugger_tool._basic_error_analysis("AttributeError: 'NoneType' has no attribute 'split'")
        assert "AttributeError" in result
        assert "Object has no such attribute or method" in result

    def test_detects_type_error(self, debugger_tool):
        """Test TypeError detection and English fix"""
        result = debugger_tool._basic_error_analysis("TypeError: unsupported operand type(s)")
        assert "TypeError" in result
        assert "Type mismatch" in result

    def test_detects_value_error(self, debugger_tool):
        """Test ValueError detection and English fix"""
        result = debugger_tool._basic_error_analysis("ValueError: invalid literal")
        assert "ValueError" in result
        assert "Invalid value" in result

    def test_detects_file_not_found_error(self, debugger_tool):
        """Test FileNotFoundError detection"""
        result = debugger_tool._basic_error_analysis("FileNotFoundError: [Errno 2] No such file")
        assert "filenotfounderror" in result.lower() or "文件路径不存在" in result

    def test_detects_permission_error(self, debugger_tool):
        """Test PermissionError detection"""
        result = debugger_tool._basic_error_analysis("PermissionError: [Errno 13]")
        assert "permissionerror" in result.lower() or "权限不足" in result

    def test_detects_timeout(self, debugger_tool):
        """Test timeout detection"""
        result = debugger_tool._basic_error_analysis("TimeoutError: operations timed out")
        assert "timeout" in result.lower() or "操作超时" in result

    def test_detects_connection_error(self, debugger_tool):
        """Test ConnectionError detection"""
        result = debugger_tool._basic_error_analysis("ConnectionError: connection refused")
        assert "connectionerror" in result.lower() or "网络连接失败" in result

    def test_none_check_message(self, debugger_tool):
        """Test None check message when 'None' in error"""
        result = debugger_tool._basic_error_analysis(
            "AttributeError: 'NoneType' object has no attribute"
        )
        assert "None" in result or "对象为 None" in result

    def test_unknown_error_shows_llm_prompt(self, debugger_tool):
        """Test that unknown errors prompt LLM configuration"""
        result = debugger_tool._basic_error_analysis("SomeUnknownError: something happened")
        assert "MINIMAX_API_KEY" in result

    def test_basic_error_analysis_with_stack_trace(self, debugger_tool):
        """Test that stack trace is included in output"""
        stack = "  File 'main.py', line 10, in main\n    foo()"
        result = debugger_tool._basic_error_analysis(
            "RuntimeError: something failed", stack_trace=stack
        )
        assert "堆栈跟踪" in result or "main.py" in result

    def test_basic_error_analysis_case_insensitive(self, debugger_tool):
        """Test that error detection is case-insensitive"""
        result = debugger_tool._basic_error_analysis("INDEXERROR: list index out of range")
        assert "IndexError" in result or "Index out of range" in result


class TestFormatDebugResponse:
    """Tests for _format_debug_response() internal method"""

    def test_format_with_error_includes_error_header(self, debugger_tool):
        """Test that _format_debug_response includes error in header when error is provided"""
        result = debugger_tool._format_debug_response("Fix: add null check", error="NullRef")
        assert "NullRef" in result
        assert "Fix: add null check" in result

    def test_format_without_error_shows_health_check_header(self, debugger_tool):
        """Test that _format_debug_response shows health check header when no error"""
        result = debugger_tool._format_debug_response("Code looks healthy", error=None)
        assert "健康" in result or "health" in result.lower() or "分析" in result

    def test_format_preserves_llm_content(self, debugger_tool):
        """Test that LLM response content is preserved in output"""
        llm_content = "## Root Cause\nMissing validation on line 42"
        result = debugger_tool._format_debug_response(llm_content, error="ValueError")
        assert llm_content in result


class TestAnalyzeCodeHealth:
    """Tests for _analyze_code_health() internal method"""

    def test_analyze_code_health_calls_llm_chat(self, debugger_tool, mock_llm_client):
        """Test that _analyze_code_health calls LLM chat with analysis prompt"""
        mock_llm_client.chat.return_value = Mock(content="Code analysis complete")
        debugger_tool._analyze_code_health("def foo(): pass", "python")

        mock_llm_client.chat.assert_called_once()
        prompt = mock_llm_client.chat.call_args[0][0]
        assert "python" in prompt
        assert "potential issues" in prompt.lower()

    def test_analyze_code_health_returns_formatted_response(self, debugger_tool, mock_llm_client):
        """Test that _analyze_code_health returns formatted response"""
        mock_llm_client.chat.return_value = Mock(content="Found 2 issues")
        result = debugger_tool._analyze_code_health("code", "javascript")

        assert "Found 2 issues" in result

    def test_analyze_code_health_exception_returns_error(self, debugger_tool, mock_llm_client):
        """Test that _analyze_code_health returns error string on exception"""
        mock_llm_client.chat.side_effect = Exception("LLM failed")
        result = debugger_tool._analyze_code_health("code", "python")

        assert "❌" in result or "failed" in result.lower()


class TestAnalyzeError:
    """Tests for _analyze_error() internal method"""

    def test_analyze_error_calls_llm_debug_code(self, debugger_tool, mock_llm_client):
        """Test that _analyze_error calls LLM debug_code with correct parameters"""
        mock_llm_client.debug_code.return_value = Mock(content="Fix: add null check")
        result = debugger_tool._analyze_error("code", "NullReferenceException", "python")

        mock_llm_client.debug_code.assert_called_once()
        call_kwargs = mock_llm_client.debug_code.call_args.kwargs
        assert call_kwargs["code"] == "code"
        assert call_kwargs["error"] == "NullReferenceException"
        assert call_kwargs["language"] == "python"
        assert "Fix: add null check" in result

    def test_analyze_error_not_configured_falls_back_to_basic(self, debugger_tool, mock_llm_client):
        """Test that _analyze_error falls back to basic when LLM returns 'not configured'"""
        mock_llm_client.debug_code.return_value = Mock(content="LLM not configured")
        result = debugger_tool._analyze_error("code", "KeyError: 'x'", "python")

        assert "KeyError" in result
        assert "Key not found in dictionary" in result

    def test_analyze_error_empty_response_falls_back_to_basic(self, debugger_tool, mock_llm_client):
        """Test that _analyze_error falls back to basic when LLM returns empty content"""
        mock_llm_client.debug_code.return_value = Mock(content="")
        result = debugger_tool._analyze_error("code", "TypeError", "python")

        assert "TypeError" in result

    def test_analyze_error_exception_returns_error_string(self, debugger_tool, mock_llm_client):
        """Test that _analyze_error returns error string on exception"""
        mock_llm_client.debug_code.side_effect = RuntimeError("LLM unavailable")
        result = debugger_tool._analyze_error("code", "SomeError", "python")

        assert "❌" in result or "failed" in result.lower()

    def test_analyze_error_with_stack_trace_passes_to_llm(self, debugger_tool, mock_llm_client):
        """Test that _analyze_error calls LLM debug_code with correct parameters"""
        mock_llm_client.debug_code.return_value = Mock(content="Fix: add null check")
        stack_trace = "  File 'main.py', line 10, in main\n    foo()"
        result = debugger_tool._analyze_error(
            "code", "RuntimeError", "python", stack_trace=stack_trace
        )

        call_kwargs = mock_llm_client.debug_code.call_args.kwargs
        assert call_kwargs["code"] == "code"
        assert call_kwargs["error"] == "RuntimeError"
        assert call_kwargs["language"] == "python"
        assert "Fix: add null check" in result
