"""Beaver Agent CLI Commands"""

import tempfile
import structlog
from pathlib import Path

from rich.console import Console

from beaver_agent.core.config import BeaverConfig, load_config
from beaver_agent.core.agent import BeaverAgent
from beaver_agent.tools.browser_tool import BrowserTool
from beaver_agent.tools.code_analyzer import analyze_repository


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
        config.model.name = cmd.split(" ", 1)[1].strip()
        console.print(f"[green]模型已切换为:[/green] {config.model.name}")
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

    # Unknown command
    console.print(f"[red]未知命令:[/red] {cmd}\n输入 [green]/help[/green] 查看可用命令")
    return True


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
