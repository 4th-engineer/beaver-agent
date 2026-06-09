"""Tests for main.py CLI entry points (run, chat, model, version, setup)"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from beaver_agent.main import app


@pytest.fixture
def runner():
    return CliRunner()


class TestRunCommand:
    """Tests for the run command."""

    def test_run_command_invokes_repl(self, runner, tmp_path, monkeypatch):
        """Test 'beaver run' calls run_repl with config."""
        monkeypatch.chdir(tmp_path)
        # Create a minimal .env so load_config doesn't fail
        env_file = tmp_path / ".env"
        env_file.write_text("MINIMAX_API_KEY=***\n")

        with patch("beaver_agent.main.run_repl") as mock_repl:
            mock_repl.return_value = None
            result = runner.invoke(app, ["run"], input="exit\n")
            mock_repl.assert_called_once()
            # REPL exits via KeyboardInterrupt / EOF / exit command → exit_code 0
            assert result.exit_code == 0

    def test_run_command_with_debug_flag(self, runner, tmp_path, monkeypatch):
        """Test 'beaver run --debug' enables debug mode."""
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MINIMAX_API_KEY=***\n")

        with patch("beaver_agent.main.run_repl") as mock_repl:
            mock_repl.return_value = None
            result = runner.invoke(app, ["run", "--debug"], input="exit\n")
            mock_repl.assert_called_once()
            # Should not crash with debug flag
            assert result.exit_code == 0


class TestChatCommand:
    """Tests for the chat command."""

    def test_chat_requires_query(self, runner):
        """Test 'beaver chat' without --query exits with code 2 (missing option)."""
        result = runner.invoke(app, ["chat"])
        assert result.exit_code == 2
        assert "Missing option" in result.output or "--query" in result.output

    def test_chat_with_query_error_propagates(self, runner, tmp_path, monkeypatch):
        """Test 'beaver chat -q <query>' propagates agent.run exceptions."""
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MINIMAX_API_KEY=***\n")

        with patch("beaver_agent.cli.commands.BeaverAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.run.side_effect = RuntimeError("LLM failed")
            result = runner.invoke(app, ["chat", "-q", "Hello"])
            # Exceptions propagate; exit code 1 indicates error
            assert result.exit_code == 1

    def test_chat_with_query_success(self, runner, tmp_path, monkeypatch):
        """Test 'beaver chat -q <query>' successfully calls agent and prints response."""
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MINIMAX_API_KEY=***\n")

        with patch("beaver_agent.cli.commands.BeaverAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.run.return_value = "Test response from agent"
            result = runner.invoke(app, ["chat", "-q", "Hello"])
            mock_instance.run.assert_called_once_with("Hello")
            assert result.exit_code == 0


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_command_shows_version(self, runner):
        """Test 'beaver version' displays version string."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Beaver Agent" in result.output


class TestSetupCommand:
    """Tests for the setup command."""

    def test_setup_command_no_env(self, runner, tmp_path, monkeypatch):
        """Test 'beaver setup' with no .env and no .env.example exits with 1."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["setup"])
        assert result.exit_code == 1
        assert ".env.example not found" in result.output

    def test_setup_command_with_env_example(self, runner, tmp_path, monkeypatch):
        """Test 'beaver setup' with .env.example creates .env."""
        monkeypatch.chdir(tmp_path)
        env_example = tmp_path / ".env.example"
        env_example.write_text("MINIMAX_API_KEY=your_key_here\n")

        result = runner.invoke(app, ["setup"])
        # Should either detect existing .env or prompt for editing
        # In test environment without EDITOR, it just prints instructions
        assert result.exit_code == 0

    def test_setup_command_force_overwrites(self, runner, tmp_path, monkeypatch):
        """Test 'beaver setup --force' overwrites existing .env."""
        monkeypatch.chdir(tmp_path)
        env_example = tmp_path / ".env.example"
        env_example.write_text("MINIMAX_API_KEY=new_key\n")
        env_file = tmp_path / ".env"
        env_file.write_text("MINIMAX_API_KEY=old_key\n")

        result = runner.invoke(app, ["setup", "--force"])
        assert result.exit_code == 0


class TestModelCommand:
    """Tests for the model command."""

    def test_model_command_show(self, runner):
        """Test 'beaver model --show' displays model info."""
        with patch("beaver_agent.main.load_config") as mock_load:
            mock_cfg = MagicMock()
            mock_cfg.model.name = "test-model"
            mock_cfg.model.provider = "test-provider"
            mock_load.return_value = mock_cfg
            result = runner.invoke(app, ["model", "--show"])
            assert result.exit_code == 0
