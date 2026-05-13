"""Tests for Code Generation Tool"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from beaver_agent.tools.code_gen import CodeGenTool


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
def code_gen_tool(mock_config, mock_llm_client):
    """Create a CodeGenTool instance with mocked dependencies"""
    return CodeGenTool(mock_config, mock_llm_client)


class TestCodeGenToolInit:
    """Tests for CodeGenTool initialization"""

    def test_init_stores_config_and_llm(self, code_gen_tool, mock_config, mock_llm_client):
        """Test that __init__ stores config and llm_client"""
        assert code_gen_tool.config is mock_config
        assert code_gen_tool.llm is mock_llm_client

    def test_init_docstring_present(self, code_gen_tool):
        """Test that __init__ has a docstring"""
        assert CodeGenTool.__init__.__doc__ is not None
        assert "Args:" in CodeGenTool.__init__.__doc__


class TestGenerateSkeleton:
    """Tests for _generate_skeleton method"""

    def test_skeleton_python(self, code_gen_tool):
        """Test Python skeleton generation"""
        skeleton = code_gen_tool._generate_skeleton("Create a web server", "python")
        assert "# Python Code for: Create a web server" in skeleton
        assert "def main() -> None:" in skeleton
        assert '__name__ == "__main__"' in skeleton

    def test_skeleton_javascript(self, code_gen_tool):
        """Test JavaScript skeleton generation"""
        skeleton = code_gen_tool._generate_skeleton("API endpoint handler", "javascript")
        assert "// JavaScript/Node.js for: API endpoint handler" in skeleton
        assert "function main()" in skeleton
        assert "module.exports" in skeleton

    def test_skeleton_go(self, code_gen_tool):
        """Test Go skeleton generation"""
        skeleton = code_gen_tool._generate_skeleton("HTTP handler", "go")
        assert "// Go code for: HTTP handler" in skeleton
        assert "package main" in skeleton
        assert "func main()" in skeleton

    def test_skeleton_unknown_language(self, code_gen_tool):
        """Test skeleton for unknown language falls back to generic template"""
        skeleton = code_gen_tool._generate_skeleton("something", "cobol")
        assert "// Code for: something" in skeleton
        assert "Configure MINIMAX_API_KEY in .env" in skeleton

    def test_generate_skeleton_is_internal(self, code_gen_tool):
        """Test that _generate_skeleton is a private method (prefixed with _)"""
        assert hasattr(code_gen_tool, "_generate_skeleton")
        assert "_generate_skeleton" in dir(code_gen_tool)


class TestGenerate:
    """Tests for generate method"""

    def test_generate_calls_llm_with_correct_args(self, code_gen_tool, mock_llm_client):
        """Test that generate() calls LLM with correct parameters"""
        mock_response = Mock()
        mock_response.content = "def hello():\n    return 'world'"
        mock_llm_client.generate_code.return_value = mock_response

        result = code_gen_tool.generate("Hello world function", language="python")

        mock_llm_client.generate_code.assert_called_once_with(
            description="Hello world function", language="python", context=None
        )
        assert "def hello():" in result

    def test_generate_with_context(self, code_gen_tool, mock_llm_client):
        """Test that generate() passes context to LLM"""
        mock_response = Mock()
        mock_response.content = "def foo():\n    pass"
        mock_llm_client.generate_code.return_value = mock_response

        code_gen_tool.generate("foo function", language="python", context="Use type hints")

        mock_llm_client.generate_code.assert_called_once()
        call_kwargs = mock_llm_client.generate_code.call_args
        assert call_kwargs.kwargs.get("context") == "Use type hints"

    def test_generate_with_file_path_saves_and_returns_content(
        self, code_gen_tool, mock_llm_client, mock_config
    ):
        """Test that generate() with file_path calls FileTool.write_file and returns save result"""
        mock_response = Mock()
        mock_response.content = "def hello():\n    return 'world'"
        mock_llm_client.generate_code.return_value = mock_response

        mock_file_tool = Mock()
        mock_file_tool.write_file.return_value = "✓ Saved to /tmp/hello.py"
        with patch.object(code_gen_tool, "_file_tool", mock_file_tool):
            result = code_gen_tool.generate(
                "hello function", language="python", file_path="/tmp/hello.py"
            )

        mock_file_tool.write_file.assert_called_once_with(
            "/tmp/hello.py", "def hello():\n    return 'world'"
        )
        assert "def hello():" in result
        assert "✓ Saved to /tmp/hello.py" in result

    def test_generate_file_path_save_failure_returns_error_with_content(
        self, code_gen_tool, mock_llm_client, mock_config
    ):
        """Test that generate() with file_path handles write errors gracefully"""
        mock_response = Mock()
        mock_response.content = "def hello():\n    return 'world'"
        mock_llm_client.generate_code.return_value = mock_response

        mock_file_tool = Mock()
        mock_file_tool.write_file.side_effect = RuntimeError("Disk full")
        with patch.object(code_gen_tool, "_file_tool", mock_file_tool):
            result = code_gen_tool.generate(
                "hello function", language="python", file_path="/tmp/hello.py"
            )

        assert "def hello():" in result
        assert "❌ Save failed" in result
        assert "Disk full" in result

    def test_generate_not_configured_returns_skeleton(self, code_gen_tool, mock_llm_client):
        """Test that generate() returns skeleton when LLM returns 'not configured'"""
        mock_response = Mock()
        mock_response.content = "LLM not configured"
        mock_llm_client.generate_code.return_value = mock_response

        result = code_gen_tool.generate("test function", language="python")

        assert "# Python Code for: test function" in result
        assert "placeholder" in result

    def test_generate_empty_content_returns_skeleton(self, code_gen_tool, mock_llm_client):
        """Test that generate() returns skeleton when LLM returns empty content"""
        mock_response = Mock()
        mock_response.content = ""
        mock_llm_client.generate_code.return_value = mock_response

        result = code_gen_tool.generate("test function", language="python")

        assert "# Python Code for: test function" in result

    def test_generate_exception_returns_error_message(self, code_gen_tool, mock_llm_client):
        """Test that generate() returns error message when LLM raises exception"""
        mock_llm_client.generate_code.side_effect = RuntimeError("Network error")

        result = code_gen_tool.generate("test function", language="python")

        assert "❌" in result
        assert "failed" in result.lower()

    def test_generate_docstring_present(self):
        """Test that generate() has a docstring with Args/Returns sections"""
        assert CodeGenTool.generate.__doc__ is not None
        assert "Args:" in CodeGenTool.generate.__doc__
        assert "Returns:" in CodeGenTool.generate.__doc__


class TestCompleteCode:
    """Tests for complete_code method"""

    def test_complete_code_calls_llm_chat(self, code_gen_tool, mock_llm_client):
        """Test that complete_code() calls LLM chat with formatted prompt"""
        mock_response = Mock()
        mock_response.content = "# Completed code\ndef foo():\n    return True"
        mock_llm_client.chat.return_value = mock_response

        partial = "def foo():\n    # TODO: implement"
        result = code_gen_tool.complete_code(partial, "Complete the function", "python")

        mock_llm_client.chat.assert_called_once()
        call_arg = mock_llm_client.chat.call_args[0][0]
        assert "Complete the following python code" in call_arg
        assert partial in call_arg
        assert "# Completed code" in result

    def test_complete_code_exception_returns_error_message(self, code_gen_tool, mock_llm_client):
        """Test that complete_code() returns error message when LLM raises exception"""
        mock_llm_client.chat.side_effect = RuntimeError("API error")

        result = code_gen_tool.complete_code("def foo():", "complete it", "python")

        assert "❌" in result
        assert "completion failed" in result.lower()

    def test_complete_code_docstring_present(self):
        """Test that complete_code() has a docstring with Args/Returns sections"""
        assert CodeGenTool.complete_code.__doc__ is not None
        assert "Args:" in CodeGenTool.complete_code.__doc__
        assert "Returns:" in CodeGenTool.complete_code.__doc__


class TestRefactor:
    """Tests for refactor method"""

    def test_refactor_calls_llm_chat(self, code_gen_tool, mock_llm_client):
        """Test that refactor() calls LLM chat with formatted prompt"""
        mock_response = Mock()
        mock_response.content = "# Refactored code\ndef foo():\n    return True"
        mock_llm_client.chat.return_value = mock_response

        code = "def foo():\n\tpass"
        result = code_gen_tool.refactor(code, style="clean", language="python")

        mock_llm_client.chat.assert_called_once()
        call_arg = mock_llm_client.chat.call_args[0][0]
        assert "Refactor the following python code" in call_arg
        assert "clean" in call_arg
        assert code in call_arg

    def test_refactor_default_style(self, code_gen_tool, mock_llm_client):
        """Test that refactor() uses 'clean' as default style"""
        mock_response = Mock()
        mock_response.content = "# Refactored"
        mock_llm_client.chat.return_value = mock_response

        code_gen_tool.refactor("def foo():\n\tpass", language="python")

        call_arg = mock_llm_client.chat.call_args[0][0]
        assert "clean" in call_arg

    def test_refactor_exception_returns_error_message(self, code_gen_tool, mock_llm_client):
        """Test that refactor() returns error message when LLM raises exception"""
        mock_llm_client.chat.side_effect = RuntimeError("API error")

        result = code_gen_tool.refactor("def foo():\n\tpass", language="python")

        assert "❌" in result
        assert "refactoring failed" in result.lower()

    def test_refactor_docstring_present(self):
        """Test that refactor() has a docstring with Args/Returns sections"""
        assert CodeGenTool.refactor.__doc__ is not None
        assert "Args:" in CodeGenTool.refactor.__doc__
        assert "Returns:" in CodeGenTool.refactor.__doc__
