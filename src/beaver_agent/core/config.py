"""Beaver Agent Configuration Management"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

import structlog

logger = structlog.get_logger()

__all__ = ["BeaverConfig", "AppConfig", "ModelConfig", "GitHubConfig", "CLIConfig", "load_config"]


class AppConfig(BaseModel):
    """Root application configuration.

    Attributes:
        name: Human-readable application name.
        version: Semantic version string.
        debug: Whether debug mode is enabled (enables verbose logging).
    """

    name: str = "Beaver Agent"
    version: str = "0.1.0"
    debug: bool = False
    think_mode: bool = False  # Enable chain-of-thought: outputs reasoning before executing
    self_critique: bool = False  # Enable self-critique: reviews its own output for quality


class ModelConfig(BaseModel):
    """LLM model provider configuration.

    Attributes:
        provider: Name of the LLM provider (e.g., 'openrouter', 'anthropic', 'openai').
        name: Model name or alias to use for completions.
        api_key: Optional API key for the provider. Falls back to environment variables.
        api_base: Optional base URL for API endpoints (useful for proxy/self-hosted).
        max_tokens: Maximum number of tokens to generate in a single response.
        temperature: Sampling temperature (0.0-1.0). Higher values increase creativity.
    """

    provider: str = "openrouter"
    name: str = Field(default="anthropic/claude-3-haiku", validation_alias="model")
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7


class GitHubConfig(BaseModel):
    """GitHub integration configuration.

    Attributes:
        token: Optional GitHub personal access token for API authentication.
        owner: Default GitHub repository owner (user or organization).
        repo: Default repository name.
    """

    token: Optional[str] = None
    owner: str = "user-YeLei"
    repo: str = "beaver-agent"


class CLIConfig(BaseModel):
    """Command-line interface configuration.

    Attributes:
        prompt: Prompt prefix displayed before user input (e.g., '🦫 Beaver').
        welcome_banner: Optional ASCII art or welcome message shown on startup.
    """

    prompt: str = "🦫 Beaver"
    welcome_banner: str = ""


class LoggingConfig(BaseModel):
    """Logging subsystem configuration.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: Log output format ('json' for structured logging, 'text' for plain text).
    """

    level: str = "INFO"
    format: str = "json"


class FileToolConfig(BaseModel):
    """Configuration for file tool security settings"""

    root_path: Path = Field(default_factory=Path.cwd)


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server"""

    command: Optional[str] = None
    args: list = Field(default_factory=list)
    env: dict = Field(default_factory=dict)
    url: Optional[str] = None
    headers: dict = Field(default_factory=dict)
    timeout: int = 120
    connect_timeout: int = 60


class MCPConfig(BaseModel):
    """Configuration for MCP servers"""

    servers: dict[str, MCPServerConfig] = Field(default_factory=dict)

    # Support both "servers" (model) and "mcp_servers" (YAML key) names
    model_config = {"populate_by_name": True}

    @field_validator("servers", mode="before")
    @classmethod
    def handle_mcp_servers_key(cls, v, info) -> dict:
        """Handle both 'servers' (model) and 'mcp_servers' (YAML alias) field names.

        Pydantic's populate_by_name allows both names, but the validator still
        receives the raw dict. This ensures the 'servers' field is always populated
        regardless of which key name was used in the YAML/source.

        Args:
            v: The raw value from the model field before type coercion.
            info: Field validation info containing the alias data was loaded under.
        Returns:
            The validated servers dict, or the original value if not applicable.
        """
        return v


class BeaverConfig(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    cli: CLIConfig = Field(default_factory=CLIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    file_tool: FileToolConfig = Field(default_factory=FileToolConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)


def load_config(debug: bool = False) -> BeaverConfig:
    """Load configuration from settings.yaml and environment variables"""

    # Find project root and load .env automatically
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try current directory as well
        try:
            load_dotenv()
        except Exception as e:
            logger.warning("dotenv_load_failed", exc_info=e)
    config_paths = [
        Path("config/settings.yaml"),
        Path(__file__).parent.parent / "config" / "settings.yaml",
        Path.home() / ".beaver" / "config.yaml",
    ]

    config_data = {}
    for path in config_paths:
        if path.exists():
            try:
                with open(path) as f:
                    config_data = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error("config_file_load_failed", path=str(path), exc_info=e)
            break

    # Ensure required sections exist even when no config file was found
    if "model" not in config_data:
        config_data["model"] = {}
    if "github" not in config_data:
        config_data["github"] = {}

    # Override with environment variables
    config_data["model"]["api_key"] = os.environ.get(
        "MINIMAX_API_KEY",
        os.environ.get(
            "OPENROUTER_API_KEY",
            os.environ.get("ANTHROPIC_API_KEY", config_data.get("model", {}).get("api_key")),
        ),
    )
    # Override api_base and model name if provided via environment
    if os.environ.get("MINIMAX_API_BASE"):
        config_data["model"]["api_base"] = os.environ["MINIMAX_API_BASE"]
    if os.environ.get("MINIMAX_MODEL_NAME"):
        config_data["model"]["name"] = os.environ["MINIMAX_MODEL_NAME"]
    config_data["github"]["token"] = os.environ.get(
        "GITHUB_TOKEN", config_data.get("github", {}).get("token")
    )

    # Apply debug mode
    if debug:
        config_data["app"] = config_data.get("app", {})
        config_data["app"]["debug"] = True
        config_data["logging"] = {"level": "DEBUG"}

    return BeaverConfig(**config_data)
