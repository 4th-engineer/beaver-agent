"""Tests for Beaver Bot Session Memory"""


import pytest

from beaver_agent.core.memory.session import SessionMemory


@pytest.fixture
def memory():
    return SessionMemory()


def test_add_message(memory):
    """Test adding messages to memory"""
    memory.add_message("user", "Hello")
    memory.add_message("assistant", "Hi there")

    history = memory.get_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"


def test_clear_memory(memory):
    """Test clearing memory"""
    memory.add_message("user", "Hello")
    memory.clear()

    history = memory.get_history()
    assert len(history) == 0


def test_get_history_with_limit(memory):
    """Test getting history with limit"""
    for i in range(10):
        memory.add_message("user", f"Message {i}")

    history = memory.get_history(limit=3)
    assert len(history) == 3


def test_search_memory(memory):
    """Test searching memory"""
    memory.add_message("user", "Write a quicksort")
    memory.add_message("assistant", "Here's a quicksort")
    memory.add_message("user", "Add tests")

    results = memory.search("quicksort")
    assert len(results) == 2


def test_get_context(memory):
    """Test getting formatted context"""
    memory.add_message("user", "Hello")
    memory.add_message("assistant", "Hi")

    context = memory.get_context()
    # Exact format: "role: content" on each line
    lines = context.strip().split("\n")
    assert len(lines) == 2
    assert lines[0] == "user: Hello"
    assert lines[1] == "assistant: Hi"


def test_get_context_limit_20_messages(memory):
    """get_context includes at most the last 20 messages."""
    mem = SessionMemory()
    for i in range(25):
        mem.add_message("user", f"Message {i}")
    context = mem.get_context()
    lines = context.strip().split("\n")
    assert len(lines) == 20
    # Last message should be "Message 24"
    assert "Message 24" in lines[-1]
    # First message should be "Message 5" (oldest of the last 20)
    assert "Message 5" in lines[0]


def test_search_no_match(memory):
    """search returns empty list when query not found."""
    memory.add_message("user", "Hello world")
    results = memory.search("nonexistent")
    assert results == []


def test_search_case_insensitive(memory):
    """search is case-insensitive."""
    memory.add_message("user", "Hello WORLD")
    results = memory.search("world")
    assert len(results) == 1
    results = memory.search("HELLO")
    assert len(results) == 1


def test_get_history_empty(memory):
    """get_history returns empty list when memory is empty."""
    history = memory.get_history()
    assert history == []


def test_clear_empty_memory(memory):
    """clear succeeds on already-empty memory without error."""
    memory.clear()
    history = memory.get_history()
    assert history == []


def test_max_history_limit(memory):
    """Test that memory respects max history limit"""
    mem = SessionMemory(max_history=5)

    for i in range(10):
        mem.add_message("user", f"Message {i}")

    history = mem.get_history()
    assert len(history) == 5
    assert history[0]["content"] == "Message 5"  # Oldest messages dropped


def test_metadata_tracking(memory):
    """Test that metadata is tracked"""
    memory.add_message("user", "Test")

    assert "created_at" in memory.metadata
    assert "last_updated" in memory.metadata
