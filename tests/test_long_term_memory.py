"""Tests for Beaver Agent Long-Term Memory"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from beaver_agent.core.memory.long_term import (
    LongTermMemory,
    MemoryCategory,
    MemoryEntry,
    MemoryQuery,
)


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def memory(temp_memory_dir):
    """Create a LongTermMemory instance with temporary storage."""
    return LongTermMemory(temp_memory_dir)


@pytest.fixture
def populated_memory(temp_memory_dir):
    """Create a LongTermMemory with pre-populated entries."""
    mem = LongTermMemory(temp_memory_dir)
    mem.add(
        content="User preference: concise responses",
        category=MemoryCategory.USER_PREFERENCE,
        tags=["preference", "user"],
    )
    mem.add(
        content="Project uses pytest with xdist",
        category=MemoryCategory.PROJECT_CONTEXT,
        tags=["project", "testing"],
    )
    mem.add(
        content="Problem: file read failed\nSolution: check permissions",
        category=MemoryCategory.SOLUTION,
        tags=["solution", "problem"],
    )
    return mem


class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def test_to_dict(self):
        """Test MemoryEntry serialization to dict."""
        entry = MemoryEntry(
            id="mem_123",
            content="Test content",
            category=MemoryCategory.USER_PREFERENCE,
            tags=["test"],
            created_at=1000.0,
            last_accessed=1001.0,
            access_count=5,
            session_id="sess_abc",
            source="manual",
        )
        result = entry.to_dict()

        assert result["id"] == "mem_123"
        assert result["content"] == "Test content"
        assert result["category"] == "user_preference"
        assert result["tags"] == ["test"]
        assert result["created_at"] == 1000.0
        assert result["last_accessed"] == 1001.0
        assert result["access_count"] == 5
        assert result["session_id"] == "sess_abc"
        assert result["source"] == "manual"

    def test_from_dict(self):
        """Test MemoryEntry deserialization from dict."""
        data = {
            "id": "mem_456",
            "content": "Loaded content",
            "category": "project_context",
            "tags": ["project"],
            "created_at": 2000.0,
            "last_accessed": 2001.0,
            "access_count": 3,
            "session_id": "sess_xyz",
            "source": "auto",
        }
        entry = MemoryEntry.from_dict(data)

        assert entry.id == "mem_456"
        assert entry.content == "Loaded content"
        assert entry.category == MemoryCategory.PROJECT_CONTEXT
        assert entry.tags == ["project"]
        assert entry.created_at == 2000.0
        assert entry.last_accessed == 2001.0
        assert entry.access_count == 3
        assert entry.session_id == "sess_xyz"
        assert entry.source == "auto"

    def test_from_dict_defaults(self):
        """Test MemoryEntry.from_dict handles missing optional fields."""
        data = {
            "id": "mem_789",
            "content": "Minimal data",
            "category": "fact",
            "created_at": 3000.0,
        }
        entry = MemoryEntry.from_dict(data)

        assert entry.tags == []
        assert entry.last_accessed == 3000.0
        assert entry.access_count == 0
        assert entry.session_id is None
        assert entry.source == "auto"


class TestLongTermMemoryInit:
    """Tests for LongTermMemory initialization."""

    def test_init_creates_directory(self, temp_memory_dir):
        """Test that init creates the memory directory."""
        LongTermMemory(temp_memory_dir)
        assert temp_memory_dir.exists()

    def test_init_nonexistent_dir(self, temp_memory_dir):
        """Test that init creates subdirectories if they don't exist."""
        subdir = temp_memory_dir / "subdir" / "nested"
        LongTermMemory(subdir)
        assert subdir.exists()


class TestMemoryAdd:
    """Tests for adding memory entries."""

    def test_add_returns_memory_id(self, memory, temp_memory_dir):
        """Test that add returns a non-empty memory ID."""
        mem_id = memory.add(
            content="Test memory",
            category=MemoryCategory.FACT,
        )
        assert mem_id.startswith("mem_")
        assert len(mem_id) > 4

    def test_add_stores_in_file(self, memory, temp_memory_dir):
        """Test that add writes entry to category file."""
        memory.add(
            content="Persisted memory",
            category=MemoryCategory.FACT,
        )

        fact_file = temp_memory_dir / "fact.jsonl"
        assert fact_file.exists()

        with open(fact_file) as f:
            lines = f.readlines()
        assert len(lines) == 1

        entry_data = json.loads(lines[0])
        assert entry_data["content"] == "Persisted memory"
        assert entry_data["category"] == "fact"

    def test_add_with_tags(self, memory):
        """Test add with custom tags."""
        mem_id = memory.add(
            content="Tagged memory",
            category=MemoryCategory.CONVENTION,
            tags=["custom", "test"],
        )
        assert mem_id

        results = memory.search(MemoryQuery(query="Tagged"))
        assert len(results) == 1
        assert results[0].tags == ["custom", "test"]

    def test_add_with_session_id(self, memory):
        """Test add with session ID."""
        mem_id = memory.add(
            content="Session memory",
            category=MemoryCategory.USER_PREFERENCE,
            session_id="sess_123",
        )
        assert mem_id

    def test_add_multiple_categories(self, memory):
        """Test adding to different categories."""
        memory.add(content="Preference", category=MemoryCategory.USER_PREFERENCE)
        memory.add(content="Context", category=MemoryCategory.PROJECT_CONTEXT)
        memory.add(content="Solution", category=MemoryCategory.SOLUTION)

        stats = memory.get_stats()
        assert stats["total_entries"] == 3
        assert stats["categories"]["user_preference"] == 1
        assert stats["categories"]["project_context"] == 1
        assert stats["categories"]["solution"] == 1


