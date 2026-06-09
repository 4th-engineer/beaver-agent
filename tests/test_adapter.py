"""Tests for ModelAdapter implementations."""

from unittest.mock import MagicMock

import pytest

from beaver_agent.core.eval.adapter import (
    BeaverAdapter,
    MiniMaxAdapter,
    ModelAdapter,
    OpenAIAdapter,
)


class TestModelAdapter:
    """Tests for abstract ModelAdapter class."""

    def test_is_abc(self):
        """ModelAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ModelAdapter()


class TestBeaverAdapter:
    """Tests for BeaverAdapter."""

    def test_init(self):
        """BeaverAdapter initializes with llm_client."""
        mock_client = MagicMock()
        adapter = BeaverAdapter(mock_client)
        assert adapter._client is mock_client

    def test_generate_delegates_to_client(self):
        """generate() calls the LLM client with the prompt."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "generated text"
        adapter = BeaverAdapter(mock_client)

        result = adapter.generate("test prompt")

        mock_client.generate.assert_called_once_with("test prompt")
        assert result == "generated text"

    def test_generate_passes_kwargs(self):
        """generate() passes kwargs to the LLM client."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "result"
        adapter = BeaverAdapter(mock_client)

        adapter.generate("prompt", temperature=0.7, max_tokens=100)

        mock_client.generate.assert_called_once_with("prompt", temperature=0.7, max_tokens=100)

    def test_supports_streaming_false(self):
        """BeaverAdapter does not support streaming."""
        adapter = BeaverAdapter(MagicMock())
        assert adapter.supports_streaming() is False


class TestOpenAIAdapter:
    """Tests for OpenAIAdapter."""

    def test_init_defaults(self):
        """OpenAIAdapter initializes with defaults."""
        adapter = OpenAIAdapter()
        assert adapter.model == "gpt-4"
        assert adapter.api_key == ""
        assert adapter.base_url == ""

    def test_init_with_params(self):
        """OpenAIAdapter initializes with custom parameters."""
        adapter = OpenAIAdapter(
            model="gpt-4o", api_key="sk-test", base_url="https://api.example.com"
        )
        assert adapter.model == "gpt-4o"
        assert adapter.api_key == "sk-test"
        assert adapter.base_url == "https://api.example.com"

    def test_generate_raises_not_implemented(self):
        """generate() raises NotImplementedError."""
        adapter = OpenAIAdapter(api_key="sk-test")
        with pytest.raises(NotImplementedError, match="OpenAI adapter not yet implemented"):
            adapter.generate("test prompt")

    def test_supports_streaming_true(self):
        """OpenAIAdapter supports streaming."""
        adapter = OpenAIAdapter()
        assert adapter.supports_streaming() is True


class TestMiniMaxAdapter:
    """Tests for MiniMaxAdapter."""

    def test_init_defaults(self):
        """MiniMaxAdapter initializes with defaults."""
        adapter = MiniMaxAdapter(api_key="test-key")
        assert adapter.api_key == "test-key"
        assert adapter.model == "MiniMax-M2.7"

    def test_init_with_params(self):
        """MiniMaxAdapter initializes with custom parameters."""
        adapter = MiniMaxAdapter(api_key="my-key", model="custom-model")
        assert adapter.api_key == "my-key"
        assert adapter.model == "custom-model"

    def test_generate_raises_not_implemented(self):
        """generate() raises NotImplementedError."""
        adapter = MiniMaxAdapter(api_key="test-key")
        with pytest.raises(NotImplementedError, match="MiniMax adapter not yet implemented"):
            adapter.generate("test prompt")

    def test_supports_streaming_false(self):
        """MiniMaxAdapter does not support streaming."""
        adapter = MiniMaxAdapter(api_key="test-key")
        assert adapter.supports_streaming() is False
