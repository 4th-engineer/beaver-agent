"""Beaver Agent CLI Commands"""

import tempfile
import structlog
from pathlib import Path

from rich.console import Console

from beaver_agent.core.config import BeaverConfig, load_config
from beaver_agent.core.agent import BeaverAgent
from beaver_agent.tools.browser_tool import BrowserTool
from beaver_agent.tools.code_analyzer import analyze_repository
from beaver_agent.tools.mapper import generate


logger = structlog.get_logger()


__all__ = [
    "handle_command",
    "print_help",
    "show_model_info",
    "show_status",
    "chat_command",
    "model_command",
]

console = Console()


def handle_command(cmd: str, config: BeaverConfig, agent: BeaverAgent) -> bool:
    """Handle built-in slash commands from the REPL.

    Parses user input starting with "/" and executes the corresponding
    built-in command. Supports model switching, debugging, browsing, and more.

    Args:
        cmd: The raw command string input by the user (e.g., "/help", "/model gpt-4")
        config: The Beaver configuration object containing model, app, and CLI settings
        agent: The active BeaverAgent instance for accessing session state

    Returns:
        True if the REPL should continue running, False if the user issued /exit

    Supported Commands:
        /exit, /quit, /q   - Exit the REPL (returns False)
        /help, /h, ?      - Display help message
        /clear, /reset    - Clear the terminal screen
        /model            - Display current model name and provider
        /model <name>     - Switch to a different model by name
        /status           - Display agent session status
        /debug            - Toggle debug mode on/off
        /analyze          - Analyze the repository structure
        /browse <url>     - Open a URL and retrieve content
        /screenshot       - Take a screenshot of the current browser page
    """
    cmd = cmd.strip().lower()

    # Exit commands
    if cmd in ("/exit", "/quit", "/q"):
        console.print("[blue]下次见! 👋[/blue]")
        return False

    # Help
    if cmd in ("/help", "/h", "?"):
        print_help()
        return True

    # Clear screen
    if cmd in ("/clear", "/reset"):
        console.clear()
        return True

    # Model info
    if cmd == "/model":
        show_model_info(config)
        return True

    # Status
    if cmd == "/status":
        try:
            show_status(agent)
        except Exception as e:
            logger.error("status_command_failed", exc_info=e)
            console.print(f"[red]状态获取失败:[/red] {e}")
        return True

    # Switch model
    if cmd.startswith("/model "):
        new_model = cmd.split(" ", 1)[1].strip()
        if new_model:
            config.model.name = new_model
            console.print(f"[green]模型已切换为:[/green] {config.model.name}")
        else:
            console.print("[yellow]请指定模型名称[/yellow]")
        return True

    # Debug toggle
    if cmd == "/debug":
        try:
            config.app.debug = not config.app.debug
            console.print(f"[yellow]调试模式:[/yellow] {'开启' if config.app.debug else '关闭'}")
        except Exception as e:
            logger.error("debug_toggle_failed", exc_info=e)
            console.print(f"[red]调试模式切换失败:[/red] {e}")
        return True

    # Analyze repository
    if cmd == "/analyze":
        try:
            result = analyze_repository(str(Path(__file__).parent.parent.parent.parent))
            console.print(result)
        except Exception as e:
            logger.error("analyze_command_failed", exc_info=e)
            console.print(f"[red]分析失败:[/red] {e}")
        return True

    # Browse URL
    if cmd.startswith("/browse "):
        url = cmd.split(" ", 1)[1].strip()
        if not url.startswith("http"):
            url = "https://" + url
        try:
            bt = BrowserTool()
            result = bt.open(url)
            console.print(f"[green]已打开:[/green] {url}\n{result}")
        except Exception as e:
            logger.error("browse_command_failed", url=url, exc_info=e)
            console.print(f"[red]浏览失败:[/red] {e}")
        return True

    # Screenshot
    if cmd == "/screenshot":
        try:
            bt = BrowserTool()
            bt.open("https://example.com")
            ss_path = tempfile.mktemp(suffix=".png")
            result = bt.screenshot(ss_path, full=True)
            console.print(f"[green]{result}[/green]\n路径: {ss_path}")
        except Exception as e:
            logger.error("screenshot_command_failed", exc_info=e)
            console.print(f"[red]截图失败:[/red] {e}")
        return True

    # Map / code index
    if cmd == "/map":
        try:
            result = generate(Path.cwd())
            console.print(
                f"[green]✓[/green] 解析 {result['parsed_files']}/{result['total_files']} 个 Python 文件"
            )
            console.print(f"[green]✓[/green] 找到 {result['entry_points']} 个入口点")
            console.print(f"[green]✓[/green] 输出目录: {result['output_dir']}")
        except Exception as e:
            logger.error("map_command_failed", exc_info=e)
            console.print(f"[red]代码地图生成失败:[/red] {e}")
        return True

    # Stats
    if cmd == "/stats":
        handle_stats_command(Path.cwd())
        return True

    # Self-check
    if cmd == "/self-check":
        handle_self_check_command(Path.cwd())
        return True

    # Unknown command
    console.print(f"[red]未知命令:[/red] {cmd}\n输入 [green]/help[/green] 查看可用命令")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# /stats  - Project statistics
