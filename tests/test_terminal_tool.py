"""Tests for Terminal Tool"""

import pytest
from unittest.mock import Mock, patch
from beaver_agent.tools.terminal_tool import TerminalTool


@pytest.fixture
def mock_config():
    """Create a mock config object"""
    config = Mock()
    return config


@pytest.fixture
def terminal_tool(mock_config):
    """Create a TerminalTool instance with mocked config"""
    return TerminalTool(mock_config)


class TestTerminalToolInit:
    """Tests for TerminalTool initialization"""

    def test_init_stores_config(self, terminal_tool, mock_config):
        """Test that __init__ stores the config"""
        assert terminal_tool.config is mock_config

    def test_init_blocked_commands_defined(self, terminal_tool):
        """Test that BLOCKED_COMMANDS is defined"""
        assert hasattr(terminal_tool, "BLOCKED_COMMANDS")
        assert isinstance(terminal_tool.BLOCKED_COMMANDS, list)
        assert len(terminal_tool.BLOCKED_COMMANDS) > 0


class TestIsBlocked:
    """Tests for _is_blocked security check"""

    def test_blocked_dangerous_rm_rf(self, terminal_tool):
        """Test that dangerous rm commands are blocked"""
        assert terminal_tool._is_blocked("rm -rf /") is True
        assert terminal_tool._is_blocked("rm -rf ~") is True

    def test_blocked_fork_bomb(self, terminal_tool):
        """Test that fork bombs are blocked"""
        assert terminal_tool._is_blocked(":(){ :|:& };:") is True

    def test_blocked_disk_operations(self, terminal_tool):
        """Test that disk operations are blocked"""
        assert terminal_tool._is_blocked("mkfs") is True
        assert terminal_tool._is_blocked("dd if=/dev/zero of=/dev/sdX") is True

    def test_not_blocked_safe_commands(self, terminal_tool):
        """Test that safe commands are not blocked"""
        assert terminal_tool._is_blocked("ls -la") is False
        assert terminal_tool._is_blocked("echo hello") is False
        assert terminal_tool._is_blocked("python script.py") is False

    def test_blocked_case_insensitive(self, terminal_tool):
        """Test that blocked check is case-insensitive"""
        assert terminal_tool._is_blocked("RM -RF /") is True
        assert terminal_tool._is_blocked("MkFs") is True


class TestExecute:
    """Tests for execute command"""

    def test_blocked_command_returns_security_message(self, terminal_tool):
        """Test that blocked commands return security error"""
        result = terminal_tool.execute("rm -rf /")
        assert "blocked" in result.lower()

    def test_successful_command_returns_output(self, terminal_tool):
        """Test that successful commands return output"""
        result = terminal_tool.execute("echo hello")
        assert "hello" in result

    def test_timeout_returns_timeout_message(self, terminal_tool):
        """Test that timeout returns timeout error"""
        result = terminal_tool.execute("sleep 10", timeout=1)
        assert "timed out" in result.lower()

    def test_nonexistent_command_returns_error(self, terminal_tool):
        """Test that nonexistent commands return error"""
        result = terminal_tool.execute("nonexistent_command_xyz")
        # May return "not found" or error message depending on shell
        assert isinstance(result, str)

    def test_execute_with_cwd_parameter(self, terminal_tool):
        """Test execute accepts cwd parameter"""
        result = terminal_tool.execute("pwd", cwd="/tmp")
        assert isinstance(result, str)

    def test_execute_with_timeout_parameter(self, terminal_tool):
        """Test execute accepts timeout parameter"""
        result = terminal_tool.execute("echo test", timeout=5)
        assert "test" in result

    def test_execute_timeout_expired_exception_returns_timeout_message(self, terminal_tool, mock_config):
        """Test that subprocess.TimeoutExpired is caught and returns timeout message"""
        import subprocess
        # Patch subprocess.run to raise TimeoutExpired
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep 10", timeout=1)):
            result = terminal_tool.execute("sleep 10", timeout=1)
            assert "timed out" in result.lower()
            assert "1" in result  # timeout value in message


class TestGetErrorLog:
    """Tests for get_error_log"""

    def test_get_error_log_returns_string(self, terminal_tool):
        """Test that get_error_log returns a string"""
        result = terminal_tool.get_error_log()
        assert isinstance(result, str)

    def test_get_error_log_accepts_lines_parameter(self, terminal_tool):
        """Test that get_error_log accepts lines parameter"""
        result = terminal_tool.get_error_log(lines=10)
        assert isinstance(result, str)


class TestRunTests:
    """Tests for run_tests"""

    def test_run_tests_with_explicit_command(self, terminal_tool):
        """Test run_tests with explicit test command"""
        result = terminal_tool.run_tests(test_command="echo no tests")
        assert "no tests" in result

    def test_run_tests_without_command(self, terminal_tool):
        """Test run_tests without explicit command"""
        result = terminal_tool.run_tests()
        assert isinstance(result, str)
