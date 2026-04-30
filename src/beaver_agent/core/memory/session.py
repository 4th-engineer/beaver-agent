"""Beaver Agent Session Memory"""

from typing import List, Dict, Any, Optional
import time


class SessionMemory:
    """In-memory session storage for conversation context"""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.messages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {
            "created_at": time.time(),
            "last_updated": time.time(),
        }

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a message to session history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }
        if metadata:
            message["metadata"] = metadata

        self.messages.append(message)
        self.metadata["last_updated"] = time.time()

        # Trim if exceeds max
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history"""
        if limit:
            return self.messages[-limit:]
        return self.messages

    def clear(self) -> None:
        """Clear session memory"""
        self.messages.clear()
        self.metadata["last_updated"] = time.time()

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search through session history"""
        results = []
        query_lower = query.lower()
        for msg in self.messages:
            if query_lower in msg.get("content", "").lower():
                results.append(msg)
        return results

    def get_context(self, max_tokens: int = 4000) -> str:
        """Get formatted context string"""
        lines = []
        for msg in self.messages[-20:]:  # Last 20 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")

        return "\n".join(lines)
