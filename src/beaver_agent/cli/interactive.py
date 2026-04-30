"""Beaver Bot Interactive REPL"""

import sys
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from beaver_agent.core.agent import BeaverAgent
from beaver_agent.core.config import BeaverConfig
from beaver_agent.cli.commands import handle_command


console = Console()


def run_repl(config: BeaverConfig) -> None:
    """Run the interactive REPL loop"""

    # Print welcome banner
    if config.cli.welcome_banner:
        console.print(Panel(config.cli.welcome_banner, border_style="cyan"))

    # Initialize agent
    agent = BeaverAgent(config)

    # Main loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask(
                f"[bold cyan]{config.cli.prompt}>[/bold cyan]",
                default=""
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
            with console.status("[bold green]思考中...") as status:
                response = agent.run(user_input)

            # Display response
            if response:
                console.print(Markdown(response))

        except KeyboardInterrupt:
            console.print("\n[yellow]退出中...[/yellow]")
            break
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]错误:[/red] {e}")
            if config.app.debug:
                import traceback
                traceback.print_exc()

    console.print("[blue]下次见! 👋[/blue]")


def print_welcome(config: BeaverConfig) -> None:
    """Print welcome message"""
    console.print(Panel(
        f"[bold cyan]🦫 Beaver Bot[/bold cyan] v{config.app.version}\n\n"
        f"[dim]输入 [green]/help[/green] 查看帮助[/dim]\n"
        f"[dim]输入 [red]/exit[/red] 退出[/dim]",
        title="Welcome",
        border_style="cyan"
    ))
