"""Beaver Agent CLI - Main Entry Point"""

import typer
from pathlib import Path
from rich.console import Console
from typing import Optional

from beaver_agent.cli.interactive import run_repl
from beaver_agent.cli.commands import chat_command, model_command
from beaver_agent.core.agent import BeaverAgent
from beaver_agent.core.config import load_config

__all__ = ["app"]

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
    query: str = typer.Option(..., "--query", "-q", help="查询内容"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="指定模型"),
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
    config = load_config()
    if model:
        config.model.name = model
    chat_command(config, query)


@app.command()
def model(
    show: bool = typer.Option(False, "--show", help="显示当前模型配置"),
    url: Optional[str] = typer.Option(None, "--url", help="设置 API Base URL"),
    token: Optional[str] = typer.Option(None, "--token", help="设置 API Token"),
    name: Optional[str] = typer.Option(None, "--name", help="设置模型名称"),
) -> None:
    """显示或配置 LLM 模型设置。

    支持显示当前配置，或通过选项设置 API URL、Token、模型名称。
    配置会自动写入 .env 文件。

    Examples:
        beaver model --show              # 显示当前配置
        beaver model --url <url>        # 设置 API Base URL
        beaver model --token <token>    # 设置 API Token
        beaver model --name MiniMax-M2.7 # 设置模型名称
    """
    from dotenv import load_dotenv, set_key
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    load_dotenv(env_path)

    if url is not None:
        set_key(env_path, "MINIMAX_API_BASE", url)
        console.print(f"[green]API URL 已设置:[/green] {url}")

    if token is not None:
        set_key(env_path, "MINIMAX_API_KEY", token)
        console.print(f"[green]API Token 已设置[/green]（已脱敏）")

    if name is not None:
        set_key(env_path, "MINIMAX_MODEL_NAME", name)
        console.print(f"[green]模型名称已设置:[/green] {name}")

    if show or (url is None and token is None and name is None):
        config = load_config()
        console.print(f"[green]模型:[/green] {config.model.name}")
        console.print(f"[green]Provider:[/green] {config.model.provider}")
        console.print(f"[green]API Base:[/green] {config.model.api_base}")
        # Mask token in output
        key = config.model.api_key
        if key and len(key) > 8:
            masked = key[:6] + "..." + key[-4:]
        else:
            masked = "***" if key else "[未设置]"
        console.print(f"[green]API Key:[/green] {masked}")


@app.command()
def map(
    path: str = typer.Option(".", "--path", help="要扫描的目录路径"),
) -> None:
    """生成代码地图索引 (.beaver/)

    对指定目录进行 AST 静态分析，生成机器可读的代码索引：
    - index.json       文件树 + 模块导入/导出关系
    - dep_graph.json   依赖图
    - entry_points.json 入口点 (main 函数等)

    纯静态分析，零 LLM 调用。

    Examples:
        beaver map                  # 扫描当前目录
        beaver map --path ./myproject  # 扫描指定目录
    """
    from beaver_agent.tools.mapper import generate

    result = generate(Path(path))
    console.print(
        f"[green]✓[/green] 解析 {result['parsed_files']}/{result['total_files']} 个 Python 文件"
    )
    console.print(f"[green]✓[/green] 找到 {result['entry_points']} 个入口点")
    console.print(f"[green]✓[/green] 输出目录: {result['output_dir']}")


@app.command()
def version():
    """显示版本信息"""
    from beaver_agent import __version__

    console.print(f"[green]Beaver Agent[/green] v{__version__}")


@app.command()
def setup(
    force: bool = typer.Option(False, "--force", "-f", help="强制重新配置，覆盖已有 .env"),
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
