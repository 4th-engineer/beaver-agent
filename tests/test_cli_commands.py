"""Tests for CLI command functions in commands.py"""

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from beaver_agent.main import app
from beaver_agent.cli.commands import handle_command, print_help, show_model_info, show_status


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.model.name = "test-model"
    config.model.provider = "test-provider"
    config.app.debug = False
    config.cli.prompt = ">"
    return config


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.session_id = "test-session-123"
    return agent


class TestHandleCommand:
    """Tests for handle_command slash commands."""

    def test_exit_command_returns_false(self, mock_config, mock_agent):
        """Test /exit returns False to terminate REPL."""
        result = handle_command("/exit", mock_config, mock_agent)
        assert result is False

    def test_quit_command_returns_false(self, mock_config, mock_agent):
        """Test /quit returns False to terminate REPL."""
        result = handle_command("/quit", mock_config, mock_agent)
        assert result is False

    def test_q_command_returns_false(self, mock_config, mock_agent):
        """Test /q returns False to terminate REPL."""
        result = handle_command("/q", mock_config, mock_agent)
        assert result is False

    def test_help_command_returns_true(self, mock_config, mock_agent, capsys):
        """Test /help returns True and prints help text."""
        result = handle_command("/help", mock_config, mock_agent)
        assert result is True
        captured = capsys.readouterr()
        assert "Beaver Agent" in captured.out

    def test_h_command_shows_help(self, mock_config, mock_agent, capsys):
        """Test /h alias shows help."""
        result = handle_command("/h", mock_config, mock_agent)
        assert result is True
        captured = capsys.readouterr()
        assert "Beaver Agent" in captured.out

    def test_question_mark_shows_help(self, mock_config, mock_agent, capsys):
        """Test ? alias shows help."""
        result = handle_command("?", mock_config, mock_agent)
        assert result is True
        captured = capsys.readouterr()
        assert "Beaver Agent" in captured.out

    def test_clear_command_returns_true(self, mock_config, mock_agent, capsys):
        """Test /clear returns True (screen cleared)."""
        result = handle_command("/clear", mock_config, mock_agent)
        assert result is True

    def test_reset_command_returns_true(self, mock_config, mock_agent, capsys):
        """Test /reset returns True (screen cleared)."""
        result = handle_command("/reset", mock_config, mock_agent)
        assert result is True

    def test_model_command_shows_model_info(self, mock_config, mock_agent, capsys):
        """Test /model shows current model info."""
        result = handle_command("/model", mock_config, mock_agent)
        assert result is True
        captured = capsys.readouterr()
        assert "test-model" in captured.out
        assert "test-provider" in captured.out

    def test_model_switch(self, mock_config, mock_agent, capsys):
        """Test /model <name> switches model."""
        result = handle_command("/model gpt-5", mock_config, mock_agent)
        assert result is True
        assert mock_config.model.name == "gpt-5"
        captured = capsys.readouterr()
        assert "gpt-5" in captured.out

    def test_status_command(self, mock_config, mock_agent, capsys):
        """Test /status shows agent status."""
        result = handle_command("/status", mock_config, mock_agent)
        assert result is True
        captured = capsys.readouterr()
        assert "test-session-123" in captured.out

    def test_debug_toggle_on(self, mock_config, mock_agent, capsys):
        """Test /debug toggles debug mode on."""
        mock_config.app.debug = False
        result = handle_command("/debug", mock_config, mock_agent)
        assert result is True
        assert mock_config.app.debug is True
        captured = capsys.readouterr()
        assert "开启" in captured.out

    def test_debug_toggle_off(self, mock_config, mock_agent, capsys):
        """Test /debug toggles debug mode off."""
        mock_config.app.debug = True
        result = handle_command("/debug", mock_config, mock_agent)
        assert result is True
        assert mock_config.app.debug is False
        captured = capsys.readouterr()
        assert "关闭" in captured.out

    def test_unknown_command_returns_true(self, mock_config, mock_agent, capsys):
        """Test unknown command returns True and prints error."""
        result = handle_command("/unknown", mock_config, mock_agent)
        assert result is True
        captured = capsys.readouterr()
        assert "未知命令" in captured.out

    def test_browse_command(self, mock_config, mock_agent, capsys):
        """Test /browse <url> opens URL."""
        with patch("beaver_agent.cli.commands.BrowserTool") as MockBrowserTool:
            mock_instance = MagicMock()
            mock_instance.open.return_value = "Page content"
            MockBrowserTool.return_value = mock_instance

            result = handle_command("/browse https://example.com", mock_config, mock_agent)
            assert result is True
            mock_instance.open.assert_called_once_with("https://example.com")
            captured = capsys.readouterr()
            assert "example.com" in captured.out

    def test_browse_command_adds_https(self, mock_config, mock_agent, capsys):
        """Test /browse <url> adds https:// if missing."""
        with patch("beaver_agent.cli.commands.BrowserTool") as MockBrowserTool:
            mock_instance = MagicMock()
            mock_instance.open.return_value = "Page content"
            MockBrowserTool.return_value = mock_instance

            result = handle_command("/browse example.com", mock_config, mock_agent)
            assert result is True
            mock_instance.open.assert_called_once_with("https://example.com")

    def test_screenshot_command(self, mock_config, mock_agent, capsys):
        """Test /screenshot takes screenshot."""
        with patch("beaver_agent.cli.commands.BrowserTool") as MockBrowserTool:
            with patch("beaver_agent.cli.commands.tempfile.mktemp") as mock_mktemp:
                mock_mktemp.return_value = "/tmp/test.png"
                mock_instance = MagicMock()
                mock_instance.open.return_value = None
                mock_instance.screenshot.return_value = "Screenshot saved"
                MockBrowserTool.return_value = mock_instance

                result = handle_command("/screenshot", mock_config, mock_agent)
                assert result is True
                mock_instance.open.assert_called_once()
                mock_instance.screenshot.assert_called_once()


class TestPrintHelp:
    """Tests for print_help function."""

    def test_print_help_displays_commands(self, capsys):
        """Test print_help shows all commands."""
        print_help()
        captured = capsys.readouterr()
        assert "/help" in captured.out
        assert "/exit" in captured.out
        assert "/model" in captured.out
        assert "/status" in captured.out
        assert "/debug" in captured.out


class TestShowModelInfo:
    """Tests for show_model_info function."""

    def test_show_model_info_displays_model(self, mock_config, capsys):
        """Test show_model_info shows model name and provider."""
        show_model_info(mock_config)
        captured = capsys.readouterr()
        assert "test-model" in captured.out
        assert "test-provider" in captured.out


class TestShowStatus:
    """Tests for show_status function."""

    def test_show_status_displays_session_id(self, mock_agent, capsys):
        """Test show_status shows agent session ID."""
        show_status(mock_agent)
        captured = capsys.readouterr()
        assert "test-session-123" in captured.out


class TestCliApp:
    """Tests for Typer CLI app commands."""

    def test_run_command_exists(self, runner):
        """Test 'run' command is registered in CLI."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output

    def test_chat_command_exists(self, runner):
        """Test 'chat' command is registered in CLI."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "chat" in result.output

    def test_setup_command_exists(self, runner):
        """Test 'setup' command is registered in CLI."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "setup" in result.output

    def test_model_command_exists(self, runner):
        """Test 'model' command is registered in CLI."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "model" in result.output
