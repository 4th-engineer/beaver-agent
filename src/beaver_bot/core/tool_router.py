"""Beaver Bot Tool Router v2 - With LLM integration"""

from typing import Dict, Any, Optional

import structlog

from beaver_bot.core.config import BeaverConfig
from beaver_bot.core.llm_client import LLMClient

logger = structlog.get_logger()


class ToolRouter:
    """Route tasks to appropriate tools"""

    def __init__(self, config: BeaverConfig):
        self.config = config
        self._tool_registry: Dict[str, Any] = {}
        self._llm_client: Optional[LLMClient] = None
        self._register_llm()
        self._register_tools()

    def _register_llm(self) -> None:
        """Initialize LLM client"""
        try:
            self._llm_client = LLMClient(self.config.model)
            logger.info("llm_client_ready", provider=self.config.model.provider)
        except Exception as e:
            logger.error("llm_init_failed", error=str(e))

    def _register_tools(self) -> None:
        """Register all available tools"""
        from beaver_bot.tools.file_tool import FileTool
        from beaver_bot.tools.terminal_tool import TerminalTool
        from beaver_bot.tools.github_tool import GitHubTool
        from beaver_bot.tools.code_gen import CodeGenTool
        from beaver_bot.tools.code_review import CodeReviewTool
        from beaver_bot.tools.debugger import DebuggerTool

        self._tool_registry = {
            "file_tool": FileTool(self.config),
            "terminal_tool": TerminalTool(self.config),
            "github_tool": GitHubTool(self.config),
            "code_gen": CodeGenTool(self.config, self._llm_client),
            "code_review": CodeReviewTool(self.config, self._llm_client),
            "debugger": DebuggerTool(self.config, self._llm_client),
        }

        logger.info("tools_registered", count=len(self._tool_registry))

    def route(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route a task to the appropriate tool"""

        tool_name = task.get("tool")
        action = task.get("action")
        params = task.get("params", {})

        if not tool_name:
            return {"success": False, "error": "No tool specified"}

        if tool_name not in self._tool_registry:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        tool = self._tool_registry[tool_name]

        # Execute the action
        try:
            if hasattr(tool, action):
                result = getattr(tool, action)(**params)
                return {"success": True, "tool": tool_name, "action": action, "data": result}
            else:
                return {"success": False, "error": f"Tool {tool_name} has no action: {action}"}
        except Exception as e:
            logger.error("tool_execution_failed", tool=tool_name, action=action, error=str(e))
            return {"success": False, "error": str(e), "tool": tool_name, "action": action}

    def list_tools(self) -> list:
        """List all registered tools"""
        return list(self._tool_registry.keys())

    def get_tool(self, name: str) -> Optional[Any]:
        """Get a specific tool by name"""
        return self._tool_registry.get(name)

    def get_llm_client(self) -> Optional[LLMClient]:
        """Get the LLM client"""
        return self._llm_client
