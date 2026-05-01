"""Beaver Agent Agent Core v2 - With LLM Integration"""

import uuid
from typing import Optional, Dict, Any, List

import structlog

from beaver_agent.core.config import BeaverConfig
from beaver_agent.core.llm_client import LLMClient
from beaver_agent.core.intent_parser import IntentParser
from beaver_agent.core.task_planner import TaskPlanner
from beaver_agent.core.tool_router import ToolRouter
from beaver_agent.core.memory.session import SessionMemory
from beaver_agent.core.conversation_logger import ConversationLogger
from beaver_agent.core.data_store import init_data_store

logger = structlog.get_logger()


class BeaverAgent:
    """Beaver Agent Agent - Main orchestration class with LLM"""

    def __init__(self, config: BeaverConfig):
        self.config = config
        
        # Initialize data store and run migrations BEFORE other init
        try:
            self.data_store = init_data_store()
            logger.info("data_store_initialized", 
                       version=self.data_store.get_version().raw,
                       stats=self.data_store.get_stats())
        except Exception as e:
            logger.error("data_store_init_failed", error=str(e))
            raise
        
        self.session_id = str(uuid.uuid4())[:8]
        self.memory = SessionMemory()
        self.intent_parser = IntentParser()
        self.task_planner = TaskPlanner()
        self.tool_router = ToolRouter(config)
        self.conversation_history: List[Dict[str, str]] = []
        self.logger = ConversationLogger()

        # Initialize LLM
        try:
            self.llm = self.tool_router.get_llm_client()
        except Exception as e:
            logger.warning("llm_init_failed", error=str(e))
            self.llm = None

        # Start conversation logging
        self.logger.start_session(self.session_id)

        logger.info("agent_initialized", session_id=self.session_id, model=config.model.name)

    def run(self, user_input: str) -> str:
        """Main agent loop: parse intent → plan tasks → execute tools → return response"""

        logger.info("processing_request", input=user_input[:100])

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_input})

        # Log user input
        self.logger.log_user_input(user_input, intent=None)

        # Step 1: Parse intent
        intent = self.intent_parser.parse(user_input)
        logger.debug("intent_parsed", intent=intent)

        # Step 2: Plan tasks
        tasks = self.task_planner.plan(user_input, intent)
        logger.debug("tasks_planned", task_count=len(tasks))

        # Step 3: Execute tools and collect results
        tool_results = []
        for task in tasks:
            result = self.tool_router.route(task)
            tool_results.append(result)

            # Log tool call
            self.logger.log_tool_call(
                tool_name=task.get("tool", "unknown"),
                action=task.get("action", ""),
                params=task.get("params", {}),
                result=result,
                success=result.get("success", False),
            )

        # Step 4: Generate response using LLM
        response = self._generate_response(user_input, intent, tool_results)

        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": response})

        return response

    def _generate_response(
        self,
        user_input: str,
        intent: str,
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """Generate final response using LLM with tool results"""

        context = self._build_context(tool_results)

        if not self.llm:
            return self._generate_fallback_response(intent, context)

        # Build conversation context for LLM
        messages = []

        # System prompt
        system = """You are Beaver Agent, an expert AI coding assistant.
You help users with:
- Writing and generating code
- Code review and quality analysis
- Debugging and error fixing
- GitHub operations

Be concise, helpful, and technical.
Always provide actionable suggestions."""

        messages.append({"role": "system", "content": system})

        # Add conversation history (last 10 messages)
        for msg in self.conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current context
        if context:
            context_msg = f"Here are the results of tools executed:\n{context}\n\nUser's latest request: {user_input}"
            messages.append({"role": "system", "content": context_msg})

        # Log LLM request
        self.logger.log_llm_request(
            messages=messages,
            model=self.llm.model if self.llm else "unknown",
            provider=self.llm.provider if self.llm else "unknown",
        )

        try:
            response = self.llm._call(messages, max_tokens=2048)

            # Log LLM response
            self.logger.log_llm_response(
                content=response.content,
                model=response.model,
                usage=response.usage,
            )

            return response.content
        except Exception as e:
            logger.error("llm_response_failed", error=str(e))

            # Log error
            self.logger.log_llm_response(
                content="",
                model=self.llm.model if self.llm else "unknown",
                error=str(e),
            )

            return self._generate_fallback_response(intent, context)

    def _build_context(self, tool_results: List[Dict[str, Any]]) -> str:
        """Build context string from tool results — tool-specific summarization."""
        if not tool_results:
            return ""

        table = Table(
            title="🔧 工具执行结果",
            show_header=True,
            header_style="bold cyan",
            border_style="cyan",
            box=None,
            padding=(0, 1),
        )
        table.add_column("状态", justify="center", style="green", no_wrap=True)
        table.add_column("工具", style="bold")
        table.add_column("结果", style="white")

        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            success = result.get("success", False)
            data = result.get("data", "")
            error = result.get("error", "")

            status = "[green]✓[/green]" if success else "[red]✗[/red]"
            content = data if success else f"[red]{error}[/red]"

            # Tool-specific summarization
            content = self._summarize_content(tool_name, content)

            table.add_row(status, tool_name, content)

        # Render table to string
        from io import StringIO
        buf = StringIO()
        tmp_console = Console(file=buf, force_terminal=True)
        tmp_console.print(table)
        return buf.getvalue()

    def _summarize_content(self, tool: str, content: str) -> str:
        """Summarize long tool output based on tool type — no truncation, highlight key info."""
        if not isinstance(content, str):
            content = str(content)

        # For file read: show first 20 lines + file stats
        if tool in ("read_file", "Read"):
            lines = content.strip().split("\n")
            if len(lines) > 24:
                total = len(lines)
                preview = "\n".join(lines[:20])
                # Extract key info from first lines
                first_lines = lines[:5]
                stats = ""
                for fl in first_lines:
                    if "total lines" in fl.lower() or "file" in fl.lower():
                        stats += f" | {fl.strip()}"
                return (
                    f"{preview}\n"
                    f"[dim]... ({total - 20} more lines){stats}[/dim]\n\n"
                    "[cyan]📄 文件预览 (前 20 行)[/cyan]"
                )
            return content

        # For terminal output: show last 30 lines (usually the important part)
        if tool in ("terminal", "exec", "bash", "run_command"):
            lines = content.strip().split("\n")
            if len(lines) > 35:
                # Try to find error/warning patterns
                error_lines = [l for l in lines if any(k in l.lower() for k in ("error", "fail", "exception", "traceback", "warning", "warn"))]
                if error_lines:
                    # Show last 15 normal + all error lines
                    last_normal = lines[-20:] if len(lines) > 20 else lines
                    errors = "\n".join(error_lines[:10])
                    return (
                        f"{chr(10).join(last_normal[:15])}\n\n"
                        f"[red]⚠️ 发现问题 ({len(error_lines)} 处):[/red]\n{errors}"
                    )
                return (
                    f"{chr(10).join(lines[-30:])}\n\n"
                    f"[dim]↑ 前 {len(lines) - 30} 行...[/dim]"
                )
            return content

        # For search results: show top matches with context
        if tool in ("search", "grep", "SearchFiles"):
            lines = content.strip().split("\n")
            if len(lines) > 20:
                # Show first 10 + count summary
                return (
                    f"{chr(10).join(lines[:10])}\n\n"
                    f"[dim]... 共 {len(lines)} 条匹配结果[/dim]"
                )
            return content

        # For JSON data: pretty-print with syntax highlight
        if tool in ("mcp", "API", "http", "fetch"):
            import json
            try:
                parsed = json.loads(content)
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
                if len(formatted) > 2000:
                    # Show structure summary + first 50 lines
                    lines = formatted.split("\n")
                    return (
                        f"{chr(10).join(lines[:50])}\n\n"
                        f"[dim]JSON 结构: {self._json_summary(parsed)}[/dim]"
                    )
                return formatted
            except (json.JSONDecodeError, TypeError):
                pass

        # For git/status: keep last 20 lines
        if tool in ("git", "git_status", "git_log"):
            lines = content.strip().split("\n")
            if len(lines) > 25:
                return (
                    f"{chr(10).join(lines[-20:])}\n\n"
                    f"[dim]↑ 前 {len(lines) - 20} 行...[/dim]"
                )
            return content

        # Default: if really long, show structure summary
        if len(content) > 3000:
            lines = content.strip().split("\n")
            return (
                f"{chr(10).join(lines[:30])}\n\n"
                f"[dim]...(共 {len(lines)} 行, 约 {len(content)} 字符)[/dim]"
            )

        return content

    def _json_summary(self, obj: Any, depth: int = 0) -> str:
        """Build a one-line summary of JSON structure."""
        if depth > 3:
            return "..."
        if isinstance(obj, dict):
            keys = list(obj.keys())[:5]
            summary = ", ".join(f"{k}={self._json_summary(obj[k], depth+1)}" for k in keys)
            suffix = f" (+{len(obj)-5} keys)" if len(obj) > 5 else ""
            return f"{{{summary}{suffix}}}"
        elif isinstance(obj, list):
            return f"[{len(obj)} items]"
        elif isinstance(obj, str):
            return f'"{obj[:20]}{"..." if len(obj) > 20 else ""}"'
        return repr(obj)[:30]

    def _generate_fallback_response(self, intent: str, context: str) -> str:
        """Generate response without LLM (fallback mode)"""

        if intent == "code_generation":
            return f"""## 💻 代码生成

**状态**: 工具已执行

{context}

---

💡 如需完整 AI 代码生成能力，请配置:
- `OPENROUTER_API_KEY` 或 `ANTHROPIC_API_KEY`
"""

        elif intent == "code_review":
            return f"""## 🔍 代码审查

**状态**: 审查完成

{context}

---

💡 配置 LLM API key 可获取深度 AI 代码分析。
"""

        elif intent == "debug":
            return f"""## 🐛 调试分析

**状态**: 分析完成

{context}

---

💡 配置 LLM API key 可获取详细错误根因分析。
"""

        elif intent == "github_operation":
            return f"""## 🐙 GitHub 操作

{context}
"""

        else:
            return f"""## 💬 对话

你好！我是 Beaver Agent 🦫

**上次操作结果**:
{context or "暂无"}

---

目前我可以帮你：
- 💻 写代码（描述你想要的功能）
- 🔍 审查代码（分析问题、优化建议）
- 🐛 调试问题（错误分析）
- 🐙 GitHub 操作（仓库、Issue、PR）

输入 [green]/help[/green] 查看更多命令。
"""

    def reset(self) -> None:
        """Reset agent state"""
        self.logger.end_session()
        self.conversation_history.clear()
        self.memory.clear()
        self.session_id = str(uuid.uuid4())[:8]
        self.logger.start_session(self.session_id)
        logger.info("agent_reset", new_session_id=self.session_id)

    def shutdown(self) -> None:
        """Shutdown agent and close log files"""
        self.logger.end_session()
        logger.info("agent_shutdown", session_id=self.session_id)
