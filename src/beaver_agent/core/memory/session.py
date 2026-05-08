"""Beaver Agent Session Memory"""

from typing import List, Dict, Any, Optional
import time

import structlog

logger = structlog.get_logger()

__all__ = ["SessionMemory"]


class SessionMemory:
    """In-memory session storage for conversation context.

    Stores conversation history with automatic trimming when max_history is
    exceeded. Each message is timestamped and optionally tagged with metadata.

    Attributes:
        max_history: Maximum number of messages to retain.
        messages: List of message dicts with keys: role, content, timestamp.
        metadata: Dict with created_at and last_updated timestamps.
    """

    def __init__(self, max_history: int = 100):
        """Initialize session memory.

        Args:
            max_history: Maximum number of messages to store (default: 100).
                When exceeded, oldest messages are trimmed automatically.
        """
        self.max_history = max_history
        self.messages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {
            "created_at": time.time(),
            "last_updated": time.time(),
        }

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a message to session history.

        Args:
            role: Message role (e.g., "user", "assistant", "system").
            content: The message text content.
            metadata: Optional arbitrary metadata dict (e.g., {"tool": "file_tool"}).

        Example:
            >>> mem = SessionMemory()
            >>> mem.add_message("user", "Hello, world!")
            >>> mem.add_message("assistant", "Hi there!", metadata={"model": "gpt-4"})
        """
        message: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }
        if metadata:
            message["metadata"] = metadata

        self.messages.append(message)
        self.metadata["last_updated"] = time.time()
        logger.debug("session_message_added", role=role, message_count=len(self.messages))

        # Trim if exceeds max
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history :]

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history.

        Args:
            limit: If provided, return only the last N messages. If None,
                return the entire history (up to max_history).

        Returns:
            List of message dicts, each with keys: role, content, timestamp,
            and optionally metadata.

        Example:
            >>> mem = SessionMemory()
            >>> mem.add_message("user", "Hello")
            >>> history = mem.get_history(limit=10)  # last 10 messages
        """
        if limit:
            return self.messages[-limit:]
        return self.messages

    def clear(self) -> None:
        """Clear all messages from session memory.

        Resets messages to an empty list and updates last_updated timestamp.
        Metadata (created_at, last_updated) is preserved.

        Example:
            >>> mem = SessionMemory()
            >>> mem.add_message("user", "Hello")
            >>> mem.clear()
            >>> mem.get_history()
            []
        """
        self.messages.clear()
        self.metadata["last_updated"] = time.time()
        logger.debug("session_cleared")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search through session history by content keyword.

        Performs a case-insensitive substring match against message content.

        Args:
            query: The search string to look for in message content.

        Returns:
            List of all message dicts where content contains the query
            (case-insensitive). Empty list if no matches found.

        Example:
            >>> mem = SessionMemory()
            >>> mem.add_message("user", "How do I fix the bug?")
            >>> mem.add_message("assistant", "Have you tried restarting?")
            >>> results = mem.search("bug")
            >>> len(results)
            1
        """
        results = []
        query_lower = query.lower()
        for msg in self.messages:
            if query_lower in msg.get("content", "").lower():
                results.append(msg)
        return results

    def get_context(self, max_tokens: int = 4000) -> str:
        """Get a formatted context string for prompt injection.

        Concatenates the last 20 messages into a single string suitable
        for use as conversation context in LLM prompts. Each message
        is formatted as "role: content" on its own line.

        Note:
            The max_tokens parameter is accepted for API compatibility
            but the actual tokenization is performed by the caller.

        Args:
            max_tokens: Reserved parameter for API compatibility (default: 4000).
                The caller is responsible for token counting and truncation.

        Returns:
            A newline-separated string of "role: content" lines, covering
            the last 20 messages (or fewer if history is shorter).

        Example:
            >>> mem = SessionMemory()
            >>> mem.add_message("user", "Hello")
            >>> mem.add_message("assistant", "Hi!")
            >>> print(mem.get_context())
            user: Hello
            assistant: Hi!
        """
        lines = []
        for msg in self.messages[-20:]:  # Last 20 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")

        return "\n".join(lines)
