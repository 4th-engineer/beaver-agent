"""Beaver Agent Conversation Logger - Records user input and LLM interactions"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from threading import RLock

import structlog

logger = structlog.get_logger()

__all__ = ["ConversationLogger"]


class ConversationLogger:
    """Thread-safe conversation logger for debugging and analysis"""

    def __init__(self, log_dir: str = None) -> None:
        """Initialize the conversation logger.

        Args:
            log_dir: Optional directory path for storing log files.
                Defaults to ``logs/`` in the project root.
        """
        if log_dir is None:
            # Default to logs/ in project root
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._lock = RLock()
        self._session_file: Optional[Path] = None
        self._session_id: Optional[str] = None

    def start_session(self, session_id: str) -> None:
        """Start a new logging session.

        Args:
            session_id: Unique identifier for this session (e.g., short UUID).
                Used to name the log file and correlate log entries.
        """
        with self._lock:
            self._session_id = session_id
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._session_file = self.log_dir / f"conversation_{timestamp}_{session_id}.jsonl"

            # Write session start marker
            self._write_entry(
                {
                    "type": "session_start",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        logger.info(
            "conversation_logger_started", session_id=session_id, log_file=str(self._session_file)
        )

    def log_user_input(self, user_input: str, intent: str = None) -> None:
        """Log a user message to the current session.

        Args:
            user_input: The raw text input from the user. Content exceeding
                2000 characters is automatically truncated before writing.
            intent: Optional parsed intent string (e.g., from IntentParser).
                Defaults to None if intent was not determined.
        """
        # Truncate very long input for logging
        if len(user_input) > 2000:
            user_input = user_input[:2000] + "... [truncated]"

        self._write_entry(
            {
                "type": "user_input",
                "timestamp": datetime.now().isoformat(),
                "intent": intent,
                "content": user_input,
            }
        )

    def log_llm_request(self, messages: List[Dict[str, Any]], model: str, provider: str) -> None:
        """Log an LLM API request to the current session.

        Args:
            messages: List of message dicts sent to the LLM API, typically
                containing 'role' and 'content' keys.
            model: Model name used for the request (e.g., 'MiniMax-M2.7').
            provider: Provider name (e.g., 'minimax', 'openai').
                Content in messages exceeding 2000 characters is
                automatically truncated before writing.
        """
        # Truncate very long content for logging
        truncated_messages = []
        for msg in messages:
            truncated_msg = dict(msg)
            if (
                isinstance(truncated_msg.get("content"), str)
                and len(truncated_msg["content"]) > 2000
            ):
                truncated_msg["content"] = truncated_msg["content"][:2000] + "... [truncated]"
            truncated_messages.append(truncated_msg)

        self._write_entry(
            {
                "type": "llm_request",
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "provider": provider,
                "messages": truncated_messages,
            }
        )

    def log_llm_response(
        self, content: str, model: str, usage: Dict = None, error: str = None
    ) -> None:
        """Log an LLM API response to the current session.

        Args:
            content: The generated text response from the LLM. Content
                exceeding 5000 characters is automatically truncated.
            model: Model name that generated the response.
            usage: Optional dict of token usage statistics (e.g.,
                {'prompt_tokens': N, 'completion_tokens': M}).
            error: Optional error message string if the request failed.
                When provided, 'content' may be empty or partial.
        """
        # Truncate very long content
        if len(content) > 5000:
            content = content[:5000] + "... [truncated]"

        entry = {
            "type": "llm_response",
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "content": content,
        }

        if usage:
            entry["usage"] = usage
        if error:
            entry["error"] = error

        self._write_entry(entry)

    def log_tool_call(
        self,
        tool_name: str,
        action: str,
        params: Dict = None,
        result: Any = None,
        success: bool = True,
        error: str = None,
    ) -> None:
        """Log a tool invocation to the current session.

        Args:
            tool_name: Name of the tool that was invoked (e.g., 'file_tool').
            action: Name of the method called on the tool (e.g., 'read_file').
            params: Optional dict of keyword arguments passed to the action.
                If the serialized params exceed 1000 characters, only the first
                1000 are stored with a truncation marker.
            result: Optional result returned by the tool. If the serialized
                result exceeds 2000 characters, only the first 2000 are stored
                with a truncation marker.
            success: Whether the tool call succeeded (default True). Used to
                distinguish between successful executions and errors.
            error: Optional error message string if the tool call failed.
                When provided, 'success' should be False.
        """
        entry = {
            "type": "tool_call",
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "action": action,
            "success": success,
        }

        if params:
            # Truncate params for logging
            if isinstance(params, dict):
                str_params = json.dumps(params, ensure_ascii=False)
                if len(str_params) > 1000:
                    params = {"_truncated": str_params[:1000] + "... [truncated]"}
            entry["params"] = params

        if result:
            str_result = json.dumps(result, ensure_ascii=False, default=str)
            if len(str_result) > 2000:
                result = str_result[:2000] + "... [truncated]"
            entry["result"] = result

        if error:
            entry["error"] = error

        self._write_entry(entry)

    def log_skill_invocation(self, skill_name: str, trigger: str, matched: bool = True) -> None:
        """Log a skill invocation attempt.

        Args:
            skill_name: Name of the skill that was invoked.
            trigger: The user input or pattern that triggered the skill.
            matched: Whether the skill was successfully matched and invoked.
                False indicates a near-miss where intent was detected but
                skill execution was not attempted.
        """
        self._write_entry(
            {
                "type": "skill_invocation",
                "timestamp": datetime.now().isoformat(),
                "skill": skill_name,
                "trigger": trigger,
                "matched": matched,
            }
        )

    def end_session(self) -> None:
        """End the current logging session.

        Writes a session_end marker to the log file and clears the session
        reference. Safe to call even if no session is active (no-op).
        """
        if self._session_file:
            self._write_entry(
                {
                    "type": "session_end",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self._session_id,
                }
            )

        logger.info("conversation_logger_ended", session_id=self._session_id)
        self._session_file = None
        self._session_id = None

    def _write_entry(self, entry: Dict) -> None:
        """Write a log entry to the session file as a JSONL line.

        Args:
            entry: A dictionary representing the log entry. Serialized to JSON
                with ensure_ascii=False before writing. Silently drops the
                entry if no session is active (no session file set).
        """
        if not self._session_file:
            return

        with self._lock:
            try:
                with open(self._session_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("conversation_log_write_failed", exc_info=e)

    def get_recent_logs(self, limit: int = 10) -> List[Dict]:
        """Read the most recent log entries from the current session file.

        Args:
            limit: Maximum number of entries to return. Reads from the end
                of the file backward. Defaults to 10.

        Returns:
            A list of parsed log entry dicts, most recent last.
            Returns an empty list if no session is active or the log file
            does not exist.
        """
        if not self._session_file or not self._session_file.exists():
            return []

        entries = []
        try:
            with open(self._session_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error("conversation_log_read_failed", exc_info=e)

        return entries

    @staticmethod
    def list_log_files(log_dir: str = None) -> List[Path]:
        """List all conversation log files on disk.

        Args:
            log_dir: Directory to scan for log files. Defaults to the
                project's logs/ directory.

        Returns:
            A list of Path objects pointing to .jsonl log files in
            the directory, sorted newest-first (by filename timestamp).
        """
        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"

        log_path = Path(log_dir)
        if not log_path.exists():
            return []

        return sorted(log_path.glob("conversation_*.jsonl"), reverse=True)
