"""Beaver Agent Tool Router - LLM-integrated tool dispatch."""

from typing import Any

import structlog

from beaver_agent.core.config import BeaverConfig
from beaver_agent.core.llm_client import LLMClient

logger = structlog.get_logger()

__all__ = ["ToolRouter"]


class ToolRouter:
    """Route tasks to appropriate tools.

    Maintains a registry of available tools (file_tool, terminal_tool,
    github_tool, code_gen, code_review, debugger) and dispatches incoming
    task requests to the correct tool/action pair. Supports graceful
    degradation when the LLM client is unavailable.

    The routing loop: route() validates the tool/action exists, calls it
    via getattr, and wraps the result in a success/error dict. All tool
    execution errors are caught and returned as structured error responses
    rather than raised, so callers always get a deterministic return value.

    Attributes:
        config: The BeaverConfig used to initialize tools and the LLM client.
        ERR_NO_TOOL: Error code when no tool name is provided.
        ERR_UNKNOWN_TOOL: Error code when the tool name is not in the registry.
        ERR_NO_ACTION: Error code when the tool has no matching action method.
        ERR_TOOL_EXECUTION: Error code when tool.action() raises an exception.

    Example:
        router = ToolRouter(config)
        result = router.route({"tool": "file_tool", "action": "read", "params": {"path": "README.md"}})
        if result["success"]:
            logger.info("tool_result", tool=result.get("tool"), action=result.get("action"), data=result["data"])
    """

    def __init__(self, config: BeaverConfig) -> None:
        """Initialize the ToolRouter with configuration and register all tools and LLM.

        Args:
            config: BeaverConfig instance containing model and tool configuration.
                Used to initialize the LLM client and pass to each tool constructor.

        Registers all available tools (file_tool, terminal_tool, github_tool,
        code_gen, code_review, debugger) and sets up the LLM client for
        AI-powered tools. Logs registration count and LLM provider on success.
        """
        self.config = config
        self._tool_registry: dict[str, Any] = {}
        self._llm_client: LLMClient | None = None
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
            logger.warning("llm_init_failed", exc_info=e)

    def _register_tools(self) -> None:
        """Register all available tools in the tool registry.

        Imports and instantiates each tool (FileTool, TerminalTool, GitHubTool,
        CodeGenTool, CodeReviewTool, DebuggerTool), passing self.config and, for
        AI-powered tools, self._llm_client. Stores each tool in _tool_registry
        by name (e.g., 'file_tool', 'terminal_tool'). Logs the total count
        of registered tools. If a tool fails to initialize, logs the error
        and continues with remaining tools — partial registration is acceptable.
        """
        from beaver_agent.tools.code_gen import CodeGenTool
        from beaver_agent.tools.code_review import CodeReviewTool
        from beaver_agent.tools.debugger import DebuggerTool
        from beaver_agent.tools.file_tool import FileTool
        from beaver_agent.tools.github_tool import GitHubTool
        from beaver_agent.tools.terminal_tool import TerminalTool

        self._tool_registry = {}
        for name, tool_cls, args in [
            ("file_tool", FileTool, [self.config]),
            ("terminal_tool", TerminalTool, [self.config]),
            ("github_tool", GitHubTool, [self.config]),
            ("code_gen", CodeGenTool, [self.config, self._llm_client]),
            ("code_review", CodeReviewTool, [self.config, self._llm_client]),
            ("debugger", DebuggerTool, [self.config, self._llm_client]),
        ]:
            try:
                self._tool_registry[name] = tool_cls(*args)
            except Exception as e:
                logger.warning("tool_registration_failed", tool=name, exc_info=e)

        logger.info("tools_registered", count=len(self._tool_registry))

    # Error codes for programmatic error handling
    ERR_NO_TOOL = "ERR_NO_TOOL"
    ERR_UNKNOWN_TOOL = "ERR_UNKNOWN_TOOL"
    ERR_NO_ACTION = "ERR_NO_ACTION"
    ERR_TOOL_EXECUTION = "ERR_TOOL_EXECUTION"

    def route(self, task: dict[str, Any]) -> dict[str, Any]:
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
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "error_code": self.ERR_UNKNOWN_TOOL,
            }

        tool = self._tool_registry[tool_name]

        # Execute the action
        try:
            if hasattr(tool, action):
                result = getattr(tool, action)(**params)
                return {"success": True, "tool": tool_name, "action": action, "data": result}
            else:
                return {
                    "success": False,
                    "error": f"Tool {tool_name} has no action: {action}",
                    "error_code": self.ERR_NO_ACTION,
                    "tool": tool_name,
                    "action": action,
                }
        except Exception as e:
            logger.error("tool_execution_failed", tool=tool_name, action=action, exc_info=e)
            return {
                "success": False,
                "error": str(e),
                "error_code": self.ERR_TOOL_EXECUTION,
                "tool": tool_name,
                "action": action,
            }

    def list_tools(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of strings, each being the name of a registered tool.
        """
        return list(self._tool_registry.keys())

    def get_tool(self, name: str) -> Any | None:
        """Get a specific tool by name.

        Args:
            name: The tool name to look up (e.g., 'file_tool', 'terminal_tool').

        Returns:
            The tool instance, or None if not found.
        """
        return self._tool_registry.get(name)

    def get_llm_client(self) -> LLMClient | None:
        """Get the LLM client used for AI-powered tools.

        Returns:
            The LLMClient instance, or None if initialization failed or
            the client was never initialized.
        """
        return getattr(self, "_llm_client", None)
