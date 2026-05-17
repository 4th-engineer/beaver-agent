"""Tests for Beaver Agent CLI"""

import pytest
from typer.testing import CliRunner

from beaver_agent.main import app


@pytest.fixture
def runner():
    return CliRunner()


def test_help_command(runner):
    """Test --help shows all commands"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "chat" in result.output
    assert "model" in result.output


def test_version_command(runner):
    """Test version command"""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Beaver Agent" in result.output


def test_model_command_show(runner):
    """Test model show command"""
    result = runner.invoke(app, ["model", "--show"])
    assert result.exit_code == 0


def test_chat_single_query(runner):
    """Test single query chat mode"""
    result = runner.invoke(app, ["chat", "-q", "你好"])
    assert result.exit_code == 0
    assert "Beaver" in result.output or "🦫" in result.output


def test_setup_command_already_exists(runner, tmp_path, monkeypatch):
    """Test setup command when .env already exists (no force flag)."""
    # Mock .env and .env.example in a temp directory so we don't touch the real project
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env"
    env_example = tmp_path / ".env.example"
    env_example.write_text("MINIMAX_API_KEY=your_key_here\nGITHUB_TOKEN=your_token_here\n")
    env_file.write_text("MINIMAX_API_KEY=real_key\nGITHUB_TOKEN=real_token\n")

    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 0
    assert ".env already exists" in result.output


def test_setup_command_missing_env_example(runner, tmp_path, monkeypatch):
    """Test setup command when .env.example is missing (and .env also doesn't exist)."""
    monkeypatch.chdir(tmp_path)
    # .env does NOT exist, .env.example does NOT exist → raises Exit(1)

    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 1
    assert ".env.example not found" in result.output
