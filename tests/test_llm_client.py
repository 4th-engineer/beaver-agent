"""Tests for LLMClient and LLMResponse."""

from unittest.mock import MagicMock, patch

from beaver_agent.core.llm_client import LLMClient, LLMResponse


class TestLLMResponse:
    """Tests for LLMResponse data class."""

    def test_init_with_content_model(self):
        """LLMResponse stores content and model."""
        response = LLMResponse(content="Hello", model="claude-3")
        assert response.content == "Hello"
        assert response.model == "claude-3"
        assert response.usage == {}

    def test_init_with_usage(self):
        """LLMResponse stores usage dict."""
        usage = {"input_tokens": 100, "output_tokens": 50}
        response = LLMResponse(content="Hi", model="gpt-4", usage=usage)
        assert response.usage == usage

    def test_init_defaults_to_empty_usage(self):
        """LLMResponse defaults usage to empty dict if not provided."""
        response = LLMResponse(content="Hi", model="gpt-4")
        assert response.usage == {}

    def test_usage_none_becomes_empty_dict(self):
        """LLMResponse converts None usage to empty dict."""
        response = LLMResponse(content="Hi", model="gpt-4", usage=None)
        assert response.usage == {}


class TestLLMClientFallback:
    """Tests for LLMClient._call_fallback (no external dependencies)."""

    def test_fallback_returns_no_api_key_message(self):
        """_call_fallback returns message about missing API key."""
        client = LLMClient.__new__(LLMClient)  # Bypass __init__
        client._call = client._call_fallback
        client.model = "none"

        response = client._call([])
        assert "not configured" in response.content
        assert "OPENROUTER_API_KEY" in response.content or "ANTHROPIC_API_KEY" in response.content
        assert response.model == "none"

    def test_chat_uses_fallback_when_no_client(self):
        """chat() uses _call_fallback when no LLM is available."""
        client = LLMClient.__new__(LLMClient)
        client._call = client._call_fallback
        client.model = "none"

        response = client.chat("Hello")
        assert "not configured" in response.content

    def test_generate_code_uses_fallback(self):
        """generate_code() returns fallback message without API key."""
        client = LLMClient.__new__(LLMClient)
        client._call = client._call_fallback
        client.model = "none"

        response = client.generate_code("Write a function")
        assert "not configured" in response.content

    def test_review_code_uses_fallback(self):
        """review_code() returns fallback message without API key."""
        client = LLMClient.__new__(LLMClient)
        client._call = client._call_fallback
        client.model = "none"

        response = client.review_code("def foo(): pass")
        assert "not configured" in response.content

    def test_debug_code_uses_fallback(self):
        """debug_code() returns fallback message without API key."""
        client = LLMClient.__new__(LLMClient)
        client._call = client._call_fallback
        client.model = "none"

        response = client.debug_code("def foo(): pass", "error message")
        assert "not configured" in response.content

    def test_explain_code_uses_fallback(self):
        """explain_code() returns fallback message without API key."""
        client = LLMClient.__new__(LLMClient)
        client._call = client._call_fallback
        client.model = "none"

        response = client.explain_code("def foo(): pass")
        assert "not configured" in response.content


class TestLLMClientInit:
    """Tests for LLMClient initialization and provider routing."""

    def test_init_minimax_provider(self):
        """LLMClient with minimax provider sets _call_minimax."""

        config = MagicMock()
        config.provider = "minimax"
        config.name = "MiniMax-M2"
        config.api_key = "test-key"
        config.api_base = None

        client = LLMClient(config)
        assert client.provider == "minimax"
        assert client.model == "MiniMax-M2"
        assert client.api_key == "test-key"

    def test_init_openrouter_provider(self):
        """LLMClient with openrouter provider sets _call_openai."""

        config = MagicMock()
        config.provider = "openrouter"
        config.name = "anthropic/claude-3"
        config.api_key = "test-key"
        config.api_base = None

        with patch("openai.OpenAI"):
            client = LLMClient(config)
            assert client.provider == "openrouter"

    def test_api_key_falls_back_to_env_var(self):
        """LLMClient uses ANTHROPIC_API_KEY when config.api_key is None."""

        config = MagicMock()
        config.provider = "anthropic"
        config.name = "claude-3"
        config.api_key = None
        config.api_base = None

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env-key"}):
            with patch("anthropic.Anthropic"):
                client = LLMClient(config)
                assert client.api_key == "env-key"

    def test_api_key_falls_back_to_openai_env(self):
        """LLMClient uses OPENAI_API_KEY when ANTHROPIC_API_KEY is not set."""

        config = MagicMock()
        config.provider = "openai"
        config.name = "gpt-4"
        config.api_key = None
        config.api_base = None

        with patch.dict("os.environ", {"OPENAI_API_KEY": "openai-key"}, clear=False):
            with patch("openai.OpenAI"):
                client = LLMClient(config)
                assert client.api_key == "openai-key"


