"""Beaver Agent Interactive REPL"""

import sys
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from beaver_agent.core.agent import BeaverAgent
from beaver_agent.core.config import BeaverConfig
from beaver_agent.cli.commands import handle_command


console = Console()


def run_repl(config: BeaverConfig) -> None:
    """Run the interactive REPL loop"""

    # Print welcome banner
    if config.cli.welcome_banner:
        console.print(Panel(
            config.cli.welcome_banner,
            title="🦫 Beaver Agent",
            border_style="cyan",
            padding=(1, 2),
        ))

    # Initialize agent
    agent = BeaverAgent(config)

    # Main loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask(
                f"[bold cyan]{config.cli.prompt}>[/bold cyan]",
                default="",
            ).strip()

            if not user_input:
                continue

            # Handle built-in commands
            if user_input.startswith("/"):
                result = handle_command(user_input, config, agent)
                if result is False:  # /exit
                    break
                continue

            # Process through agent
            with console.status(
                "[bold green]🦫 思考中...[/bold green]\n"
                "[dim]分析意图 → 规划任务 → 执行工具[/dim]"
            ) as status:
                response = agent.run(user_input)

            # Display response
            if response:
                _print_response(response)

        except KeyboardInterrupt:
            console.print("\n[yellow]退出中...[/yellow]")
            break
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]✗ 错误:[/red] {e}")
            if config.app.debug:
                import traceback
                traceback.print_exc()

    console.print("[blue]下次见! 👋[/blue]")


def _print_response(response: str) -> None:
    """Print agent response with syntax highlighting for code blocks."""
    # Check if response contains code blocks
    if "```" in response:
        # Print as markdown (handles code blocks with syntax highlighting)
        console.print(Markdown(response, code_theme="monokai"))
    else:
        console.print(response)


def print_welcome(config: BeaverConfig) -> None:
    """Print welcome message"""
    console.print(Panel(
        f"[bold cyan]🦫 Beaver Agent[/bold cyan] v{config.app.version}\n\n"
        f"[dim]输入 [green]/help[/green] 查看帮助    [dim]输入 [red]/exit[/red] 退出[/dim]",
        title="Welcome",
        border_style="cyan",
        padding=(1, 2),
    ))
