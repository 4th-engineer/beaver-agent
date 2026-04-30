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


@app.command()
def setup(
    force: bool = typer.Option(False, "--force", "-f", help="强制重新配置，覆盖已有 .env"),
):
    """首次配置 - 创建 .env 并引导填写 API Key"""
    import os
    import shutil
    from pathlib import Path

    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists() and not force:
        console.print("[yellow].env 已存在[/yellow]，使用 [bold]--force[/bold] 强制重新配置")
        return

    if not env_example.exists():
        console.print("[red].env.example 不存在[/red]，无法创建 .env")
        raise typer.Exit(1)

    # 复制模板
    shutil.copy(env_example, env_file)

    # 读取现有内容
    content = env_file.read_text()

    console.print("\n[bold cyan]🦫 Beaver Agent 首次配置[/bold cyan]\n")
    console.print("请填入你的 API Key（直接编辑 .env 文件）\n")
    console.print(f"[dim]{env_file.absolute()}[/dim]\n")

    # 打开编辑器
    editor = os.environ.get("EDITOR")
    if editor:
        import subprocess
        subprocess.run([editor, str(env_file)])
    else:
        console.print("[dim]请手动编辑 .env 文件填入 API Key[/dim]")
        console.print(f"[dim]  nano {env_file.absolute()}[/dim]")

    # 验证
    new_content = env_file.read_text()
    if "your_" in new_content or "your_" in content:
        console.print("\n[yellow]⚠️  检测到未填写的字段，请确保以下项已配置:[/yellow]")
        for line in new_content.splitlines():
            if "=" in line and ("your_" in line or line.strip().startswith("#")):
                pass
            elif "=" in line and not line.strip().startswith("#"):
                key = line.split("=")[0]
                val = line.split("=", 1)[1].strip()
                if val in ("", "your_...here", "your_g...here"):
                    console.print(f"  [red]✗[/red] {key} 未填写")
                else:
                    console.print(f"  [green]✓[/green] {key}")
    else:
        console.print("\n[green]✅ 配置完成！运行 [bold]beaver run[/bold] 开始使用[/green]")


if __name__ == "__main__":
    app()
