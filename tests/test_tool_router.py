"""Tests for ToolRouter — execute() error paths and tool registry."""

import pytest
from unittest.mock import MagicMock

from beaver_agent.core.tool_router import ToolRouter


class MockTool:
    """A simple mock tool for testing."""

    def healthy_action(self, **kwargs):
        return {"status": "ok"}

    def failing_action(self, **kwargs):
        raise RuntimeError("deliberate test failure")


@pytest.fixture
def router():
    """Create a ToolRouter with mock tools registered.

    We bypass __init__ to avoid needing a full BeaverConfig — execute()
    only reads _tool_registry, so we set it up directly.
    """
    r = ToolRouter.__new__(ToolRouter)
    r._tool_registry = {"mock_tool": MockTool()}
    r.ERR_NO_TOOL = "ERR_NO_TOOL"
    r.ERR_UNKNOWN_TOOL = "ERR_UNKNOWN_TOOL"
    r.ERR_NO_ACTION = "ERR_NO_ACTION"
    r.ERR_TOOL_EXECUTION = "ERR_TOOL_EXECUTION"
    return r


class TestToolRouterRouteErrors:
    """Tests for ToolRouter.route() error handling paths."""

    def test_route_no_tool_specified(self, router):
        """route() returns error when task has no 'tool' key."""
        result = router.route({})
        assert result["success"] is False
        assert result["error_code"] == "ERR_NO_TOOL"
        assert "No tool specified" in result["error"]

    def test_route_unknown_tool(self, router):
        """route() returns error when tool name is not registered."""
        result = router.route({"tool": "nonexistent_tool"})
        assert result["success"] is False
        assert result["error_code"] == "ERR_UNKNOWN_TOOL"
        assert "Unknown tool" in result["error"]

    def test_route_no_action(self, router):
        """route() returns error when tool has no requested action."""
        result = router.route({"tool": "mock_tool", "action": "nonexistent_action"})
        assert result["success"] is False
        assert result["error_code"] == "ERR_NO_ACTION"
        assert "nonexistent_action" in result["error"]

    def test_route_tool_raises_exception(self, router, caplog):
        """route() catches tool exception and returns error with exc_info logged."""
        result = router.route({
            "tool": "mock_tool",
            "action": "failing_action",
        })
        assert result["success"] is False
        assert result["error_code"] == "ERR_TOOL_EXECUTION"
        assert "deliberate test failure" in result["error"]

    def test_route_success(self, router):
        """route() returns success result when tool action succeeds."""
        result = router.route({
            "tool": "mock_tool",
            "action": "healthy_action",
        })
        assert result["success"] is True
        assert result["data"]["status"] == "ok"


class TestToolRouterRegistry:
    """Tests for ToolRouter tool registry access."""

    def test_list_tools(self, router):
        """list_tools() returns registered tool names."""
        tools = router.list_tools()
        assert "mock_tool" in tools

    def test_get_tool_existing(self, router):
        """get_tool() returns the tool instance if found."""
        tool = router.get_tool("mock_tool")
        assert tool is not None

    def test_get_tool_nonexistent(self, router):
        """get_tool() returns None for unknown tool name."""
        tool = router.get_tool("nonexistent")
        assert tool is None

    def test_get_llm_client_none_by_default(self, router):
        """get_llm_client() returns None when no LLM client was initialized."""
        # Router created via __new__ bypasses __init__, so _llm_client is unset
        assert router.get_llm_client() is None

    def test_get_llm_client_returns_client(self):
        """get_llm_client() returns the LLM client when it was initialized."""
        from unittest.mock import MagicMock
        from beaver_agent.core.tool_router import ToolRouter

        r = ToolRouter.__new__(ToolRouter)
        r._tool_registry = {}
        r._llm_client = MagicMock()  # Simulate initialized LLM client
        r.ERR_NO_TOOL = "ERR_NO_TOOL"
        r.ERR_UNKNOWN_TOOL = "ERR_UNKNOWN_TOOL"
        r.ERR_NO_ACTION = "ERR_NO_ACTION"
        r.ERR_TOOL_EXECUTION = "ERR_TOOL_EXECUTION"

        client = r.get_llm_client()
        assert client is not None
        assert client is r._llm_client