class TestLLMClientChat:
    """Tests for LLMClient.chat() method."""

    def test_chat_builds_messages_with_system_prompt(self):
        """chat() includes system prompt in messages."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("Hi", "none"))
        client._call = mock_call
        client.model = "none"

        response = client.chat("Hello", system="You are helpful")

        call_args = mock_call.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["role"] == "system"
        assert call_args[0]["content"] == "You are helpful"
        assert call_args[1]["role"] == "user"
        assert call_args[1]["content"] == "Hello"

    def test_chat_builds_messages_with_context(self):
        """chat() includes conversation context."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("Hi", "none"))
        client._call = mock_call
        client.model = "none"

        context = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
        ]
        response = client.chat("Hello", context=context)

        call_args = mock_call.call_args[0][0]
        assert len(call_args) == 3
        assert call_args[0]["role"] == "user"
        assert call_args[0]["content"] == "Previous message"
        assert call_args[1]["role"] == "assistant"
        assert call_args[1]["content"] == "Previous response"
        assert call_args[2]["role"] == "user"
        assert call_args[2]["content"] == "Hello"

    def test_chat_passes_kwargs_to_call(self):
        """chat() passes max_tokens and temperature to _call."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("Hi", "none"))
        client._call = mock_call
        client.model = "none"

        client.chat("Hello", max_tokens=100, temperature=0.5)

        mock_call.assert_called_once()
        kwargs = mock_call.call_args[1]
        assert kwargs.get("max_tokens") == 100
        assert kwargs.get("temperature") == 0.5


class TestLLMClientGenerateCode:
    """Tests for LLMClient.generate_code() method."""

    def test_generate_code_uses_correct_system_prompt(self):
        """generate_code() sends appropriate system prompt."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("def main(): pass", "none"))
        client._call = mock_call
        client.model = "none"

        client.generate_code("Write a main function", language="python")

        call_args = mock_call.call_args[0][0]
        system_msg = call_args[0]
        assert system_msg["role"] == "system"
        assert "Beaver Agent" in system_msg["content"]
        assert "code" in system_msg["content"].lower()

    def test_generate_code_includes_language_in_prompt(self):
        """generate_code() specifies language in prompt."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("function test() {}", "none"))
        client._call = mock_call
        client.model = "none"

        client.generate_code("Write a test", language="javascript")

        call_args = mock_call.call_args[0][0]
        user_msg = call_args[-1]
        assert "javascript" in user_msg["content"].lower()

    def test_generate_code_includes_context_when_provided(self):
        """generate_code() includes existing code as context."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("completed code", "none"))
        client._call = mock_call
        client.model = "none"

        existing = "def foo():\n    pass"
        client.generate_code("Complete this", language="python", context=existing)

        call_args = mock_call.call_args[0][0]
        user_msg = call_args[-1]
        assert "Context" in user_msg["content"]
        assert existing in user_msg["content"]


class TestLLMClientReviewCode:
    """Tests for LLMClient.review_code() method."""

    def test_review_code_includes_language(self):
        """review_code() specifies language in prompt."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("Review complete", "none"))
        client._call = mock_call
        client.model = "none"

        client.review_code("def foo(): pass", language="python")

        call_args = mock_call.call_args[0][0]
        user_msg = call_args[-1]
        assert "python" in user_msg["content"].lower()

    def test_review_code_includes_file_path_when_provided(self):
        """review_code() includes file path in prompt when given."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("Review complete", "none"))
        client._call = mock_call
        client.model = "none"

        client.review_code("code", file_path="src/main.py")

        call_args = mock_call.call_args[0][0]
        user_msg = call_args[-1]
        assert "src/main.py" in user_msg["content"]


class TestLLMClientDebugCode:
    """Tests for LLMClient.debug_code() method."""

    def test_debug_code_includes_error(self):
        """debug_code() includes error message in prompt."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("Fix applied", "none"))
        client._call = mock_call
        client.model = "none"

        client.debug_code("code", error="TypeError: undefined")

        call_args = mock_call.call_args[0][0]
        user_msg = call_args[-1]
        assert "TypeError" in user_msg["content"]
        assert "code" in user_msg["content"].lower()

    def test_debug_code_includes_language(self):
        """debug_code() includes language in prompt."""
        client = LLMClient.__new__(LLMClient)
        mock_call = MagicMock(return_value=LLMResponse("Fix applied", "none"))
        client._call = mock_call
        client.model = "none"

        client.debug_code("code", error="Error", language="javascript")

        call_args = mock_call.call_args[0][0]
        user_msg = call_args[-1]
        assert "javascript" in user_msg["content"].lower()
