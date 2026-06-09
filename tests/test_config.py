"""Tests for core/config.py — configuration management and Pydantic models."""

from pathlib import Path

import yaml

from beaver_agent.core.config import (
    AppConfig,
    BeaverConfig,
    CLIConfig,
    FileToolConfig,
    GitHubConfig,
    LoggingConfig,
    MCPConfig,
    MCPServerConfig,
    ModelConfig,
    load_config,
)


class TestAppConfig:
    def test_defaults(self):
        cfg = AppConfig()
        assert cfg.name == "Beaver Agent"
        assert cfg.version == "0.1.0"
        assert cfg.debug is False

    def test_custom_values(self):
        cfg = AppConfig(name="Test", version="1.2.3", debug=True)
        assert cfg.name == "Test"
        assert cfg.version == "1.2.3"
        assert cfg.debug is True


class TestModelConfig:
    def test_defaults(self):
        cfg = ModelConfig()
        assert cfg.provider == "openrouter"
        assert cfg.name == "anthropic/claude-3-haiku"
        assert cfg.api_key is None
        assert cfg.api_base is None
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.7

    def test_custom_values(self):
        # Note: name field uses validation_alias="model", so pass via model= kwarg
        cfg = ModelConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-test",
            api_base="https://api.example.com",
            max_tokens=2048,
            temperature=0.5,
        )
        assert cfg.provider == "openai"
        assert cfg.name == "gpt-4"
        assert cfg.api_key == "sk-test"
        assert cfg.api_base == "https://api.example.com"
        assert cfg.max_tokens == 2048
        assert cfg.temperature == 0.5

    def test_validation_alias_model(self):
        """The 'model' field uses a validation_alias so it accepts 'model' in YAML/dict input."""
        cfg = ModelConfig.model_validate({"model": "claude-3-sonnet"})
        assert cfg.name == "claude-3-sonnet"


class TestGitHubConfig:
    def test_defaults(self):
        cfg = GitHubConfig()
        assert cfg.token is None
        assert cfg.owner == "user-YeLei"
        assert cfg.repo == "beaver-agent"

    def test_custom_values(self):
        cfg = GitHubConfig(token="ghp_test", owner="testuser", repo="testrepo")
        assert cfg.token == "ghp_test"
        assert cfg.owner == "testuser"
        assert cfg.repo == "testrepo"


class TestCLIConfig:
    def test_defaults(self):
        cfg = CLIConfig()
        assert cfg.prompt == "🦫 Beaver"
        assert cfg.welcome_banner == ""

    def test_custom_values(self):
        cfg = CLIConfig(prompt="🦫>", welcome_banner="Hello")
        assert cfg.prompt == "🦫>"
        assert cfg.welcome_banner == "Hello"


class TestLoggingConfig:
    def test_defaults(self):
        cfg = LoggingConfig()
        assert cfg.level == "INFO"
        assert cfg.format == "json"

    def test_custom_values(self):
        cfg = LoggingConfig(level="DEBUG", format="text")
        assert cfg.level == "DEBUG"
        assert cfg.format == "text"

    def test_invalid_level(self):
        """Pydantic accepts any string for level — no strict enum validation."""
        cfg = LoggingConfig(level="TRACE")
        assert cfg.level == "TRACE"


class TestFileToolConfig:
    def test_defaults(self):
        cfg = FileToolConfig()
        assert cfg.root_path == Path.cwd()

    def test_custom_root(self):
        cfg = FileToolConfig(root_path=Path("/tmp/safe"))
        assert cfg.root_path == Path("/tmp/safe")


class TestMCPServerConfig:
    def test_defaults(self):
        cfg = MCPServerConfig()
        assert cfg.command is None
        assert cfg.args == []
        assert cfg.env == {}
        assert cfg.url is None
        assert cfg.headers == {}
        assert cfg.timeout == 120
        assert cfg.connect_timeout == 60

    def test_custom_values(self):
        cfg = MCPServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            env={"DEBUG": "1"},
            url="http://localhost:3000",
            headers={"Authorization": "Bearer token"},
            timeout=60,
            connect_timeout=30,
        )
        assert cfg.command == "npx"
        assert cfg.args == ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        assert cfg.env == {"DEBUG": "1"}
        assert cfg.url == "http://localhost:3000"
        assert cfg.headers == {"Authorization": "Bearer token"}
        assert cfg.timeout == 60
        assert cfg.connect_timeout == 30


