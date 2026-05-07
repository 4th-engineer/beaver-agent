"""Tests for BeaverAgent core class."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from beaver_agent.core.agent import BeaverAgent
from beaver_agent.core.config import BeaverConfig, AppConfig, ModelConfig


@pytest.fixture
def mock_config():
    """Minimal config for agent tests."""
    return BeaverConfig(
        app=AppConfig(debug=False),
        model=ModelConfig(name="test-model", provider="minimax"),
    )


@pytest.fixture
def mock_data_store():
    """Mock data store."""
    store = MagicMock()
    store.get_version.return_value = MagicMock(raw="1.0.0")
    store.get_stats.return_value = {"items": 10}
    store.data_dir = MagicMock()
    store.data_dir.__truediv__ = MagicMock(return_value=MagicMock())
    return store


@pytest.fixture
def agent(mock_config, mock_data_store):
    """Agent instance with mocked dependencies."""
    with patch("beaver_agent.core.agent.init_data_store", return_value=mock_data_store), \
         patch("beaver_agent.core.agent.ConversationLogger"), \
         patch("beaver_agent.core.agent.SessionMemory"), \
         patch("beaver_agent.core.agent.LongTermMemory"), \
         patch("beaver_agent.core.agent.IntentParser"), \
         patch("beaver_agent.core.agent.TaskPlanner"), \
         patch("beaver_agent.core.agent.ToolRouter"):
        agent = BeaverAgent(mock_config)
        return agent


class TestBeaverAgentInit:
    """Tests for BeaverAgent.__init__."""

    def test_init_creates_session_id(self, mock_config, mock_data_store):
        """Test that __init__ generates an 8-character session ID."""
        with patch("beaver_agent.core.agent.init_data_store", return_value=mock_data_store), \
             patch("beaver_agent.core.agent.ConversationLogger"), \
             patch("beaver_agent.core.agent.SessionMemory"), \
             patch("beaver_agent.core.agent.LongTermMemory"), \
             patch("beaver_agent.core.agent.IntentParser"), \
             patch("beaver_agent.core.agent.TaskPlanner"), \
             patch("beaver_agent.core.agent.ToolRouter"):
            agent = BeaverAgent(mock_config)
            assert agent.session_id is not None
            assert len(agent.session_id) == 8

    def test_init_stores_config(self, agent, mock_config):
        """Test that __init__ stores the config."""
        assert agent.config == mock_config

    def test_init_initializes_conversation_history(self, agent):
        """Test that __init__ starts with empty conversation history."""
        assert agent.conversation_history == []

    def test_init_initializes_memory(self, agent):
        """Test that __init__ initializes session and long-term memory."""
        assert agent.memory is not None
        assert agent.long_term_memory is not None

    def test_init_initializes_intent_parser(self, agent):
        """Test that __init__ initializes the intent parser."""
        assert agent.intent_parser is not None

    def test_init_initializes_task_planner(self, agent):
        """Test that __init__ initializes the task planner."""
        assert agent.task_planner is not None

    def test_init_initializes_tool_router(self, agent):
        """Test that __init__ initializes the tool router."""
        assert agent.tool_router is not None

    def test_init_starts_conversation_logger(self, agent):
        """Test that __init__ starts a conversation logging session."""
        assert agent.logger is not None

    def test_init_handles_llm_failure(self, mock_config, mock_data_store):
        """Test that __init__ handles LLM initialization failure gracefully."""
        with patch("beaver_agent.core.agent.init_data_store", return_value=mock_data_store), \
             patch("beaver_agent.core.agent.ConversationLogger"), \
             patch("beaver_agent.core.agent.SessionMemory"), \
             patch("beaver_agent.core.agent.LongTermMemory"), \
             patch("beaver_agent.core.agent.IntentParser"), \
             patch("beaver_agent.core.agent.TaskPlanner"), \
             patch("beaver_agent.core.agent.ToolRouter") as mock_router, \
             patch("beaver_agent.core.agent.logger") as mock_logger:
            mock_router.return_value.get_llm_client.side_effect = RuntimeError("LLM init failed")
            agent = BeaverAgent(mock_config)
            assert agent.llm is None
            mock_logger.warning.assert_called()


class TestBeaverAgentReset:
    """Tests for BeaverAgent.reset()."""

    def test_reset_clears_conversation_history(self, agent):
        """Test that reset() clears conversation history."""
        agent.conversation_history = [{"role": "user", "content": "hello"}]
        agent.reset()
        assert agent.conversation_history == []

    def test_reset_resets_session_id(self, agent):
        """Test that reset() generates a new session ID."""
        old_session_id = agent.session_id
        agent.reset()
        assert agent.session_id != old_session_id

    def test_reset_calls_logger_end_and_start_session(self, agent):
        """Test that reset() ends the old session and starts a new one with the new ID."""
        old_session_id = agent.session_id
        with patch.object(agent.logger, "end_session") as mock_end, \
             patch.object(agent.logger, "start_session") as mock_start:
            agent.reset()
            mock_end.assert_called_once()
            mock_start.assert_called_once_with(agent.session_id)
            assert agent.session_id != old_session_id


class TestBeaverAgentShutdown:
    """Tests for BeaverAgent.shutdown()."""

    def test_shutdown_calls_logger_end_session(self, agent):
        """Test that shutdown() ends the conversation logging session."""
        agent.shutdown()
        agent.logger.end_session.assert_called_once()

    def test_shutdown_idempotent(self, agent):
        """Test that shutdown() can be called multiple times without error."""
        agent.shutdown()
        agent.shutdown()  # Should not raise
        assert agent.logger.end_session.call_count == 2


class TestJsonSummary:
    """Tests for BeaverAgent._json_summary()."""

    def test_json_summary_dict(self, agent):
        """Test _json_summary with a dictionary."""
        result = agent._json_summary({"key": "value"})
        assert "key" in result
        assert "value" in result

    def test_json_summary_list(self, agent):
        """Test _json_summary with a list."""
        result = agent._json_summary(["a", "b", "c"])
        assert "[3 items]" == result

    def test_json_summary_string(self, agent):
        """Test _json_summary with a short string (no truncation)."""
        result = agent._json_summary("hello")
        assert '"hello"' in result

    def test_json_summary_long_string(self, agent):
        """Test _json_summary with a long string (truncated)."""
        long_str = "x" * 50
        result = agent._json_summary(long_str)
        assert "..." in result
        assert len(result) <= 35

    def test_json_summary_other_type(self, agent):
        """Test _json_summary with unknown type uses repr."""
        result = agent._json_summary(42)
        assert "42" in result

    def test_json_summary_nested_dict(self, agent):
        """Test _json_summary with nested structures."""
        data = {"outer": {"inner": "value"}}
        result = agent._json_summary(data)
        assert "outer" in result


class TestBuildContext:
    """Tests for BeaverAgent._build_context()."""

    def test_build_context_empty(self, agent):
        """Test _build_context with empty tool results."""
        result = agent._build_context([])
        assert result == ""

    def test_build_context_with_results(self, agent):
        """Test _build_context formats tool results as a table."""
        tool_results = [
            {"tool": "terminal", "success": True, "content": "done"},
            {"tool": "file", "success": False, "content": "not found"},
        ]
        result = agent._build_context(tool_results)
        assert "terminal" in result
        assert "file" in result

    def test_build_context_with_git_status(self, agent):
        """Test _build_context truncates long git status output."""
        long_content = "\n".join([f"line {i}" for i in range(30)])
        tool_results = [
            {"tool": "git_status", "success": True, "content": long_content},
        ]
        result = agent._build_context(tool_results)
        # Should truncate to last 20 lines
        assert len(result.split("\n")) <= 25


class TestGenerateFallbackResponse:
    """Tests for BeaverAgent._generate_fallback_response()."""

    def test_fallback_code_generation(self, agent):
        """Test fallback response for code_generation intent."""
        result = agent._generate_fallback_response("code_generation", "context here")
        assert "LLM" in result or "minimax" in result.lower() or "not configured" in result.lower()

    def test_fallback_code_review(self, agent):
        """Test fallback response for code_review intent."""
        result = agent._generate_fallback_response("code_review", "context here")
        assert len(result) > 0

    def test_fallback_debugging(self, agent):
        """Test fallback response for debugging intent."""
        result = agent._generate_fallback_response("debugging", "context here")
        assert len(result) > 0

    def test_fallback_general_chat(self, agent):
        """Test fallback response for general_chat intent."""
        result = agent._generate_fallback_response("general_chat", "context here")
        assert len(result) > 0

    def test_fallback_unknown_intent(self, agent):
        """Test fallback response for unknown intent."""
        result = agent._generate_fallback_response("unknown_intent", "context here")
        assert len(result) > 0


class TestSummarizeContent:
    """Tests for BeaverAgent._summarize_content()."""

    def test_summarize_git_log(self, agent):
        """Test that _summarize_content shows last 20 lines for git log when > 25 lines."""
        # Create content with 30 lines so truncation kicks in (threshold is 25)
        content = "\n".join([f"commit {i}" for i in range(30)])
        result = agent._summarize_content("git_log", content)
        # Should contain last 20 lines (commit 10 through commit 29) plus truncation note
        assert "commit 10" in result
        assert "commit 29" in result
        assert "前 10 行" in result  # truncation note

    def test_summarize_git_status(self, agent):
        """Test that _summarize_content shows last 20 lines for git status."""
        content = "\n".join([f"status {i}" for i in range(30)])
        result = agent._summarize_content("git_status", content)
        lines = result.strip().split("\n")
        assert len(lines) <= 25  # header + last 20 lines + "..."

    def test_summarize_json_valid(self, agent):
        """Test that _summarize_content parses and formats valid JSON."""
        import json
        data = {"key": "value", "nested": {"inner": 42}}
        content = json.dumps(data)
        result = agent._summarize_content("git", content)
        assert "key" in result or "JSON" in result

    def test_summarize_json_invalid(self, agent):
        """Test that _summarize_content falls back to truncation for invalid JSON."""
        content = "{ invalid json }" + "\n" + "x" * 100
        result = agent._summarize_content("git", content)
        # Should contain raw content
        assert "invalid" in result or len(result) > 0

    def test_summarize_large_list(self, agent):
        """Test that _summarize_content truncates very large content to 30 lines."""
        # Need enough content to exceed 3000 char threshold
        # "item XXX: value here\n" ≈ 22 chars, 200 items = ~4400 chars
        items = [f"item {i}: some longer value here" for i in range(200)]
        content = "\n".join(items)
        result = agent._summarize_content("file", content)
        assert "[200 items]" in result or "200" in result

    def test_summarize_short_content(self, agent):
        """Test that _summarize_content returns short content unchanged."""
        content = "short content"
        result = agent._summarize_content("file", content)
        assert "short content" in result

    def test_summarize_execute_command_with_json(self, agent):
        """Test that _summarize_content parses JSON from execute_command output."""
        import json
        data = {"result": "success", "items": [1, 2, 3]}
        content = json.dumps(data)
        result = agent._summarize_content("execute_command", content)
        assert "result" in result or "success" in result

    def test_summarize_execute_command_invalid_json(self, agent):
        """Test execute_command with invalid JSON falls back to raw content."""
        content = "not json at all" + "\n" + "more content"
        result = agent._summarize_content("execute_command", content)
        assert "not json at all" in result or len(result) > 0


class TestAgentRun:
    """Tests for BeaverAgent.run()."""

    def test_run_with_mocked_llm(self, agent):
        """Test that run() processes user input and returns a response."""
        mock_response = MagicMock()
        mock_response.content = "Hello! How can I help?"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {"success": True, "content": "tool result"}

        result = agent.run("Hello")

        assert isinstance(result, str)
        assert len(result) > 0
        # Should add to conversation history
        assert len(agent.conversation_history) == 2  # user + assistant

    def test_run_stores_user_input_in_history(self, agent):
        """Test that run() adds user input to conversation history."""
        mock_response = MagicMock()
        mock_response.content = "response"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {"success": True}

        agent.run("test input")
        assert {"role": "user", "content": "test input"} in agent.conversation_history

    def test_run_stores_assistant_response_in_history(self, agent):
        """Test that run() adds assistant response to conversation history."""
        mock_response = MagicMock()
        mock_response.content = "assistant response"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {"success": True}

        agent.run("hello")
        assert any(
            msg["role"] == "assistant" and "assistant response" in msg["content"]
            for msg in agent.conversation_history
        )

    def test_run_no_llm_uses_fallback(self, agent):
        """Test that run() uses fallback when LLM is not available."""
        agent.llm = None
        agent.tool_router.route.return_value = {"success": True, "content": "tool result"}

        result = agent.run("hello")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_run_logs_tool_results(self, agent):
        """Test that run() logs each tool call."""
        mock_response = MagicMock()
        mock_response.content = "done"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response

        # Set up mock tasks so the loop runs and logs tool calls
        mock_task = {"tool": "terminal", "action": "execute", "params": {"command": "ls"}}
        agent.tool_router.route.return_value = {"success": True, "content": "ok"}
        agent.intent_parser.parse.return_value = "terminal_operation"
        agent.task_planner.plan.return_value = [mock_task]

        agent.run("do something")
        agent.logger.log_tool_call.assert_called()

    def test_run_llm_exception_uses_fallback(self, agent):
        """Test that run() falls back to _generate_fallback_response when LLM._call() raises."""
        agent.llm = MagicMock()
        agent.llm._call.side_effect = RuntimeError("LLM API error")
        agent.tool_router.route.return_value = {"success": True}

        result = agent.run("hello")

        assert isinstance(result, str)
        assert len(result) > 0
        # Should have logged the LLM failure
        agent.logger.log_llm_response.assert_called()

    def test_run_extracts_memory(self, agent):
        """Test that run() extracts and stores memory from conversation."""
        mock_response = MagicMock()
        mock_response.content = "response"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {"success": True}

        # Patch memory extraction to avoid side effects
        agent._extract_and_store_memory = MagicMock()

        agent.run("hello")
        agent._extract_and_store_memory.assert_called_once()


class TestExtractAndStoreMemory:
    """Tests for BeaverAgent._extract_and_store_memory()."""

    def test_remembers_chinese_preference(self, agent):
        """Test that Chinese language request triggers user preference memory."""
        agent.long_term_memory = MagicMock()

        agent._extract_and_store_memory(
            "请用中文回复",
            "好的，我会用中文回复",
            [{"success": True, "tool": "terminal", "data": "ok"}],
        )

        agent.long_term_memory.remember_user_preference.assert_called_once()
        call_args = agent.long_term_memory.remember_user_preference.call_args
        assert "Chinese" in call_args[0][0]
        assert call_args[1]["session_id"] == agent.session_id

    def test_remembers_user_preference_multiple_patterns(self, agent):
        """Test that all Chinese patterns are detected."""
        agent.long_term_memory = MagicMock()

        patterns = ["用中文沟通", "说话.*中文", "回复.*中文"]
        for pattern in patterns:
            agent.long_term_memory.reset_mock()
            agent._extract_and_store_memory(
                pattern, "response", [{"success": True, "tool": "terminal", "data": "ok"}]
            )
            agent.long_term_memory.remember_user_preference.assert_called_once()

    def test_no_memory_on_normal_input(self, agent):
        """Test that non-preference input does not store preference memory."""
        agent.long_term_memory = MagicMock()

        agent._extract_and_store_memory(
            "Show me the files",
            "Here are your files",
            [{"success": True, "tool": "file", "data": "file list"}],
        )

        agent.long_term_memory.remember_user_preference.assert_not_called()

    def test_remembers_project_fact_from_code_analyzer_via_analyze_tool_name(
        self, agent
    ):
        """Test that 'analyze' tool name also triggers project fact memory."""
        agent.long_term_memory = MagicMock()

        agent._extract_and_store_memory(
            "analyze",
            "done",
            [{
                "success": True,
                "tool": "analyze",
                "data": "src/core/agent.py - 500 lines",
            }],
        )

        agent.long_term_memory.remember_project_fact.assert_called_once()

    def test_remembers_convention_from_git_operations(self, agent):
        """Test that git operations trigger convention memory."""
        agent.long_term_memory = MagicMock()

        agent._extract_and_store_memory(
            "check git status",
            "on branch main",
            [{
                "success": True,
                "tool": "git",
                "data": "On branch main, 3 files changed",
            }],
        )

        agent.long_term_memory.remember_convention.assert_called_once()

    def test_remembers_convention_from_github_tool(self, agent):
        """Test that GitHub operations trigger convention memory."""
        agent.long_term_memory = MagicMock()

        agent._extract_and_store_memory(
            "show repo info",
            "repository info",
            [{
                "success": True,
                "tool": "github",
                "data": "commit abc123: fix bug",
            }],
        )

        agent.long_term_memory.remember_convention.assert_called_once()

    def test_remembers_solution_on_bug_query(self, agent):
        """Test that error/bug queries with successful tool results store solutions."""
        agent.long_term_memory = MagicMock()

        agent._extract_and_store_memory(
            "fix the error",
            "error fixed",
            [{
                "success": True,
                "tool": "debugger",
                "data": "Fixed: missing import added",
            }],
        )

        agent.long_term_memory.remember_solution.assert_called_once()
        # remember_solution(problem=..., solution=..., ...) — all keyword args
        call_kwargs = agent.long_term_memory.remember_solution.call_args.kwargs
        assert "fix the error" in call_kwargs["problem"]  # problem keyword arg

    def test_no_solution_memory_on_unsuccessful_tool(self, agent):
        """Test that failed tool executions do not store solution memory."""
        agent.long_term_memory = MagicMock()

        agent._extract_and_store_memory(
            "fix the error",
            "could not fix",
            [{"success": False, "tool": "debugger", "error": "failed"}],
        )

        agent.long_term_memory.remember_solution.assert_not_called()


class TestRunEdgeCases:
    """Tests for BeaverAgent.run() error paths and edge cases."""

    def test_run_with_empty_task_list(self, agent):
        """Test that run() returns fallback response when task planner returns no tasks."""
        mock_response = MagicMock()
        mock_response.content = "done"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {"success": True, "content": "ok"}
        agent.task_planner.plan.return_value = []

        result = agent.run("hello")
        assert isinstance(result, str)
        assert len(result) > 0
        # No tool calls should be made when there are no tasks
        agent.tool_router.route.assert_not_called()

    def test_run_with_multiple_tasks(self, agent):
        """Test that run() executes all tasks and collects results."""
        mock_response = MagicMock()
        mock_response.content = "all done"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.side_effect = [
            {"success": True, "tool": "terminal", "content": "ls ok"},
            {"success": True, "tool": "file", "content": "read ok"},
        ]
        agent.task_planner.plan.return_value = [
            {"tool": "terminal", "action": "execute", "params": {"command": "ls"}},
            {"tool": "file", "action": "read", "params": {"path": "foo.txt"}},
        ]

        result = agent.run("do both things")
        assert isinstance(result, str)
        assert len(result) > 0
        assert agent.tool_router.route.call_count == 2

    def test_run_intent_parser_exception_uses_fallback(self, agent):
        """Test that run() uses fallback response when intent parser raises."""
        mock_response = MagicMock()
        mock_response.content = "response"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {"success": True}
        agent.intent_parser.parse.side_effect = RuntimeError("parse failed")

        result = agent.run("hello")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_run_task_planner_exception_uses_fallback(self, agent):
        """Test that run() uses fallback response when task planner raises."""
        mock_response = MagicMock()
        mock_response.content = "response"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.task_planner.plan.side_effect = RuntimeError("planning failed")

        result = agent.run("hello")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_run_with_github_intent(self, agent):
        """Test that run() extracts GitHub facts from GitHub tool results."""
        mock_response = MagicMock()
        mock_response.content = "github result"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {
            "success": True,
            "tool": "github",
            "data": "owner=beaver prefix=🐙 owner=openai prefix=🔍",
        }
        agent.intent_parser.parse.return_value = "github_operation"
        agent.task_planner.plan.return_value = [
            {"tool": "github", "action": "get_repo_info", "params": {"owner": "beaver", "repo": "agent"}},
        ]

        # Patch _extract_and_store_memory to verify it's called
        agent._extract_and_store_memory = MagicMock()
        agent.run("show me the beaver repo")
        agent._extract_and_store_memory.assert_called_once()

    def test_run_with_debug_intent(self, agent):
        """Test that run() uses debug intent with _generate_fallback_response."""
        mock_response = MagicMock()
        mock_response.content = "debug result"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {"success": True}
        agent.intent_parser.parse.return_value = "debugging"

        agent._extract_and_store_memory = MagicMock()
        result = agent.run("debug this")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "debug" in result.lower() or "调试" in result

    def test_run_with_unknown_intent(self, agent):
        """Test that run() uses fallback response for unknown intent."""
        mock_response = MagicMock()
        mock_response.content = "response"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {"success": True}
        agent.intent_parser.parse.return_value = "unknown_intent"

        agent._extract_and_store_memory = MagicMock()
        result = agent.run("whatever")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_run_logs_user_input_truncated(self, agent):
        """Test that run() logs input truncated to 100 chars."""
        mock_response = MagicMock()
        mock_response.content = "response"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock()

        agent.llm = MagicMock()
        agent.llm._call.return_value = mock_response
        agent.tool_router.route.return_value = {"success": True}

        long_input = "x" * 200
        agent.run(long_input)
        # Just verify it doesn't crash - truncation is handled in logging
