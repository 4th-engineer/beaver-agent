"""Component 2: Model Adapter — unified interface for different LLM providers."""

from abc import ABC, abstractmethod


class ModelAdapter(ABC):
    """Abstract adapter that all LLM providers must implement."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Send prompt to LLM and return generated text."""
        raise NotImplementedError

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this adapter supports streaming responses."""
        raise NotImplementedError


class BeaverAdapter(ModelAdapter):
    """Adapter that uses the existing BeaverAgent LLM client."""

    def __init__(self, llm_client):
        """Initialize the BeaverAdapter with a BeaverAgent LLM client.

        Args:
            llm_client: An instance of the BeaverAgent LLM client
                (e.g., LLMClient) used to generate text via the
                agent's configured model and provider.
        """
        self._client = llm_client

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using the BeaverAgent LLM client.

        Args:
            prompt: The input prompt to send to the LLM.
            **kwargs: Additional keyword arguments passed to the client.

        Returns:
            The generated text response from the LLM.
        """
        return self._client.generate(prompt)

    def supports_streaming(self) -> bool:
        """Return False since BeaverAdapter does not support streaming.

        Returns:
            False — streaming is not supported by this adapter.
        """
        return False


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI-compatible API endpoints."""

    def __init__(self, model: str = "gpt-4", api_key: str = "", base_url: str = ""):
        """Initialize the OpenAIAdapter.

        Args:
            model: The model name to use (default: "gpt-4").
            api_key: API key for authentication. If empty, the adapter
                will attempt to read from the OPENAI_API_KEY environment
                variable at generate() time.
            base_url: Base URL for the OpenAI-compatible API endpoint.
                If empty, defaults to the standard OpenAI API URL.
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using OpenAI-compatible API.

        Raises:
            NotImplementedError: OpenAI adapter is not yet implemented.
        """
        raise NotImplementedError("OpenAI adapter not yet implemented")

    def supports_streaming(self) -> bool:
        """Return True since OpenAI adapter supports streaming.

        Returns:
            True — streaming is supported by this adapter.
        """
        return True


class MiniMaxAdapter(ModelAdapter):
    """Adapter for MiniMax API."""

    def __init__(self, api_key: str, model: str = "MiniMax-M2.7"):
        """Initialize the MiniMaxAdapter.

        Args:
            api_key: The MiniMax API key for authentication.
            model: The model name to use (default: "MiniMax-M2.7").
        """
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using MiniMax API.

        Raises:
            NotImplementedError: MiniMax adapter is not yet implemented.
        """
        raise NotImplementedError("MiniMax adapter not yet implemented")

    def supports_streaming(self) -> bool:
        """Return False since MiniMax adapter does not support streaming.

        Returns:
            False — streaming is not supported by this adapter.
        """
        return False
