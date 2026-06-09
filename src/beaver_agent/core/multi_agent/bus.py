"""Event-bus for agent-to-agent messages (in-process pub/sub)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import structlog

logger = structlog.get_logger()


class EventBus:
    """Lightweight in-process publish/subscribe bus.

    Agents register callbacks for specific event types; when ``publish`` is
    called all matching callbacks run synchronously in the calling thread.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Register a handler for ``event_type``."""
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("bus_subscribe", event_type=event_type, handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Remove a previously registered handler."""
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h != handler
                ]

    def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Synchronously invoke all handlers registered for ``event_type``."""
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))
        for handler in handlers:
            try:
                handler(data)
            except Exception as exc:
                logger.error("bus_handler_error", event_type=event_type, exc=exc)
