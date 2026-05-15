"""Beaver Agent Long-Term Memory - Persistent memory across sessions."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger()

__all__ = ["MemoryCategory", "MemoryEntry", "MemoryQuery", "LongTermMemory"]


class MemoryCategory(Enum):
    """Categories of long-term memory."""

    USER_PREFERENCE = "user_preference"  # User likes/dislikes, communication style
    PROJECT_CONTEXT = "project_context"  # Project structure, conventions, tech stack
    SOLUTION = "solution"  # Past problems and how they were solved
    FACT = "fact"  # General facts about the world or user
    CONVENTION = "convention"  # Project-specific conventions and patterns
    TOOL_USAGE = "tool_usage"  # How to use specific tools effectively


@dataclass
class MemoryEntry:
    """A single memory entry with metadata.

    Attributes:
        id: Unique identifier for this memory entry.
        content: The memory text content.
        category: Category classification from MemoryCategory enum.
        tags: List of tag strings for filtering and retrieval.
        created_at: Unix timestamp when this entry was first created.
        last_accessed: Unix timestamp of the most recent access.
        access_count: Number of times this entry has been retrieved.
        session_id: Optional session ID that created this entry.
        source: Source of the entry — "auto" for extracted, "manual" for
            user-explicit saves.
    """

    id: str
    content: str
    category: MemoryCategory
    tags: list[str]
    created_at: float
    last_accessed: float
    access_count: int
    session_id: Optional[str] = None
    source: str = "auto"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the memory entry to a dictionary.

        Returns:
            Dictionary containing all memory entry fields (id, content,
            category, tags, created_at, last_accessed, access_count,
            session_id, source) suitable for JSON serialization.
        """
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category.value,
            "tags": self.tags,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "session_id": self.session_id,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        """Reconstruct a MemoryEntry from a dictionary.

        Args:
            data: Dictionary with memory entry fields (id, content, category
                required; tags, last_accessed, access_count, session_id,
                source are optional with sensible defaults).

        Returns:
            A MemoryEntry instance reconstructed from the dictionary.
        """
        return cls(
            id=data["id"],
            content=data["content"],
            category=MemoryCategory(data["category"]),
            tags=data.get("tags", []),
            created_at=data["created_at"],
            last_accessed=data.get("last_accessed", data["created_at"]),
            access_count=data.get("access_count", 0),
            session_id=data.get("session_id"),
            source=data.get("source", "auto"),
        )


@dataclass
class MemoryQuery:
    """Query parameters for memory search."""

    query: str
    categories: Optional[list[MemoryCategory]] = None
    tags: Optional[list[str]] = None
    limit: int = 10
    recency_weight: float = 0.3  # Weight for recency in scoring (0-1)


