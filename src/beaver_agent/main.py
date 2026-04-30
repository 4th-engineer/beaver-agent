"""Beaver Agent CLI - Main Entry Point"""

import typer
from rich.console import Console
from typing import Optional

from beaver_agent.cli.interactive import run_repl
from beaver_agent.cli.commands import chat_command, model_command
from beaver_agent.core.agent import BeaverAgent
from beaver_agent.core.config import load_config

app = typer.Typer(
    name="beaver",
    help="🦫 Beaver Agent - AI Coding Assistant",
    add_completion=False,
)

console = Console()


@app.command()
def run(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="指定模型"),
    debug: bool = typer.Option(False, "--debug", "-d", help="调试模式"),
):
    """启动交互式 CLI"""
    config = load_config(debug=debug)
    if model:
        config.model.name = model
    run_repl(config)


@app.command()
def chat(
    query: str = typer.Option(..., "--query", "-q", help="查询内容"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="指定模型"),
):
    """单次查询模式"""
    config = load_config()
    if model:
        config.model.name = model
    chat_command(config, query)


@app.command()
def model(
    show: bool = typer.Option(False, "--show", help="显示当前模型"),
):
    """查看/切换模型"""
    model_command(show)


@app.command()
def version():
    """显示版本信息"""
    from beaver_agent import __version__
    console.print(f"[green]Beaver Agent[/green] v{__version__}")


if __name__ == "__main__":
    app()
