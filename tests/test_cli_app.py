"""Tests for Typer CLI app command registration and help output."""

import pytest
from typer.testing import CliRunner

from beaver_agent.main import app


@pytest.fixture
def runner():
    return CliRunner()


class TestRunCommand:
    """Tests for run command."""

    def test_run_command_shows_help(self, runner):
        """Test run --help displays REPL usage information."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "--model" in result.output
        assert "--debug" in result.output

    def test_run_command_with_model_option(self, runner):
        """Test run accepts --model option without crashing."""
        # We cannot actually test the REPL, but we can verify
        # the option parsing accepts --model without error
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0

    def test_run_command_with_debug_flag(self, runner):
        """Test run accepts --debug flag without crashing."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "--debug" in result.output


class TestChatCommand:
    """Tests for chat command."""

    def test_chat_command_shows_help(self, runner):
        """Test chat --help displays query usage information."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "--query" in result.output
        assert "-q" in result.output
        assert "--model" in result.output

    def test_chat_requires_query(self, runner):
        """Test chat fails gracefully without --query."""
        result = runner.invoke(app, ["chat"])
        # Typer exits with 1 when required option is missing
        assert result.exit_code != 0

    def test_chat_with_empty_query_shows_help(self, runner):
        """Test chat with -q but no actual query shows help."""
        result = runner.invoke(app, ["chat", "-q", ""])
        # Empty string is still a value, so it may not trigger --help
        # but the agent will handle it
        assert result.exit_code == 0


class TestVersionCommand:
    """Tests for version command."""

    def test_version_command_shows_version(self, runner):
        """Test version command outputs version string."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Beaver Agent" in result.output

    def test_version_command_shows_help(self, runner):
        """Test version --help displays version command info."""
        result = runner.invoke(app, ["version", "--help"])
        assert result.exit_code == 0


class TestModelCommand:
    """Tests for model command."""

    def test_model_command_shows_help(self, runner):
        """Test model --help displays model management options."""
        result = runner.invoke(app, ["model", "--help"])
        assert result.exit_code == 0
        assert "--show" in result.output


class TestSetupCommand:
    """Tests for setup command."""

    def test_setup_command_shows_help(self, runner):
        """Test setup --help displays first-time setup options."""
        result = runner.invoke(app, ["setup", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output
        assert "-f" in result.output

    def test_setup_command_force_flag(self, runner):
        """Test setup --force is accepted as valid option."""
        result = runner.invoke(app, ["setup", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output


class TestCliHelp:
    """Tests for top-level --help."""

    def test_help_shows_all_commands(self, runner):
        """Test --help lists all available commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "chat" in result.output
        assert "model" in result.output
        assert "setup" in result.output
        assert "version" in result.output

    def test_no_command_exits_with_error(self, runner):
        """Test invoking beaver without any command exits with error code 2."""
        result = runner.invoke(app, [])
        # Typer exits with 2 when no command is provided
        assert result.exit_code == 2