# ─────────────────────────────────────────────────────────────────────────────

def _get_project_stats(root: Path) -> dict:
    """Gather project statistics: files, tests, LOC, language breakdown.

    Args:
        root: The project root directory to gather statistics from.

    Returns:
        A dict with keys: total_files, python_files, test_files, src_files,
        total_loc, languages (ext->count), test_count, last_commit, branch.

    Walks the project tree excluding common non-source directories (.git, .venv,
    __pycache__, etc.) and runs git commands to get branch and last commit info.
    """
    import subprocess

    stats = {
        "total_files": 0,
        "python_files": 0,
        "test_files": 0,
        "src_files": 0,
        "total_loc": 0,
        "languages": {},
        "test_count": 0,
        "last_commit": "",
        "branch": "",
    }

    # Branch + last commit
    try:
        stats["branch"] = subprocess.check_output(
            ["git", "branch", "--show-current"], text=True, cwd=root
        ).strip()
        stats["last_commit"] = subprocess.check_output(
            ["git", "log", "-1", "--format=%h %s"], text=True, cwd=root
        ).strip()
    except subprocess.CalledProcessError:
        pass

    # Walk tree
    skip_dirs = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", ".eggs"}
    for path in root.rglob("*"):
        if any(p in path.parts for p in skip_dirs):
            continue
        if path.is_file():
            ext = path.suffix.lower()
            lang = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".yaml": "YAML", ".yml": "YAML", ".md": "Markdown", ".txt": "Text", ".sh": "Shell"}.get(ext, ext.strip(".").upper() or "Other")
            stats["languages"][lang] = stats["languages"].get(lang, 0) + 1
            stats["total_files"] += 1
            if ext == ".py":
                stats["python_files"] += 1
                if "/tests/" in str(path) or path.name.startswith("test_"):
                    stats["test_files"] += 1
                if "/src/" in str(path):
                    stats["src_files"] += 1
                # Quick LOC estimate via line count
                try:
                    with open(path) as f:
                        stats["total_loc"] += sum(1 for _ in f)
                except (OSError, UnicodeDecodeError):
                    pass

    # Count pytest tests
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            capture_output=True, text=True, cwd=root, timeout=30
        )
        for line in result.stdout.splitlines():
            if " test" in line or "tests collected" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p[0].isdigit() and i+1 < len(parts) and "test" in parts[i+1]:
                        try:
                            stats["test_count"] = int(p)
                        except ValueError:
                            pass
                        break
                break
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    return stats


def _print_stats(root: Path) -> None:
    """Print formatted project statistics."""
    stats = _get_project_stats(root)
    console.print("\n[bold cyan]📊 项目统计[/bold cyan]")
    console.print(f"  总文件数   : {stats['total_files']}")
    console.print(f"  Python文件 : {stats['python_files']} (src: {stats['src_files']}, test: {stats['test_files']})")
    console.print(f"  测试数量   : {stats['test_count']}")
    console.print(f"  代码行数   : {stats['total_loc']:,}")
    console.print(f"  语言分布   : {', '.join(f'{k}={v}' for k,v in sorted(stats['languages'].items()))}")
    console.print(f"  当前分支   : [green]{stats['branch']}[/green]")
    console.print(f"  最近提交   : {stats['last_commit']}")


# ─────────────────────────────────────────────────────────────────────────────
# /self-check - Health check
# ─────────────────────────────────────────────────────────────────────────────

def _run_self_check(root: Path) -> None:
    """Run self-check: pytest + git status + config integrity.

    Args:
        root: The project root directory to run self-checks against.

    Runs three health checks in sequence:
    1. Git status - shows dirty working tree
    2. Config integrity - loads config and checks API key presence
    3. Pytest - runs the test suite with a 120s timeout

    All output is printed to console. Exceptions from subprocess calls
    (git, pytest) are caught and displayed as console errors rather than
    propagating.
    """
    import subprocess
    import os

    console.print("\n[bold cyan]🔍 自检中...[/bold cyan]\n")

    # 1. Git status
    console.print("[yellow]Git 状态:[/yellow]")
    try:
        status = subprocess.check_output(
            ["git", "status", "-s"], text=True, cwd=root
        ).strip()
        if status:
            console.print(f"  [red]有未提交文件:[/red]\n{status}")
        else:
            console.print("  [green]✓ 工作区干净[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"  [red]✗ git status failed[/red] {e}")

    # 2. Config integrity check
    console.print("\n[yellow]配置完整性:[/yellow]")
    try:
        from beaver_agent.core.config import load_config
        cfg = load_config()
        has_key = bool(cfg.model.api_key and cfg.model.api_key not in ("", "***"))
        console.print(f"  [green]✓[/green] 模型: {cfg.model.provider}/{cfg.model.name}")
        console.print(f"  [green]✓[/green] API Key: {'已配置' if has_key else '[red]未配置[/red]'}")
    except Exception as e:
        console.print(f"  [red]✗ 配置加载失败: {e}[/red]")

    # 3. Run tests
    console.print("\n[yellow]测试:[/yellow]")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "-q", "--tb=no", "-x"],
            capture_output=True, text=True, cwd=root, timeout=120, env={**os.environ, "PYTHONPATH": "src"}
        )
        if result.returncode == 0:
            # Extract summary
            lines = result.stdout.strip().splitlines()
            summary = next((l for l in reversed(lines) if "passed" in l or "error" in l), lines[-1] if lines else "unknown")
            console.print(f"  [green]✓[/green] {summary}")
        elif result.returncode == 2:
            console.print(f"  [red]✗ 测试收集失败[/red]")
        else:
            # Find failure
            console.print(f"  [red]✗ 测试失败[/red]")
            for line in result.stdout.splitlines():
                if "FAILED" in line or "ERROR" in line:
                    console.print(f"    {line.strip()}")
                    break
    except subprocess.TimeoutExpired:
        console.print("  [red]✗ 测试超时 (>120s)[/red]")
    except Exception as e:
        console.print(f"  [red]✗ 测试运行失败: {e}[/red]")

    console.print()