class TestMemorySearch:
    """Tests for searching memory."""

    def test_search_returns_matches(self, populated_memory):
        """Test search finds matching entries."""
        results = populated_memory.search(MemoryQuery(query="pytest"))
        assert len(results) >= 1
        assert any("pytest" in r.content for r in results)

    def test_search_no_matches(self, populated_memory):
        """Test search returns empty for non-matching query."""
        results = populated_memory.search(MemoryQuery(query="nonexistent_term_xyz"))
        assert len(results) == 0

    def test_search_respects_limit(self, populated_memory):
        """Test search respects the limit parameter."""
        for i in range(5):
            populated_memory.add(
                content=f"Additional entry {i}",
                category=MemoryCategory.FACT,
                tags=["test"],
            )

        results = populated_memory.search(MemoryQuery(query="entry", limit=3))
        assert len(results) == 3

    def test_search_by_category(self, populated_memory):
        """Test search filters by category."""
        results = populated_memory.search(
            MemoryQuery(query="preference", categories=[MemoryCategory.USER_PREFERENCE])
        )
        assert len(results) >= 1
        for r in results:
            assert r.category == MemoryCategory.USER_PREFERENCE

    def test_search_updates_access_stats(self, populated_memory):
        """Test that search updates access_count and last_accessed."""
        results_before = populated_memory.search(MemoryQuery(query="pytest"))
        access_count_before = results_before[0].access_count

        results_after = populated_memory.search(MemoryQuery(query="pytest"))
        assert results_after[0].access_count > access_count_before

    def test_search_by_tags(self, populated_memory):
        """Test search filters by tags."""
        results = populated_memory.search(MemoryQuery(query="pytest", tags=["testing"]))
        assert len(results) >= 1


class TestMemoryGetRecent:
    """Tests for getting recent memories."""

    def test_get_recent_empty(self, memory):
        """Test get_recent on empty memory."""
        results = memory.get_recent()
        assert results == []

    def test_get_recent_single_category(self, populated_memory):
        """Test get_recent with category filter."""
        results = populated_memory.get_recent(category=MemoryCategory.USER_PREFERENCE)
        assert len(results) == 1
        assert results[0].category == MemoryCategory.USER_PREFERENCE

    def test_get_recent_all_categories(self, populated_memory):
        """Test get_recent across all categories."""
        results = populated_memory.get_recent(limit=10)
        assert len(results) == 3  # 3 entries from fixture

    def test_get_recent_respects_limit(self, memory):
        """Test get_recent respects limit."""
        for i in range(5):
            memory.add(content=f"Entry {i}", category=MemoryCategory.FACT)

        results = memory.get_recent(limit=3)
        assert len(results) == 3

    def test_get_recent_sorted_by_date(self, memory):
        """Test get_recent returns newest first."""
        memory.add(content="First", category=MemoryCategory.FACT)
        time.sleep(0.01)
        memory.add(content="Second", category=MemoryCategory.FACT)

        results = memory.get_recent(category=MemoryCategory.FACT)
        assert results[0].content == "Second"
        assert results[1].content == "First"


class TestMemoryConvenienceMethods:
    """Tests for high-level convenience methods."""

    def test_remember_user_preference(self, memory):
        """Test remember_user_preference convenience method."""
        mem_id = memory.remember_user_preference("User likes dark mode")
        assert mem_id

        results = memory.search(MemoryQuery(query="dark mode"))
        assert len(results) == 1
        assert results[0].category == MemoryCategory.USER_PREFERENCE
        assert results[0].tags == ["preference", "user"]

    def test_remember_project_fact(self, memory):
        """Test remember_project_fact convenience method."""
        mem_id = memory.remember_project_fact(
            "Project uses FastAPI",
            tags=["python", "web"],
        )
        assert mem_id

        results = memory.search(MemoryQuery(query="FastAPI"))
        assert len(results) == 1
        assert results[0].category == MemoryCategory.PROJECT_CONTEXT

    def test_remember_solution(self, memory):
        """Test remember_solution convenience method."""
        mem_id = memory.remember_solution(
            problem="Connection timeout",
            solution="Increase timeout and add retry logic",
        )
        assert mem_id

        results = memory.search(MemoryQuery(query="timeout"))
        assert len(results) == 1
        assert results[0].category == MemoryCategory.SOLUTION
        assert "Connection timeout" in results[0].content
        assert "Increase timeout" in results[0].content

    def test_remember_convention(self, memory):
        """Test remember_convention convenience method."""
        mem_id = memory.remember_convention(
            convention="Use structlog for logging",
            context="All modules must use structlog instead of print",
        )
        assert mem_id

        results = memory.search(MemoryQuery(query="structlog"))
        assert len(results) == 1
        assert results[0].category == MemoryCategory.CONVENTION
        assert "Context:" in results[0].content


