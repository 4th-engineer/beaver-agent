"""Beaver Agent LLM Client - Unified interface for OpenRouter/Claude/OpenAI"""

import os
from typing import Optional, List, Dict, Any, Union

import structlog

from beaver_agent.core.config import ModelConfig

logger = structlog.get_logger()


class LLMResponse:
    """LLM response wrapper.

    Encapsulates the response from an LLM API call, including the generated
    content, the model used, and optional token usage statistics.

    Attributes:
        content: The generated text content from the LLM.
        model: The model name that generated the response.
        usage: Optional dictionary of token usage metrics (prompt_tokens,
            completion_tokens, total_tokens). Empty dict if usage info unavailable.
    """

    def __init__(self, content: str, model: str, usage: Optional[Dict] = None):
        self.content = content
        self.model = model
        self.usage = usage or {}


class LLMClient:
    """Unified LLM client supporting OpenRouter, Anthropic, OpenAI"""

    def __init__(self, config: ModelConfig):
        """Initialize the LLM client with model configuration.

        Args:
            config: ModelConfig containing provider, model name, api key, and api base.
                api_key falls back to ANTHROPIC_API_KEY or OPENAI_API_KEY environment variables.

        Note:
            Provider is auto-detected from config.provider (openrouter/anthropic/openai).
            Client instance (_client) is created lazily via _init_client().
        """
        self.config = config
        self.provider = config.provider
        self.model = config.name
        self.api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.api_base = config.api_base

        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the appropriate client based on provider"""
        try:
            if self.provider == "anthropic" or "claude" in self.model.lower():
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
                self._call = self._call_anthropic
            elif self.provider == "openai" or "gpt" in self.model.lower():
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
                self._call = self._call_openai
            elif self.provider == "openrouter":
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.openrouter.ai/api/v1"
                )
                self._call = self._call_openai
            elif self.provider == "minimax":
                self._call = self._call_minimax
            else:
                # Default to OpenRouter
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.openrouter.ai/api/v1"
                )
                self._call = self._call_openai

            logger.info("llm_client_initialized", provider=self.provider, model=self.model)

        except ImportError as e:
            logger.error("llm_client_import_failed", exc_info=e)
            self._call = self._call_fallback

    def _call_anthropic(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """Call Anthropic Claude API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Additional arguments:
                - max_tokens (int): Maximum tokens to generate (default: 4096)
                - temperature (float): Sampling temperature (default: 0.7)

        Returns:
            LLMResponse with Claude's reply text, model name, and token usage.

        Raises:
            Exception: Propagates API errors for caller to handle.
        """
        response = self._client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            messages=messages
        )
        return LLMResponse(
            content=response.content[0].text,
            model=self.model,
            usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
        )

    def _call_openai(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """Call OpenAI / OpenRouter API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Additional arguments:
                - max_tokens (int): Maximum tokens to generate (default: 4096)
                - temperature (float): Sampling temperature (default: 0.7)

        Returns:
            LLMResponse with model's reply text, model name, and token usage.

        Raises:
            Exception: Propagates API errors for caller to handle.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            messages=messages
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            usage={"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens}
        )

    def _call_minimax(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """Call MiniMax API (Anthropic-compatible /messages endpoint)"""
        base_url = self.api_base or "https://api.minimaxi.com/anthropic/v1/messages"

        import httpx

        try:
            with httpx.Client(base_url=base_url.rstrip("/"), timeout=60.0, follow_redirects=True) as client:
                response = client.post(
                    "",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": kwargs.get("max_tokens", 4096),
                        "temperature": kwargs.get("temperature", 0.7),
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                content = data.get("content", [])
                if isinstance(content, list) and len(content) > 0:
                    text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    text = "\n".join(text_parts) if text_parts else str(content)
                else:
                    text = str(content)

                return LLMResponse(
                    content=text,
                    model=self.model,
                    usage={
                        "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                        "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                    },
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Authentication error - let it propagate so fallback kicks in
                logger.warning("minimax_auth_failed", status_code=401)
                raise
            logger.error("minimax_http_error", status_code=e.response.status_code, detail=str(e), exc_info=e)
            return LLMResponse(
                content=f"HTTP error {e.response.status_code}: {e.response.text}",
                model=self.model
            )
        except httpx.RequestError as e:
            logger.error("minimax_request_error", exc_info=e)
            return LLMResponse(
                content=f"Request error: {e}",
                model=self.model
            )
        except Exception as e:
            logger.error("minimax_unknown_error", exc_info=e)
            return LLMResponse(
                content=f"Unexpected error: {e}",
                model=self.model
            )

    def _call_fallback(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """Fallback when no API key is available"""
        return LLMResponse(
            content="LLM API key not configured. Please set OPENROUTER_API_KEY or ANTHROPIC_API_KEY",
            model="none"
        )

    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        context: Optional[List[Dict]] = None,
        **kwargs
    ) -> LLMResponse:
        """Simple chat interface for direct LLM communication.

        Args:
            prompt: The user's message text.
            system: Optional system prompt to set the assistant's behavior.
            context: Optional list of message dicts representing prior
                conversation history for multi-turn dialogue. Each dict
                should have 'role' and 'content' keys.
            **kwargs: Additional arguments passed to the underlying
                provider call (e.g., max_tokens, temperature).

        Returns:
            LLMResponse containing the assistant's reply text, model name,
            and token usage statistics.

        Example:
            >>> client = LLMClient(config)
            >>> response = client.chat("What is 2+2?", temperature=0.5)
            >>> print(response.content)
        """

        messages = []

        # Add system prompt
        if system:
            messages.append({"role": "system", "content": system})

        # Add conversation context
        if context:
            for msg in context:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        # Add user prompt
        messages.append({"role": "user", "content": prompt})

        return self._call(messages, **kwargs)

    def generate_code(
        self,
        description: str,
        language: str = "python",
        context: Optional[str] = None
    ) -> LLMResponse:
        """Generate code from a natural language description.

        Args:
            description: A plain-text description of the code to generate.
            language: The target programming language (default: "python").
                Common values: "python", "javascript", "go", "rust", "java".
            context: Optional existing code or file content to use as
                context for more accurate generation.

        Returns:
            LLMResponse containing the generated code (wrapped in markdown
            triple backticks), the model name, and token usage.
        """

        system = f"""You are Beaver Agent, an expert coding assistant.
Generate clean, well-documented code based on the user's request.
Always wrap code blocks with triple backticks and specify the language.
If you need more context, ask clarifying questions."""

        prompt = f"Write {language} code for the following:\n\n{description}"

        if context:
            prompt = f"Context:\n{context}\n\n---\n\n{prompt}"

        return self.chat(prompt, system=system)

    def review_code(
        self,
        code: str,
        language: str = "python",
        file_path: Optional[str] = None
    ) -> LLMResponse:
        """Review code and provide improvement suggestions.

        Args:
            code: The source code to review.
            language: The programming language of the code (default: "python").
            file_path: Optional file path included in the prompt to give
                the LLM context about where this code lives.

        Returns:
            LLMResponse containing a formatted code review with sections
            for bugs, quality issues, security concerns, and performance
            suggestions, along with the model name and token usage.
        """

        system = """You are Beaver Agent, an expert code reviewer.
Analyze the code and provide:
1. Potential bugs or issues
2. Code quality improvements
3. Security concerns
4. Performance optimizations

Format your review with clear sections and line numbers if provided."""

        file_info = f"\n\nFile: {file_path}" if file_path else ""
        prompt = f"Review the following {language} code:{file_info}\n\n```{language}\n{code}\n```"

        return self.chat(prompt, system=system)

    def debug_code(
        self,
        code: str,
        error: str,
        language: str = "python"
    ) -> LLMResponse:
        """Debug code that produced an error.

        Args:
            code: The source code that triggered an error.
            error: The error message or traceback to analyze.
            language: The programming language of the code (default: "python").

        Returns:
            LLMResponse containing root cause analysis, the exact fix,
            and prevention tips, plus corrected code when applicable,
            along with the model name and token usage.
        """

        system = """You are Beaver Agent, an expert debugging assistant.
Analyze the error and provide:
1. Root cause analysis
2. The exact fix
3. Prevention tips

Always provide the corrected code if applicable."""

        prompt = f"""Debug the following {language} code that produced this error:

Error:
```
{error}
```

Code:
```{language}
{code}
```"""

        return self.chat(prompt, system=system)

    def explain_code(self, code: str, language: str = "python") -> LLMResponse:
        """Explain what code does in plain language.

        Args:
            code: The source code to explain.
            language: The programming language of the code (default: "python").

        Returns:
            LLMResponse containing a clear explanation of the code's
            functionality, breaking down complex parts and providing
            examples where helpful, plus the model name and token usage.
        """

        system = """You are Beaver Agent, an expert programming tutor.
Explain code clearly, breaking down complex parts.
Use simple language and provide examples where helpful."""

        prompt = f"Explain the following {language} code:\n\n```{language}\n{code}\n```"

        return self.chat(prompt, system=system)