def handle_stats_command(root: Path) -> None:
    """Handle /stats command - display project statistics.

    Args:
        root: The project root directory to gather statistics from.

    Retrieves project stats via _get_project_stats and displays them
    using _print_stats. Any exceptions are caught and displayed to the user.
    """
    try:
        _print_stats(root)
    except Exception as e:
        logger.error("stats_command_failed", exc_info=e)
        console.print(f"[red]统计失败:[/red] {e}")


def handle_self_check_command(root: Path) -> None:
    """Handle /self-check command - run health checks.

    Args:
        root: The project root directory to run self-checks against.

    Runs three health checks: git status, config integrity, and pytest.
    Any exceptions from _run_self_check are caught and displayed to the user.
    """
    try:
        _run_self_check(root)
    except Exception as e:
        logger.error("self_check_command_failed", exc_info=e)
        console.print(f"[red]自检失败:[/red] {e}")


def print_help() -> None:
    """Print the help message with available commands and features.

    Displays a formatted markdown table of all available slash commands,
    a list of agent capabilities, and example usage patterns.
    Uses Rich's Markdown renderer for proper syntax highlighting.
    """
    help_text = """
# 🦫 Beaver Agent 帮助

## 命令
| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助 |
| `/exit` | 退出程序 |
| `/clear` | 清屏 |
| `/model` | 显示当前模型 |
| `/model <name>` | 切换模型 |
| `/status` | 显示状态 |
| `/debug` | 切换调试模式 |
| `/analyze` | 分析代码仓库结构 |
| `/browse <url>` | 打开网页并获取内容 |
| `/screenshot` | 截取当前页面截图 |
| `/map` | 生成代码地图索引 |
| `/stats` | 项目统计（文件数、代码行数等） |
| `/self-check` | 自检（git status + pytest + 配置完整性） |

## 功能
- **代码生成**: 描述你想要的功能，我帮你写代码
- **代码审查**: 分析代码问题，提供优化建议
- **调试助手**: 帮你分析错误原因
- **GitHub 集成**: 管理仓库、Issue、PR

## 示例
```
帮我写一个快排算法
帮我 review /path/to/file.py
解释一下这段代码的作用
```
"""
    from rich.markdown import Markdown

    console.print(Markdown(help_text))


def show_model_info(config: BeaverConfig) -> None:
    """Display the current model's name and provider.

    Args:
        config: The Beaver configuration containing model settings
    """
    console.print(f"[green]当前模型:[/green] {config.model.name}")
    console.print(f"[green]Provider:[/green] {config.model.provider}")


def show_status(agent: BeaverAgent) -> None:
    """Display the agent's current runtime status.

    Args:
        agent: The active BeaverAgent instance to query for status.
            Provides access to session_id, config, memory, and tool_router.
    """
    session_history_count = len(agent.memory.get_history())
    memory_stats = agent.long_term_memory.get_stats()
    total_tools = len(agent.tool_router.list_tools())
    model_name = agent.config.model.name
    provider = agent.config.model.provider

    console.print(f"[green]会话ID:[/green] {agent.session_id}")
    console.print(f"[green]模型:[/green] {model_name} ({provider})")
    console.print(f"[green]会话历史:[/green] {session_history_count} 条消息")
    console.print(f"[green]长期记忆:[/green] {memory_stats.get('total_entries', 0)} 条记忆")
    console.print(f"[green]工具数量:[/green] {total_tools} 个工具")


def chat_command(config: BeaverConfig, query: str) -> None:
    """Execute a single chat query and exit.

    Args:
        config: The Beaver configuration object
        query: The user's query string to process
    """
    agent = BeaverAgent(config)
    response = agent.run(query)
    console.print(response)


def model_command(show: bool) -> None:
    """Display or manage the current LLM model.

    Args:
        show: If True, display current model information
    """
    config = load_config()
    show_model_info(config)