class TestMemoryContext:
    """Tests for get_context_for_prompt."""

    def test_get_context_no_memories(self, memory):
        """Test get_context returns empty string when no memories."""
        context = memory.get_context_for_prompt()
        assert context == ""

    def test_get_context_with_query(self, populated_memory):
        """Test get_context with a search query."""
        context = populated_memory.get_context_for_prompt(query="pytest")
        assert "[Long-Term Memory]" in context
        assert "pytest" in context

    def test_get_context_without_query(self, populated_memory):
        """Test get_context returns recent memories when no query."""
        context = populated_memory.get_context_for_prompt(limit=5)
        assert "[Long-Term Memory]" in context

    def test_get_context_respects_limit(self, populated_memory):
        """Test get_context respects limit parameter."""
        for i in range(3):
            populated_memory.add(
                content=f"Extra {i}",
                category=MemoryCategory.FACT,
                tags=["extra"],
            )

        context = populated_memory.get_context_for_prompt(limit=2)
        # Should contain at most 2 entries
        assert context.count("##") <= 2


class TestMemoryStats:
    """Tests for get_stats."""

    def test_get_stats_empty(self, memory):
        """Test get_stats on empty memory."""
        stats = memory.get_stats()
        assert stats["total_entries"] == 0
        assert len(stats["categories"]) == len(MemoryCategory)

    def test_get_stats_populated(self, populated_memory):
        """Test get_stats with entries."""
        stats = populated_memory.get_stats()
        assert stats["total_entries"] == 3
        assert stats["categories"]["user_preference"] == 1
        assert stats["categories"]["project_context"] == 1
        assert stats["categories"]["solution"] == 1


class TestMemoryClear:
    """Tests for clear_category."""

    def test_clear_category(self, populated_memory):
        """Test clear_category removes entries."""
        populated_memory.clear_category(MemoryCategory.USER_PREFERENCE)

        stats = populated_memory.get_stats()
        assert stats["categories"]["user_preference"] == 0
        assert stats["total_entries"] == 2  # Other categories still exist

    def test_clear_nonexistent_category(self, memory):
        """Test clear_category on empty category doesn't error."""
        memory.clear_category(MemoryCategory.USER_PREFERENCE)  # Should not raise


class TestMemoryTrim:
    """Tests for automatic trimming of large categories."""

    def test_trim_after_max_entries(self, temp_memory_dir):
        """Test that entries are trimmed when exceeding MAX_ENTRIES_PER_CATEGORY."""
        mem = LongTermMemory(temp_memory_dir)

        # Add more entries than the limit
        for i in range(550):
            mem.add(content=f"Entry {i}", category=MemoryCategory.FACT, tags=[str(i)])

        stats = mem.get_stats()
        assert stats["categories"]["fact"] == 500  # MAX_ENTRIES_PER_CATEGORY

    def test_trim_keeps_newest(self, temp_memory_dir):
        """Test that trimming keeps the newest entries."""
        mem = LongTermMemory(temp_memory_dir)

        for i in range(510):
            mem.add(content=f"Old entry {i}", category=MemoryCategory.FACT)
            time.sleep(0.001)

        time.sleep(0.01)
        mem.add(content="Newest entry", category=MemoryCategory.FACT)

        recent = mem.get_recent(category=MemoryCategory.FACT, limit=1)
        assert recent[0].content == "Newest entry"


class TestMemoryQuery:
    """Tests for MemoryQuery dataclass."""

    def test_query_defaults(self):
        """Test MemoryQuery default values."""
        query = MemoryQuery(query="test")
        assert query.categories is None
        assert query.tags is None
        assert query.limit == 10
        assert query.recency_weight == 0.3

    def test_query_custom_values(self):
        """Test MemoryQuery with custom values."""
        query = MemoryQuery(
            query="custom",
            categories=[MemoryCategory.USER_PREFERENCE],
            tags=["test"],
            limit=5,
            recency_weight=0.5,
        )
        assert query.limit == 5
        assert query.recency_weight == 0.5
        assert query.categories == [MemoryCategory.USER_PREFERENCE]
