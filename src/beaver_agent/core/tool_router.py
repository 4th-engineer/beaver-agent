"""Beaver Agent Tool Router - LLM-integrated tool dispatch."""

from typing import Dict, Any, Optional

import structlog

from beaver_agent.core.config import BeaverConfig
from beaver_agent.core.llm_client import LLMClient

logger = structlog.get_logger()

__all__ = ["ToolRouter"]


class ToolRouter:
    """Route tasks to appropriate tools"""

    def __init__(self, config: BeaverConfig):
        """Initialize the ToolRouter with configuration and register all tools and LLM.

        Args:
            config: BeaverConfig instance containing model and tool configuration.
                Used to initialize the LLM client and pass to each tool constructor.

        Registers all available tools (file_tool, terminal_tool, github_tool,
        code_gen, code_review, debugger) and sets up the LLM client for
        AI-powered tools. Logs registration count and LLM provider on success.
        """
        self.config = config
        self._tool_registry: Dict[str, Any] = {}
        self._llm_client: Optional[LLMClient] = None
        self._register_llm()
        self._register_tools()

    def _register_llm(self) -> None:
        """Initialize the LLM client for AI-powered tool operations.

        Creates an LLMClient instance using self.config.model and stores it in
        self._llm_client. If initialization fails, logs the error and leaves
        _llm_client as None — tools that require the LLM will fall back gracefully.
        """
        try:
            self._llm_client = LLMClient(self.config.model)
            logger.info("llm_client_ready", provider=self.config.model.provider)
        except Exception as e:
            logger.error("llm_init_failed", exc_info=e)

    def _register_tools(self) -> None:
        """Register all available tools in the tool registry.

        Imports and instantiates each tool (FileTool, TerminalTool, GitHubTool,
        CodeGenTool, CodeReviewTool, DebuggerTool), passing self.config and, for
        AI-powered tools, self._llm_client. Stores each tool in _tool_registry
        by name (e.g., 'file_tool', 'terminal_tool'). Logs the total count
        of registered tools. If a tool fails to initialize, logs the error
        and continues with remaining tools — partial registration is acceptable.
        """
        from beaver_agent.tools.file_tool import FileTool
        from beaver_agent.tools.terminal_tool import TerminalTool
        from beaver_agent.tools.github_tool import GitHubTool
        from beaver_agent.tools.code_gen import CodeGenTool
        from beaver_agent.tools.code_review import CodeReviewTool
        from beaver_agent.tools.debugger import DebuggerTool

        tool_entries = [
            ("file_tool", lambda: FileTool(self.config)),
            ("terminal_tool", lambda: TerminalTool(self.config)),
            ("github_tool", lambda: GitHubTool(self.config)),
            ("code_gen", lambda: CodeGenTool(self.config, self._llm_client)),
            ("code_review", lambda: CodeReviewTool(self.config, self._llm_client)),
            ("debugger", lambda: DebuggerTool(self.config, self._llm_client)),
        ]

        self._tool_registry = {}
        for name, factory in tool_entries:
            try:
                self._tool_registry[name] = factory()
            except Exception as e:
                logger.warning("tool_registration_failed", tool=name, exc_info=e)

        logger.info("tools_registered", count=len(self._tool_registry))

    # Error codes for programmatic error handling
    ERR_NO_TOOL = "ERR_NO_TOOL"
    ERR_UNKNOWN_TOOL = "ERR_UNKNOWN_TOOL"
    ERR_NO_ACTION = "ERR_NO_ACTION"
    ERR_TOOL_EXECUTION = "ERR_TOOL_EXECUTION"

    def route(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route a task to the appropriate tool.

        Takes a task dictionary with 'tool', 'action', and optional 'params' keys,
        looks up the tool in the registry, and executes the specified action
        with the given parameters.

        Args:
            task: Dictionary containing:
                - tool (str): Name of the tool to route to
                - action (str): Method name to call on the tool
                - params (dict, optional): Keyword arguments for the action method

        Returns:
            Dict with 'success' (bool) and either 'data' (result) or 'error' and
            'error_code' (string error identifier). On success, includes 'tool'
            and 'action' keys describing what was executed.
        """

        tool_name = task.get("tool")
        action = task.get("action")
        params = task.get("params", {})

        if not tool_name:
            return {"success": False, "error": "No tool specified", "error_code": self.ERR_NO_TOOL}

        if tool_name not in self._tool_registry:
            return {"success": False, "error": f"Unknown tool: {tool_name}", "error_code": self.ERR_UNKNOWN_TOOL}

        tool = self._tool_registry[tool_name]

        # Execute the action
        try:
            if hasattr(tool, action):
                result = getattr(tool, action)(**params)
                return {"success": True, "tool": tool_name, "action": action, "data": result}
            else:
                return {"success": False, "error": f"Tool {tool_name} has no action: {action}",
                        "error_code": self.ERR_NO_ACTION, "tool": tool_name, "action": action}
        except Exception as e:
            logger.error("tool_execution_failed", tool=tool_name, action=action, exc_info=e)
            return {"success": False, "error": str(e), "error_code": self.ERR_TOOL_EXECUTION,
                    "tool": tool_name, "action": action}

    def list_tools(self) -> list:
        """List all registered tool names.

        Returns:
            List of strings, each being the name of a registered tool.
        """
        return list(self._tool_registry.keys())

    def get_tool(self, name: str) -> Optional[Any]:
        """Get a specific tool by name.

        Args:
            name: The tool name to look up (e.g., 'file_tool', 'terminal_tool').

        Returns:
            The tool instance, or None if not found.
        """
        return self._tool_registry.get(name)

    def get_llm_client(self) -> Optional[LLMClient]:
        """Get the LLM client used for AI-powered tools.

        Returns:
            The LLMClient instance, or None if initialization failed.
        """
        return self._llm_client
