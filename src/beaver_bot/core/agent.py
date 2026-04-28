"""Beaver Bot Agent Core"""

import uuid
from typing import Optional, Dict, Any, List

import structlog

from beaver_bot.core.config import BeaverConfig
from beaver_bot.core.intent_parser import IntentParser
from beaver_bot.core.task_planner import TaskPlanner
from beaver_bot.core.tool_router import ToolRouter
from beaver_bot.core.memory.session import SessionMemory

logger = structlog.get_logger()


class BeaverAgent:
    """Beaver Bot Agent - Main orchestration class"""

    def __init__(self, config: BeaverConfig):
        self.config = config
        self.session_id = str(uuid.uuid4())[:8]
        self.memory = SessionMemory()
        self.intent_parser = IntentParser()
        self.task_planner = TaskPlanner()
        self.tool_router = ToolRouter(config)
        self.conversation_history: List[Dict[str, str]] = []

        logger.info("agent_initialized", session_id=self.session_id, model=config.model.name)

    def run(self, user_input: str) -> str:
        """Main agent loop: parse intent → plan tasks → execute tools → return response"""

        logger.info("processing_request", input=user_input[:100])

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_input})

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

        # Build context from tool results
        context = self._build_context(tool_results)

        # Simple response generation (would normally call LLM here)
        if intent == "code_generation":
            return self._handle_code_generation(user_input, tool_results)
        elif intent == "code_review":
            return self._handle_code_review(user_input, tool_results)
        elif intent == "debug":
            return self._handle_debug(user_input, tool_results)
        elif intent == "github_operation":
            return self._handle_github_operation(tool_results)
        else:
            return self._handle_general_chat(user_input, tool_results)

    def _build_context(self, tool_results: List[Dict[str, Any]]) -> str:
        """Build context string from tool results"""
        if not tool_results:
            return ""

        lines = []
        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            success = result.get("success", False)
            data = result.get("data", "")

            status = "✅" if success else "❌"
            lines.append(f"{status} [{tool_name}] {data}")

        return "\n".join(lines)

    def _handle_code_generation(self, user_input: str, tool_results: List) -> str:
        """Handle code generation requests"""
        context = self._build_context(tool_results)
        return f"""## 💻 代码生成

**请求**: {user_input}

**上下文**:
{context}

**说明**: 我已经分析了你的需求，由于目前处于骨架阶段，实际代码生成需要接入 LLM API。

如需完整功能，请配置 `OPENROUTER_API_KEY` 或 `ANTHROPIC_API_KEY`。
"""

    def _handle_code_review(self, user_input: str, tool_results: List) -> str:
        """Handle code review requests"""
        context = self._build_context(tool_results)
        return f"""## 🔍 代码审查

**请求**: {user_input}

**结果**:
{context}

**说明**: 我已获取代码上下文。由于未接入 LLM，无法进行深度分析。
请配置 API Key 后重试。
"""

    def _handle_debug(self, user_input: str, tool_results: List) -> str:
        """Handle debug requests"""
        context = self._build_context(tool_results)
        return f"""## 🐛 调试分析

**请求**: {user_input}

**上下文**:
{context}

**说明**: 已收集调试信息。接入 LLM 后可进行根因分析。
"""

    def _handle_github_operation(self, tool_results: List) -> str:
        """Handle GitHub operations"""
        context = self._build_context(tool_results)
        return f"""## 🐙 GitHub 操作

{context}
"""

    def _handle_general_chat(self, user_input: str, tool_results: List) -> str:
        """Handle general chat"""
        context = self._build_context(tool_results)

        if context:
            return f"""## 💬 对话

**你说**: {user_input}

**上下文**:
{context}
"""

        return f"""## 💬 对话

你好！我是 Beaver Bot 🦫

目前我可以帮你：
- 💻 写代码（描述你想要的功能）
- 🔍 审查代码（分析问题、优化建议）
- 🐛 调试问题（错误分析）
- 🐙 GitHub 操作（仓库、Issue、PR）

输入 [green]/help[/green] 查看更多命令。
"""

    def reset(self) -> None:
        """Reset agent state"""
        self.conversation_history.clear()
        self.memory.clear()
        self.session_id = str(uuid.uuid4())[:8]
        logger.info("agent_reset", new_session_id=self.session_id)
