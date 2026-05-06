"""Tests for ToolRouter LLM client integration."""

import pytest
from unittest.mock import MagicMock, patch

from beaver_agent.core.tool_router import ToolRouter


class TestToolRouterGetLLMClient:
    """Tests for ToolRouter.get_llm_client()."""

    def test_get_llm_client_returns_client_when_initialized(self):
        """get_llm_client() returns the LLM client after successful init."""
        mock_config = MagicMock()
        mock_config.model.provider = "test-provider"
        mock_config.model.name = "test-model"

        router = ToolRouter(mock_config)
        # LLMClient is mocked via patch in the actual init
        client = router.get_llm_client()
        # After successful init, client should be set
        assert client is not None

    def test_get_llm_client_returns_none_when_init_failed(self):
        """get_llm_client() returns None when LLM initialization failed."""
        mock_config = MagicMock()
        mock_config.model.provider = "test-provider"
        mock_config.model.name = "test-model"

        with patch("beaver_agent.core.tool_router.LLMClient") as mock_client_class:
            mock_client_class.side_effect = RuntimeError("LLM init failed")
            router = ToolRouter(mock_config)
            assert router.get_llm_client() is None

    def test_get_llm_client_returns_none_when_no_llm_in_router(self):
        """get_llm_client() returns None if _llm_client was never set."""
        router = ToolRouter.__new__(ToolRouter)
        router._llm_client = None
        router._tool_registry = {}
        assert router.get_llm_client() is None