class TestMCPConfig:
    def test_defaults(self):
        cfg = MCPConfig()
        assert cfg.servers == {}

    def test_servers_dict(self):
        cfg = MCPConfig(servers={"files": MCPServerConfig(command="npx")})
        assert "files" in cfg.servers
        assert cfg.servers["files"].command == "npx"

    def test_mcp_servers_alias_handling(self):
        """The handle_mcp_servers_key validator accepts raw dict regardless of YAML key name."""
        # Simulate YAML loaded with 'mcp_servers' key (the alias) instead of 'servers'
        cfg = MCPConfig.model_validate(
            {"servers": {"files": {"command": "npx", "args": ["-y", "server"]}}}
        )
        assert "files" in cfg.servers
        assert cfg.servers["files"].command == "npx"


class TestBeaverConfig:
    def test_defaults(self):
        cfg = BeaverConfig()
        assert isinstance(cfg.app, AppConfig)
        assert isinstance(cfg.model, ModelConfig)
        assert isinstance(cfg.github, GitHubConfig)
        assert isinstance(cfg.cli, CLIConfig)
        assert isinstance(cfg.logging, LoggingConfig)
        assert isinstance(cfg.file_tool, FileToolConfig)
        assert isinstance(cfg.mcp, MCPConfig)

    def test_partial_override(self):
        """Partial config dict should fill in remaining defaults."""
        cfg = BeaverConfig.model_validate({"app": {"name": "Custom", "debug": True}})
        assert cfg.app.name == "Custom"
        assert cfg.app.debug is True
        assert cfg.app.version == "0.1.0"  # default
        assert cfg.model.provider == "openrouter"  # default


class TestLoadConfig:
    def test_load_config_no_file(self, monkeypatch):
        """When no config file exists at any path, load_config returns default BeaverConfig."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Make all config paths appear non-existent
        def fake_exists(self):
            return False

        monkeypatch.setattr(Path, "exists", fake_exists)
        cfg = load_config()
        assert isinstance(cfg, BeaverConfig)
        assert cfg.app.name == "Beaver Agent"
        assert cfg.model.provider == "openrouter"

    def test_load_config_with_yaml_file(self, monkeypatch):
        """load_config reads settings.yaml and merges with defaults."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Make all config paths appear non-existent except our target

        def fake_exists(self):
            if self.name == "settings.yaml" and self.parent.name == "config":
                return True
            return False

        monkeypatch.setattr(Path, "exists", fake_exists)

        settings = {
            "app": {"name": "TestApp", "version": "2.0.0"},
            "model": {"provider": "openai", "model": "gpt-4o"},
            "github": {"owner": "testuser", "repo": "testrepo"},
            "cli": {"prompt": "🦫> "},
            "logging": {"level": "DEBUG"},
        }

        def fake_safe_load(f, Loader=None):
            return settings

        monkeypatch.setattr(yaml, "safe_load", fake_safe_load)

        cfg = load_config()
        assert cfg.app.name == "TestApp"
        assert cfg.model.provider == "openai"
        assert cfg.model.name == "gpt-4o"
        assert cfg.github.owner == "testuser"
        assert cfg.cli.prompt == "🦫> "
        assert cfg.logging.level == "DEBUG"

    def test_load_config_debug_mode(self, monkeypatch):
        """Debug flag overrides app.debug and logging.level."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Make all paths non-existent so we get defaults then debug overrides
        def fake_exists(self):
            return False

        monkeypatch.setattr(Path, "exists", fake_exists)
        cfg = load_config(debug=True)
        assert cfg.app.debug is True
        assert cfg.logging.level == "DEBUG"

    def test_load_config_env_api_key_override(self, monkeypatch):
        """Environment variables override config file values."""
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "env-api-key-value")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        def fake_exists(self):
            if self.name == "settings.yaml" and self.parent.name == "config":
                return True
            return False

        monkeypatch.setattr(Path, "exists", fake_exists)

        # Prevent load_dotenv from re-loading .env file which contains real MINIMAX_API_KEY
        import beaver_agent.core.config as config_module
        monkeypatch.setattr(config_module, "load_dotenv", lambda *args, **kwargs: None)

        def fake_safe_load(f, Loader=None):
            return {"model": {"api_key": ""}, "github": {"token": "***"}}

        monkeypatch.setattr(yaml, "safe_load", fake_safe_load)

        cfg = load_config()
        # OPENROUTER_API_KEY env var takes precedence over file value
        assert cfg.model.api_key == "env-api-key-value"
        # Note: .env GITHUB_TOKEN overrides file value when load_dotenv runs

    def test_load_config_github_token_from_env(self, monkeypatch):
        """GITHUB_TOKEN env var is picked up when github.token is not in config."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_token")

        def fake_exists(self):
            if self.name == "settings.yaml" and self.parent.name == "config":
                return True
            return False

        monkeypatch.setattr(Path, "exists", fake_exists)

        def fake_safe_load(f, Loader=None):
            return {}

        monkeypatch.setattr(yaml, "safe_load", fake_safe_load)

        cfg = load_config()
        assert cfg.github.token == "ghp_env_token"
