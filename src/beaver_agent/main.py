"""Beaver Agent CLI - Main Entry Point"""

import typer
from pathlib import Path
from rich.console import Console
from typing import Optional

import structlog

from beaver_agent.cli.interactive import run_repl
from beaver_agent.cli.commands import chat_command, model_command
from beaver_agent.core.agent import BeaverAgent
from beaver_agent.core.config import load_config

__all__ = ["app"]

console = Console()
logger = structlog.get_logger()

app = typer.Typer(
    name="beaver",
    help="🦫 Beaver Agent - AI Coding Assistant",
    add_completion=False,
)


@app.command()
def run(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Specify model name"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
) -> None:
    """Start the interactive REPL loop.

    Initializes a BeaverAgent with the specified configuration and enters
    a read-eval-print loop, processing user input until EOF, /exit command,
    or KeyboardInterrupt.

    Args:
        model: Optional model name to use (e.g., "MiniMax", "claude-3-opus").
               If not specified, uses the default from config or .env.
        debug: If True, enables debug mode which prints full tracebacks
               for unhandled exceptions in the agent or tool layer.

    Example:
        beaver run                    # Start REPL with default settings
        beaver run --model MiniMax    # Start REPL using MiniMax model
        beaver run --debug            # Start REPL with debug output enabled
    """
    config = load_config(debug=debug)
    if model:
        config.model.name = model
    run_repl(config)