class LongTermMemory:
    """
    Persistent long-term memory that survives across sessions.

    Stores memories in ``data/memory/`` directory as JSONL files, one per category.
    Automatically extracts and stores:
    - User preferences and communication style
    - Project conventions and structure
    - Past solutions to problems
    - Important facts

    Retrieval uses keyword matching with recency weighting.
    """

    MAX_ENTRIES_PER_CATEGORY = 500  # Soft limit for file size management
    DEFAULT_TAGS = ["important", "learned"]

    def __init__(self, memory_dir: Path):
        """Initialize long-term memory.

        Args:
            memory_dir: Root directory for memory storage.
                Creates subdirectories per category.
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Index: category -> list of entries (loaded lazily)
        self._index: dict[MemoryCategory, list[MemoryEntry]] = {}
        self._index_loaded: set[MemoryCategory] = set()

        logger.info("long_term_memory_initialized", memory_dir=str(self.memory_dir))

    # ─────────────────────────────────────────────────────────────────
    # Storage
    # ─────────────────────────────────────────────────────────────────

    def _get_category_file(self, category: MemoryCategory) -> Path:
        """Get the storage file path for a category."""
        return self.memory_dir / f"{category.value}.jsonl"

    def _ensure_category_loaded(self, category: MemoryCategory) -> None:
        """Lazily load a category's entries from disk."""
        if category in self._index_loaded:
            return

        category_file = self._get_category_file(category)
        entries: list[MemoryEntry] = []

        if category_file.exists():
            try:
                with open(category_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                entries.append(MemoryEntry.from_dict(data))
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.warning(
                                    "memory_entry_parse_failed",
                                    category=category.value,
                                    exc_info=e,
                                )
            except IOError as e:
                logger.error(
                    "memory_file_read_failed",
                    category=category.value,
                    exc_info=e,
                )
                # Continue with empty entries so the category at least
                # appears loadable; the caller sees an empty list, not a crash.
                entries = []

        self._index[category] = entries
        self._index_loaded.add(category)

    def add(
        self,
        content: str,
        category: MemoryCategory,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        source: str = "auto",
    ) -> str:
        """Add a new memory entry.

        Args:
            content: The memory content to store.
            category: The memory category.
            tags: Optional tags for retrieval (defaults to ["important"]).
            session_id: Optional session ID for provenance.
            source: "auto" for extracted, "manual" for explicitly saved.

        Returns:
            The generated memory ID.
        """
        self._ensure_category_loaded(category)

        memory_id = f"mem_{int(time.time() * 1000)}"
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            category=category,
            tags=tags or self.DEFAULT_TAGS,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0,
            session_id=session_id,
            source=source,
        )

        # Append to category file
        category_file = self._get_category_file(category)
        try:
            with open(category_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except IOError as e:
            logger.error(
                "memory_write_failed",
                category=category.value,
                exc_info=e,
            )
            return ""

        # Update in-memory index
        self._index[category].append(entry)

        # Trim if exceeds limit (remove oldest entries)
        self._trim_category(category)

        logger.info(
            "memory_added",
            memory_id=memory_id,
            category=category.value,
            content_preview=content[:50],
        )

        return memory_id

    def _trim_category(self, category: MemoryCategory) -> None:
        """Remove oldest entries if category exceeds max size."""
        entries = self._index.get(category, [])
        if len(entries) <= self.MAX_ENTRIES_PER_CATEGORY:
            return

        # Sort by created_at, keep newest MAX_ENTRIES
        sorted_entries = sorted(entries, key=lambda e: e.created_at, reverse=True)
        trimmed = sorted_entries[: self.MAX_ENTRIES_PER_CATEGORY]

        # Rewrite file
        category_file = self._get_category_file(category)
        try:
            with open(category_file, "w", encoding="utf-8") as f:
                for entry in trimmed:
                    f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except IOError as e:
            logger.error("memory_trim_failed", category=category.value, exc_info=e)
            return

        self._index[category] = trimmed
        logger.info(
            "memory_trimmed",
            category=category.value,
            removed=len(entries) - len(trimmed),
        )

    # ─────────────────────────────────────────────────────────────────
    # Retrieval
    # ─────────────────────────────────────────────────────────────────

    def search(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Search memories by keyword with recency weighting.

        Args:
            query: Query parameters including search string, filters, and limit.

        Returns:
            List of matching MemoryEntry objects, sorted by relevance score
            (keyword match + recency + access frequency).
        """
        query_lower = query.query.lower()
        query_terms = set(query_lower.split())

        scored_entries: list[tuple[float, MemoryEntry]] = []

        categories_to_search = query.categories if query.categories else list(MemoryCategory)

        for category in categories_to_search:
            self._ensure_category_loaded(category)
            entries = self._index.get(category, [])

            for entry in entries:
                # Filter by tags if specified
                if query.tags:
                    if not any(tag in entry.tags for tag in query.tags):
                        continue

                # Calculate relevance score
                score = self._calculate_relevance(entry, query_terms, query.recency_weight)

                if score > 0:
                    scored_entries.append((score, entry))

        # Sort by score descending
        scored_entries.sort(key=lambda x: x[0], reverse=True)

        # Update access stats for returned entries
        returned = []
        for score, entry in scored_entries[: query.limit]:
            entry.access_count += 1
            entry.last_accessed = time.time()
            returned.append(entry)

        # Async write back access stats (skip for now to avoid I/O overhead)
        # Could be batched in production

        return returned

    def _calculate_relevance(
        self,
        entry: MemoryEntry,
        query_terms: set[str],
        recency_weight: float,
    ) -> float:
        """Calculate relevance score for a memory entry.

        Combines four signals into a weighted relevance score:
        1. Keyword match ratio (proportion of query terms found in content)
        2. Tag bonus (+0.1 per query term that matches an entry tag)
        3. Recency score (exponential decay, half-life ~30 days)
        4. Access frequency bonus (log scale, capped at 1.0)

        Args:
            entry: The memory entry to score.
            query_terms: Set of lowercase terms from the search query.
            recency_weight: Weight for recency vs. keyword matching (0.0–1.0).
                Higher values favor recent entries; lower values favor keyword matches.

        Returns:
            Composite relevance score in range [0.0, ~2.4]. Higher scores indicate
            stronger relevance. Unmatched entries return 0.0.
        """
        content_lower = entry.content.lower()

        # Keyword matching score
        match_count = sum(1 for term in query_terms if term in content_lower)
        if match_count == 0:
            return 0.0

        keyword_score = match_count / len(query_terms)

        # Tag bonus (exact match with query terms as tags)
        tag_bonus = sum(0.1 for term in query_terms if term in entry.tags)

        # Recency score (exponential decay, half-life ~30 days)
        age_days = (time.time() - entry.created_at) / 86400
        recency_score = 0.5 ** (age_days / 30)

        # Access frequency bonus (log scale)
        frequency_score = min(1.0, (entry.access_count**0.5) / 10)

        return (
            keyword_score * (1 - recency_weight)
            + recency_score * recency_weight
            + tag_bonus
            + frequency_score * 0.1
        )

    def get_recent(
        self,
        category: Optional[MemoryCategory] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Get the most recent memory entries.

        Args:
            category: Optional category filter. If None, searches all.
            limit: Maximum number of entries to return.

        Returns:
            List of recent MemoryEntry objects, newest first.
        """
        if category:
            self._ensure_category_loaded(category)
            entries = sorted(
                self._index.get(category, []),
                key=lambda e: e.created_at,
                reverse=True,
            )
            return entries[:limit]

        # All categories
        all_entries: list[MemoryEntry] = []
        for cat in MemoryCategory:
            self._ensure_category_loaded(cat)
            all_entries.extend(self._index.get(cat, []))

        all_entries.sort(key=lambda e: e.created_at, reverse=True)
        return all_entries[:limit]

    # ─────────────────────────────────────────────────────────────────
    # High-Level Operations
    # ─────────────────────────────────────────────────────────────────

    def remember_user_preference(
        self,
        preference: str,
        session_id: Optional[str] = None,
    ) -> str:
        """Convenience method to store a user preference.

        Args:
            preference: The preference content (e.g., "User prefers Chinese communication").
            session_id: Optional associated session.

        Returns:
            The generated memory ID.
        """
        return self.add(
            content=preference,
            category=MemoryCategory.USER_PREFERENCE,
            tags=["preference", "user"],
            session_id=session_id,
        )

    def remember_project_fact(
        self,
        fact: str,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Convenience method to store a project-related fact.

        Args:
            fact: The fact content (e.g., "Project uses pytest with xdist").
            tags: Optional tags (defaults to ["project", "fact"]).
            session_id: Optional associated session.

        Returns:
            The generated memory ID.
        """
        return self.add(
            content=fact,
            category=MemoryCategory.PROJECT_CONTEXT,
            tags=tags or ["project", "fact"],
            session_id=session_id,
        )

    def remember_solution(
        self,
        problem: str,
        solution: str,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Store a problem-solution pair.

        Args:
            problem: Description of the problem.
            solution: How it was solved.
            tags: Optional tags for retrieval.
            session_id: Optional associated session.

        Returns:
            The generated memory ID.
        """
        content = f"Problem: {problem}\nSolution: {solution}"
        return self.add(
            content=content,
            category=MemoryCategory.SOLUTION,
            tags=tags or ["solution", "problem"],
            session_id=session_id,
        )

    def remember_convention(
        self,
        convention: str,
        context: str = "",
        session_id: Optional[str] = None,
    ) -> str:
        """Store a project convention or pattern.

        Args:
            convention: The convention description.
            context: Optional additional context.
            session_id: Optional associated session.

        Returns:
            The generated memory ID.
        """
        content = convention if not context else f"{convention}\nContext: {context}"
        return self.add(
            content=content,
            category=MemoryCategory.CONVENTION,
            tags=["convention", "pattern"],
            session_id=session_id,
        )

    def get_context_for_prompt(
        self,
        query: Optional[str] = None,
        categories: Optional[list[MemoryCategory]] = None,
        limit: int = 5,
    ) -> str:
        """Get formatted context string for LLM prompt injection.

        This is the main method for integrating long-term memory
        into the agent's prompt context.

        Args:
            query: Optional search query to find relevant memories.
            categories: Optional category filter.
            limit: Maximum memories to include.

        Returns:
            A formatted string suitable for injection into a prompt,
            or empty string if no relevant memories found.
        """
        if query:
            results = self.search(MemoryQuery(query=query, categories=categories, limit=limit))
        else:
            # Get recent memories
            all_recent = []
            cats = categories if categories else list(MemoryCategory)
            for cat in cats:
                all_recent.extend(self.get_recent(category=cat, limit=limit))
            all_recent.sort(key=lambda e: e.last_accessed, reverse=True)
            results = all_recent[:limit]

        if not results:
            return ""

        lines = ["[Long-Term Memory]"]
        for entry in results:
            category_label = entry.category.value.replace("_", " ").title()
            date_str = datetime.fromtimestamp(entry.created_at).strftime("%Y-%m-%d")
            lines.append(f"\n## {category_label} ({date_str})")
            lines.append(entry.content)
            if entry.tags:
                lines.append(f"Tags: {', '.join(entry.tags)}")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────
    # Management
    # ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        stats = {
            "categories": {},
            "total_entries": 0,
        }

        for category in MemoryCategory:
            self._ensure_category_loaded(category)
            count = len(self._index.get(category, []))
            stats["categories"][category.value] = count
            stats["total_entries"] += count

        return stats

    def clear_category(self, category: MemoryCategory) -> None:
        """Clear all memories in a category.

        Args:
            category: The category to clear.
        """
        category_file = self._get_category_file(category)
        if category_file.exists():
            category_file.unlink()

        if category in self._index:
            self._index[category] = []

        logger.info("memory_category_cleared", category=category.value)
