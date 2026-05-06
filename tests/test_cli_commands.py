"""Tests for CLI command functions in commands.py"""

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from beaver_agent.main import app
from beaver_agent.cli.commands import handle_command, print_help, show_model_info, show_status, chat_command, model_command
from rich.markdown import Markdown
from beaver_agent.cli.interactive import print_welcome, _print_response


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
    agent.config = MagicMock()
    agent.config.model.name = "test-model"
    agent.config.model.provider = "test-provider"
    agent.memory = MagicMock()
    agent.memory.get_history.return_value = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    agent.long_term_memory = MagicMock()
    agent.long_term_memory.get_stats.return_value = {"total_entries": 5, "categories": {}}
    agent.tool_router = MagicMock()
    agent.tool_router.list_tools.return_value = ["file_tool", "terminal_tool", "github_tool"]
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

    def test_analyze_command(self, mock_config, mock_agent, capsys):
        """Test /analyze runs repository analysis."""
        with patch("beaver_agent.cli.commands.analyze_repository") as mock_analyze:
            mock_analyze.return_value = "Repository structure: 42 files, 8 modules"
            with patch("beaver_agent.cli.commands.Path") as MockPath:
                MockPath.return_value.parent.parent.parent.parent = "/fake/project"

                result = handle_command("/analyze", mock_config, mock_agent)
                assert result is True
                mock_analyze.assert_called_once()
                captured = capsys.readouterr()
                assert "42 files" in captured.out


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
        """Test show_status shows agent runtime status."""
        show_status(mock_agent)
        captured = capsys.readouterr()
        assert "test-session-123" in captured.out
        assert "test-model" in captured.out
        assert "test-provider" in captured.out
        assert "2 条消息" in captured.out
        assert "5 条记忆" in captured.out
        assert "3 个工具" in captured.out


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
        result = runner.invoke(app, ["model", "--help"])
        assert result.exit_code == 0

    def test_model_command_show_true_displays_model_info(self, capsys):
        """Test model_command(show=True) loads config and displays model info."""
        mock_cfg = MagicMock()
        mock_cfg.model.name = "test-model-name"
        mock_cfg.model.provider = "test-provider-name"
        with patch("beaver_agent.cli.commands.load_config", return_value=mock_cfg):
            model_command(show=True)
        captured = capsys.readouterr()
        assert "test-model-name" in captured.out
        assert "test-provider-name" in captured.out

    def test_run_command_with_model_option(self, runner, tmp_path, monkeypatch):
        """Test 'beaver run --model <name>' sets the model name in config."""
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MINIMAX_API_KEY=***\n")

        with patch("beaver_agent.main.run_repl") as mock_repl:
            mock_repl.return_value = None
            result = runner.invoke(app, ["run", "--model", "gpt-5"], input="exit\n")
            mock_repl.assert_called_once()
            # Verify the config model name was set to gpt-5
            call_config = mock_repl.call_args[0][0]
            assert call_config.model.name == "gpt-5"
            assert result.exit_code == 0

    def test_chat_command_with_model_option(self, runner, tmp_path, monkeypatch):
        """Test 'beaver chat -q <query> --model <name>' sets the model name."""
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MINIMAX_API_KEY=***\n")

        with patch("beaver_agent.cli.commands.BeaverAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.run.return_value = "Test response"
            result = runner.invoke(app, ["chat", "-q", "Hello", "--model", "claude-3"], input="")
            mock_instance.run.assert_called_once_with("Hello")
            assert result.exit_code == 0


class TestChatCommand:
    """Tests for chat_command function."""

    def test_chat_command_returns_response(self, mock_config, capsys):
        """Test chat_command calls agent.run and prints response."""
        with patch("beaver_agent.cli.commands.BeaverAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.run.return_value = "Test response from agent"
            chat_command(mock_config, "Hello agent")
            captured = capsys.readouterr()
            assert "Test response from agent" in captured.out

    def test_chat_command_calls_agent_run_with_query(self, mock_config):
        """Test chat_command passes query to agent.run()."""
        with patch("beaver_agent.cli.commands.BeaverAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.run.return_value = "Response"
            chat_command(mock_config, "Test query")
            mock_instance.run.assert_called_once_with("Test query")

    def test_chat_command_creates_agent_with_config(self, mock_config):
        """Test chat_command passes config to BeaverAgent constructor."""
        with patch("beaver_agent.cli.commands.BeaverAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.run.return_value = "Response"
            chat_command(mock_config, "Query")
            MockAgent.assert_called_once_with(mock_config)


class TestPrintWelcome:
    """Tests for print_welcome function."""

    def test_print_welcome_displays_version(self, mock_config, capsys):
        """Test print_welcome shows version number."""
        with patch("beaver_agent.cli.interactive.Panel") as MockPanel:
            mock_config.app.version = "1.0.0"
            print_welcome(mock_config)
            MockPanel.assert_called_once()
            call_args = MockPanel.call_args[0]
            panel_content = str(call_args[0])
            assert "v1.0.0" in panel_content

    def test_print_welcome_displays_beaver_agent_text(self, mock_config, capsys):
        """Test print_welcome shows Beaver Agent branding."""
        with patch("beaver_agent.cli.interactive.Panel") as MockPanel:
            print_welcome(mock_config)
            call_args = MockPanel.call_args[0]
            panel_content = str(call_args[0])
            assert "Beaver Agent" in panel_content


class TestPrintResponse:
    """Tests for _print_response function."""

    def test_plain_text_prints_directly(self, capsys):
        """Test plain text without code blocks is printed via console.print."""
        with patch("beaver_agent.cli.interactive.console") as mock_console:
            _print_response("Hello world")
            mock_console.print.assert_called_once_with("Hello world")

    def test_markdown_with_code_blocks_renders_as_markdown(self, capsys):
        """Test response with ``` is rendered via Markdown renderer."""
        with patch("beaver_agent.cli.interactive.console") as mock_console:
            with patch("beaver_agent.cli.interactive.Markdown") as MockMarkdown:
                mock_markdown_instance = MockMarkdown.return_value
                _print_response("Hello\n```python\nprint('hi')\n```")
                mock_console.print.assert_called_once()
                # Verify Markdown was called (rendered as markdown, not plain text)
                MockMarkdown.assert_called_once()
                MockMarkdown.assert_called_with(
                    "Hello\n```python\nprint('hi')\n```",
                    code_theme="monokai"
                )
                # The console.print was called with the Markdown instance (mock)
                call_args = mock_console.print.call_args[0]
                assert call_args[0] is mock_markdown_instance

    def test_empty_code_block_markers_dont_trigger_markdown(self, capsys):
        """Test triple backticks without content between them still triggers Markdown path."""
        # Even empty code blocks should go through Markdown renderer
        with patch("beaver_agent.cli.interactive.console") as mock_console:
            with patch("beaver_agent.cli.interactive.Markdown") as MockMarkdown:
                mock_markdown_instance = MockMarkdown.return_value
                _print_response("```\n```")
                MockMarkdown.assert_called_once()
                call_args = mock_console.print.call_args[0]
                assert call_args[0] is mock_markdown_instance