@app.command()
def chat(
    query: str = typer.Option(..., "--query", "-q", help="Query content"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Specify model name"),
) -> None:
    """Execute a single query and exit.

    Initializes a BeaverAgent, sends the query for processing, prints the
    response, and exits immediately. Useful for non-interactive scripts
    or one-off commands.

    Args:
        query: The user query string to process through the agent.
        model: Optional model name to use (e.g., "MiniMax", "claude-3-opus").
               If not specified, uses the default from config or .env.

    Example:
        beaver chat -q "Explain what a structlog is"
        beaver chat -q "Write a hello world in Python" --model MiniMax
    """
    try:
        config = load_config()
    except Exception as e:
        logger.error("chat_load_config_failed", exc_info=e)
        console.print(f"[red]Config load failed:[/red] {e}")
        raise typer.Exit(1)
    if model:
        config.model.name = model
    try:
        chat_command(config, query)
    except Exception as e:
        logger.error("chat_command_failed", query=query, exc_info=e)
        console.print(f"[red]Chat command failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def model(
    show: bool = typer.Option(False, "--show", help="Show current model configuration"),
    url: Optional[str] = typer.Option(None, "--url", help="Set API Base URL"),
    token: Optional[str] = typer.Option(None, "--token", help="Set API Token"),
    name: Optional[str] = typer.Option(None, "--name", help="Set model name"),
) -> None:
    """Display or configure the LLM model settings.

    Supports showing the current configuration, or setting API URL, Token, and model name
    via options. Configuration is automatically written to the .env file.

    Examples:
        beaver model --show              # Show current configuration
        beaver model --url <url>        # Set API Base URL
        beaver model --token <token>    # Set API Token
        beaver model --name MiniMax-M2.7 # Set model name
    """
    from dotenv import load_dotenv, set_key
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    load_dotenv(env_path)

    if url is not None:
        set_key(env_path, "MINIMAX_API_BASE", url)
        console.print(f"[green]API URL set:[/green] {url}")

    if token is not None:
        set_key(env_path, "MINIMAX_API_KEY", token)
        console.print(f"[green]API Token set[/green] (masked)")

    if name is not None:
        set_key(env_path, "MINIMAX_MODEL_NAME", name)
        console.print(f"[green]Model name set:[/green] {name}")

    if show or (url is None and token is None and name is None):
        config = load_config()
        console.print(f"[green]Model:[/green] {config.model.name}")
        console.print(f"[green]Provider:[/green] {config.model.provider}")
        console.print(f"[green]API Base:[/green] {config.model.api_base}")
        # Mask token in output
        key = config.model.api_key
        if key and len(key) > 8:
            masked = key[:6] + "..." + key[-4:]
        else:
            masked = "***" if key else "[not set]"
        console.print(f"[green]API Key:[/green] {masked}")


@app.command()
def map(
    path: str = typer.Option(".", "--path", help="Directory path to scan"),
) -> None:
    """Generate code map index (.beaver/).

    Performs AST static analysis on the specified directory to produce a machine-readable
    code index:
    - index.json       File tree + module import/export relationships
    - dep_graph.json   Dependency graph
    - entry_points.json Entry points (main functions, etc.)

    Pure static analysis, zero LLM calls.

    Examples:
        beaver map                  # Scan current directory
        beaver map --path ./myproject  # Scan specified directory
    """
    from beaver_agent.tools.mapper import generate

    try:
        result = generate(Path(path))
    except Exception as e:
        logger.error("map_command_failed", path=path, exc_info=e)
        console.print(f"[red]Code map generation failed:[/red] {e}")
        raise typer.Exit(1)
    console.print(
        f"[green]✓[/green] Parsed {result['parsed_files']}/{result['total_files']} Python files"
    )
    console.print(f"[green]✓[/green] Found {result['entry_points']} entry points")
    console.print(f"[green]✓[/green] Output directory: {result['output_dir']}")


@app.command()
def version() -> None:
    """Display version information"""
    from beaver_agent import __version__

    console.print(f"[green]Beaver Agent[/green] v{__version__}")


@app.command()
def setup(
    force: bool = typer.Option(False, "--force", "-f", help="Force reconfigure, overwrite existing .env"),
) -> None:
    """First-time setup — create .env from template and guide user through API Key configuration.

    Copies .env.example to .env, optionally opens the file in the user's preferred editor,
    and validates that required fields are populated before completing.

    Args:
        force: If False (default) and .env already exists, aborts without modification.
               If True, overwrites existing .env with a fresh copy of .env.example.

    Raises:
        typer.Exit(1): If .env.example template is missing from the project directory.

    Example:
        beaver setup           # Create .env if it doesn't exist
        beaver setup --force    # Overwrite existing .env with fresh template
    """
    import os
    import shutil
    from pathlib import Path

    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists() and not force:
        console.print("[yellow].env already exists[/yellow], use [bold]--force[/bold] to overwrite")
        return

    if not env_example.exists():
        console.print("[red].env.example not found[/red], cannot create .env")
        raise typer.Exit(1)

    # Copy template
    shutil.copy(env_example, env_file)

    # Read existing content
    content = env_file.read_text()

    console.print("\n[bold cyan]🦫 Beaver Agent First-Time Setup[/bold cyan]\n")
    console.print("Please fill in your API Key (edit the .env file directly)\n")
    console.print(f"[dim]{env_file.absolute()}[/dim]\n")

    # Open editor
    editor = os.environ.get("EDITOR")
    if editor:
        import subprocess

        subprocess.run([editor, str(env_file)])
    else:
        console.print("[dim]Please manually edit the .env file to add your API Key[/dim]")
        console.print(f"[dim]  nano {env_file.absolute()}[/dim]")

    # Validate
    new_content = env_file.read_text()
    if "your_" in new_content or "your_" in content:
        console.print("\n[yellow]⚠️  Some fields are not filled — please ensure the following are configured:[/yellow]")
        for line in new_content.splitlines():
            if "=" in line and ("your_" in line or line.strip().startswith("#")):
                pass
            elif "=" in line and not line.strip().startswith("#"):
                key = line.split("=")[0]
                val = line.split("=", 1)[1].strip()
                if val in ("", "your_...here", "your_g...here"):
                    console.print(f"  [red]✗[/red] {key} not filled")
                else:
                    console.print(f"  [green]✓[/green] {key}")
    else:
        console.print("\n[green]✅ Setup complete! Run [bold]beaver run[/bold] to start[/green]")


if __name__ == "__main__":
    app()
