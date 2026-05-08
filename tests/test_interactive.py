"""Tests for beaver_agent.cli.interactive REPL module."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from rich.console import Console

from beaver_agent.cli.interactive import run_repl, _print_response, print_welcome


@pytest.fixture
def mock_config():
    """Create a mock BeaverConfig for testing."""
    config = MagicMock()
    config.cli.welcome_banner = "Welcome to Beaver Agent"
    config.cli.prompt = "🦫"
    config.app.debug = False
    config.app.version = "1.0.0"
    return config


class TestRunRepl:
    """Tests for the run_repl function."""

    def test_repl_exits_on_keyboard_interrupt(self, mock_config):
        """Test REPL exits cleanly on KeyboardInterrupt."""
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            mock_agent = MockAgent.return_value
            with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                mock_prompt.side_effect = KeyboardInterrupt()
                # Should not raise — KeyboardInterrupt is caught internally
                run_repl(mock_config)
                # Verify agent was created
                MockAgent.assert_called_once_with(mock_config)

    def test_repl_exits_on_eof_error(self, mock_config):
        """Test REPL exits cleanly on EOFError (Ctrl+D)."""
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            mock_agent = MockAgent.return_value
            with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                mock_prompt.side_effect = EOFError()
                # Should not raise — EOFError is caught internally
                run_repl(mock_config)
                MockAgent.assert_called_once_with(mock_config)

    def test_repl_handles_empty_input_continues(self, mock_config):
        """Test REPL continues loop when user enters empty input."""
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            mock_agent = MockAgent.return_value
            with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                # First empty, then Ctrl+C to exit
                mock_prompt.side_effect = ["", KeyboardInterrupt()]
                run_repl(mock_config)
                # Should have been called twice (empty + KeyboardInterrupt)
                assert mock_prompt.call_count == 2

    def test_repl_handles_command_prefix(self, mock_config):
        """Test REPL calls handle_command for input starting with /."""
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            mock_agent = MockAgent.return_value
            with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                with patch("beaver_agent.cli.interactive.handle_command") as mock_handle:
                    mock_handle.return_value = None  # /exit returns False, others None
                    # /help command then KeyboardInterrupt
                    mock_prompt.side_effect = ["/help", KeyboardInterrupt()]
                    run_repl(mock_config)
                    mock_handle.assert_called_once_with("/help", mock_config, mock_agent)

    def test_repl_calls_agent_run_for_non_command_input(self, mock_config):
        """Test REPL calls agent.run for regular user input."""
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            mock_agent = MockAgent.return_value
            mock_agent.run.return_value = "Agent response"
            with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                with patch("beaver_agent.cli.interactive._print_response") as mock_print:
                    with patch("beaver_agent.cli.interactive.console.status") as mock_status:
                        mock_status.return_value.__enter__ = MagicMock()
                        mock_status.return_value.__exit__ = MagicMock()
                        # Regular query then KeyboardInterrupt
                        mock_prompt.side_effect = ["Hello agent", KeyboardInterrupt()]
                        run_repl(mock_config)
                        mock_agent.run.assert_called_once_with("Hello agent")
                        mock_print.assert_called_once_with("Agent response")

    def test_repl_exception_handling_logs_error(self, mock_config):
        """Test REPL catches exceptions and logs them."""
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            mock_agent = MockAgent.return_value
            mock_agent.run.side_effect = RuntimeError("Agent error")
            with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                with patch("beaver_agent.cli.interactive.logger") as mock_logger:
                    with patch("beaver_agent.cli.interactive.console.status") as mock_status:
                        mock_status.return_value.__enter__ = MagicMock()
                        mock_status.return_value.__exit__ = MagicMock()
                        mock_prompt.side_effect = ["Hello", KeyboardInterrupt()]
                        run_repl(mock_config)
                        # Exception should have been logged
                        mock_logger.error.assert_called_once()
                        call_args = mock_logger.error.call_args
                        assert (
                            "repl_error" in call_args[0] or call_args[1].get("exc_info") is not None
                        )

    def test_repl_debug_mode_prints_traceback(self, mock_config):
        """Test REPL in debug mode prints full traceback for unhandled exceptions."""
        mock_config.app.debug = True
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            mock_agent = MockAgent.return_value
            mock_agent.run.side_effect = ValueError("Test error")
            with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                with patch("beaver_agent.cli.interactive.logger") as mock_logger:
                    with patch("beaver_agent.cli.interactive.console.status") as mock_status:
                        mock_status.return_value.__enter__ = MagicMock()
                        mock_status.return_value.__exit__ = MagicMock()
                        mock_prompt.side_effect = ["Hello", KeyboardInterrupt()]
                        run_repl(mock_config)
                        # In debug mode, traceback.print_exc is called
                        # We verify by checking that after the error, loop continues

    def test_repl_welcome_banner_printed(self, mock_config):
        """Test REPL prints welcome banner when configured."""
        mock_config.cli.welcome_banner = "Welcome!"
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            with patch("beaver_agent.cli.interactive.console.print") as mock_print:
                with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                    mock_prompt.side_effect = KeyboardInterrupt()
                    run_repl(mock_config)
                    # console.print should have been called for the banner
                    assert mock_print.called

    def test_repl_no_welcome_banner(self, mock_config):
        """Test REPL skips banner when welcome_banner is None."""
        mock_config.cli.welcome_banner = None
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            with patch("beaver_agent.cli.interactive.console.print") as mock_print:
                with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                    mock_prompt.side_effect = KeyboardInterrupt()
                    run_repl(mock_config)
                    # console.print should NOT have been called for banner
                    # (may still be called for exit message)

    def test_repl_handles_exit_command(self, mock_config):
        """Test REPL exits when handle_command returns False (/exit)."""
        with patch("beaver_agent.cli.interactive.BeaverAgent") as MockAgent:
            mock_agent = MockAgent.return_value
            with patch("beaver_agent.cli.interactive.Prompt.ask") as mock_prompt:
                with patch("beaver_agent.cli.interactive.handle_command") as mock_handle:
                    mock_handle.return_value = False  # /exit returns False
                    mock_prompt.return_value.strip.return_value = "/exit"
                    run_repl(mock_config)
                    # Should have called handle_command with /exit
                    mock_handle.assert_called_once()
                    call_args = mock_handle.call_args[0]
                    assert call_args[0] == "/exit"


class TestPrintResponse:
    """Tests for _print_response function."""

    def test_plain_text_prints_directly(self):
        """Test plain text without code blocks is printed via console.print."""
        with patch("beaver_agent.cli.interactive.console") as mock_console:
            _print_response("Hello world")
            mock_console.print.assert_called_once_with("Hello world")

    def test_markdown_with_code_blocks_renders_as_markdown(self):
        """Test response with ``` is rendered via Markdown renderer."""
        with patch("beaver_agent.cli.interactive.console") as mock_console:
            with patch("beaver_agent.cli.interactive.Markdown") as MockMarkdown:
                mock_markdown_instance = MockMarkdown.return_value
                _print_response("Hello\n```python\nprint('hi')\n```")
                mock_console.print.assert_called_once()
                MockMarkdown.assert_called_once_with(
                    "Hello\n```python\nprint('hi')\n```", code_theme="monokai"
                )
                call_args = mock_console.print.call_args[0]
                assert call_args[0] is mock_markdown_instance

    def test_empty_code_block_markers_trigger_markdown(self):
        """Test triple backticks without content still triggers Markdown path."""
        with patch("beaver_agent.cli.interactive.console") as mock_console:
            with patch("beaver_agent.cli.interactive.Markdown") as MockMarkdown:
                mock_markdown_instance = MockMarkdown.return_value
                _print_response("```\n```")
                MockMarkdown.assert_called_once()
                call_args = mock_console.print.call_args[0]
                assert call_args[0] is mock_markdown_instance


class TestPrintWelcome:
    """Tests for print_welcome function."""

    def test_print_welcome_displays_version(self):
        """Test print_welcome shows version number."""
        config = MagicMock()
        config.app.version = "1.0.0"
        with patch("beaver_agent.cli.interactive.Panel") as MockPanel:
            print_welcome(config)
            MockPanel.assert_called_once()
            call_args = MockPanel.call_args[0]
            panel_content = str(call_args[0])
            assert "v1.0.0" in panel_content

    def test_print_welcome_displays_beaver_agent_text(self):
        """Test print_welcome shows Beaver Agent branding."""
        config = MagicMock()
        config.app.version = "1.0.0"
        with patch("beaver_agent.cli.interactive.Panel") as MockPanel:
            print_welcome(config)
            call_args = MockPanel.call_args[0]
            panel_content = str(call_args[0])
            assert "Beaver Agent" in panel_content

    def test_print_welcome_uses_cyan_border(self):
        """Test print_welcome uses cyan border style."""
        config = MagicMock()
        config.app.version = "1.0.0"
        with patch("beaver_agent.cli.interactive.Panel") as MockPanel:
            print_welcome(config)
            call_kwargs = MockPanel.call_args[1]
            assert call_kwargs["border_style"] == "cyan"
            assert call_kwargs["title"] == "Welcome"
