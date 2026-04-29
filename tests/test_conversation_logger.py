"""Tests for ConversationLogger"""

import json
import tempfile
from pathlib import Path

import pytest

from beaver_bot.core.conversation_logger import ConversationLogger


class TestConversationLogger:
    """Test ConversationLogger functionality"""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary log directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Create a logger with temp directory"""
        return ConversationLogger(log_dir=str(temp_log_dir))

    def test_start_session(self, logger, temp_log_dir):
        """Test starting a new session"""
        logger.start_session("test-session-123")

        # Should have created a log file
        log_files = list(temp_log_dir.glob("conversation_*_test-session-123.jsonl"))
        assert len(log_files) == 1

        # Should have written session_start entry
        with open(log_files[0]) as f:
            entry = json.loads(f.readline())
            assert entry["type"] == "session_start"
            assert entry["session_id"] == "test-session-123"

    def test_log_user_input(self, logger, temp_log_dir):
        """Test logging user input"""
        logger.start_session("test-input")
        logger.log_user_input("Hello, how are you?", intent="greeting")

        log_files = list(temp_log_dir.glob("conversation_*_test-input.jsonl"))
        with open(log_files[0]) as f:
            lines = f.readlines()
            entry = json.loads(lines[-1])
            assert entry["type"] == "user_input"
            assert entry["content"] == "Hello, how are you?"
            assert entry["intent"] == "greeting"

    def test_log_llm_request_response(self, logger, temp_log_dir):
        """Test logging LLM request and response"""
        logger.start_session("test-llm")

        messages = [{"role": "user", "content": "Hello"}]
        logger.log_llm_request(messages, model="test-model", provider="test")

        logger.log_llm_response(
            content="Hi there!",
            model="test-model",
            usage={"input_tokens": 10, "output_tokens": 5}
        )

        log_files = list(temp_log_dir.glob("conversation_*_test-llm.jsonl"))
        with open(log_files[0]) as f:
            lines = f.readlines()
            req_entry = json.loads(lines[-2])
            resp_entry = json.loads(lines[-1])

            assert req_entry["type"] == "llm_request"
            assert req_entry["model"] == "test-model"

            assert resp_entry["type"] == "llm_response"
            assert resp_entry["content"] == "Hi there!"
            assert resp_entry["usage"]["input_tokens"] == 10

    def test_log_tool_call(self, logger, temp_log_dir):
        """Test logging tool calls"""
        logger.start_session("test-tool")
        logger.log_tool_call(
            tool_name="file_tool",
            action="read_file",
            params={"path": "/tmp/test.txt"},
            result={"success": True, "data": "file content"},
            success=True
        )

        log_files = list(temp_log_dir.glob("conversation_*_test-tool.jsonl"))
        with open(log_files[0]) as f:
            lines = f.readlines()
            entry = json.loads(lines[-1])
            assert entry["type"] == "tool_call"
            assert entry["tool"] == "file_tool"
            assert entry["action"] == "read_file"
            assert entry["success"] is True

    def test_log_skill_invocation(self, logger, temp_log_dir):
        """Test logging skill invocation"""
        logger.start_session("test-skill")
        logger.log_skill_invocation(
            skill_name="mcp-config",
            trigger="配置",
            matched=True
        )

        log_files = list(temp_log_dir.glob("conversation_*_test-skill.jsonl"))
        with open(log_files[0]) as f:
            lines = f.readlines()
            entry = json.loads(lines[-1])
            assert entry["type"] == "skill_invocation"
            assert entry["skill"] == "mcp-config"

    def test_end_session(self, logger, temp_log_dir):
        """Test ending a session"""
        logger.start_session("test-end")
        logger.log_user_input("Test input", intent=None)
        logger.end_session()

        log_files = list(temp_log_dir.glob("conversation_*_test-end.jsonl"))
        with open(log_files[0]) as f:
            lines = f.readlines()
            entry = json.loads(lines[-1])
            assert entry["type"] == "session_end"
            assert entry["session_id"] == "test-end"

    def test_get_recent_logs(self, logger, temp_log_dir):
        """Test retrieving recent logs"""
        logger.start_session("test-recent")
        for i in range(15):
            logger.log_user_input(f"Message {i}", intent=None)

        recent = logger.get_recent_logs(limit=5)
        assert len(recent) == 5
        assert recent[-1]["content"] == "Message 14"

    def test_list_log_files(self, temp_log_dir):
        """Test listing all log files"""
        # Create multiple log files
        logger1 = ConversationLogger(log_dir=str(temp_log_dir))
        logger1.start_session("session-1")
        logger1.end_session()

        logger2 = ConversationLogger(log_dir=str(temp_log_dir))
        logger2.start_session("session-2")
        logger2.end_session()

        files = ConversationLogger.list_log_files(log_dir=str(temp_log_dir))
        assert len(files) == 2

    def test_content_truncation(self, logger, temp_log_dir):
        """Test that very long content is truncated"""
        logger.start_session("test-truncate")

        long_message = "A" * 5000
        logger.log_user_input(long_message, intent=None)

        log_files = list(temp_log_dir.glob("conversation_*_test-truncate.jsonl"))
        with open(log_files[0]) as f:
            lines = f.readlines()
            entry = json.loads(lines[-1])
            # Content should be truncated
            assert len(entry["content"]) < 5000
            assert "[truncated]" in entry["content"]
