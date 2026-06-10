"""SQLite-backed LangGraph checkpointer — replaces the JSON-file Inbox.

For production use with state persistence across restarts, install
``langgraph-checkpoint-sqlite`` and set the ``CHECKPOINT_SQLITE_URL``
environment variable to a ``sqlite:///path/to/checkpoints.db`` DSN.

When that extra is not available, this module falls back to the built-in
``MemorySaver`` which retains state only for the lifetime of the process.
"""

from __future__ import annotations

import os
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Module-level singleton.
_SAVER = None
_CHECKPOINT_DIR: Path | None = None


def get_checkpointer(
    checkpoint_dir: Path | None = None,
    *,
    clone_from: Path | None = None,
):
    """Return a LangGraph checkpointer.

    **With** ``langgraph-checkpoint-sqlite`` installed and
    ``CHECKPOINT_SQLITE_URL`` set → ``SqliteSaver`` (persistent).

    Otherwise → ``MemorySaver`` (in-process only, survives restarts only
    via explicit clone/restore).

    Args:
        checkpoint_dir: Directory for SQLite file when using the sqlite backend.
                       Defaults to ``~/.beaver/checkpoints/``.
        clone_from:     Optional path to an existing SQLite checkpoint store.
                       Copied on first initialisation (once).
    """
    global _SAVER, _CHECKPOINT_DIR

    if _SAVER is not None:
        return _SAVER

    sqlite_url = os.environ.get("CHECKPOINT_SQLITE_URL", "").strip()

    if sqlite_url:
        _SAVER = _make_sqlite_checkpointer(sqlite_url, checkpoint_dir, clone_from)
    else:
        _SAVER = _make_memory_checkpointer()
        logger.info(
            "checkpointer_using_memory",
            note="Set CHECKPOINT_SQLITE_URL for persistent checkpoints",
        )

    return _SAVER


def _make_sqlite_checkpointer(
    sqlite_url: str,
    checkpoint_dir: Path | None,
    clone_from: Path | None,
):
    """Build a SqliteSaver checkpointer.

    Attempts to import ``langgraph.checkpoint.sqlite.SqliteSaver``.
    Raises ``ImportError`` with a helpful message if the extra is not installed.
    """
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        raise ImportError(
            "SqliteSaver requires the ``langgraph-checkpoint-sqlite`` extra.\n"
            "Install it with: uv pip install langgraph-checkpoint-sqlite\n"
            "Or set CHECKPOINT_SQLITE_URL to a sqlite:/// DSN."
        )

    if checkpoint_dir is None:
        checkpoint_dir = Path.home() / ".beaver" / "checkpoints"
    checkpoint_dir = checkpoint_dir.resolve()
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # If the DSN is a bare relative path like "checkpoints.db", resolve it
    # against the checkpoint_dir so it works as expected out of the box.
    if sqlite_url.startswith("sqlite:///") and not sqlite_url.startswith("sqlite:///"):
        resolved = str(checkpoint_dir / sqlite_url.removeprefix("sqlite:///"))
        sqlite_url = f"sqlite:///{resolved}"

    saver = SqliteSaver.from_conn_string(sqlite_url.replace("sqlite:///", ""))

    if clone_from is not None:
        _clone_sqlite(Path(clone_from), Path(sqlite_url.replace("sqlite:///", "")))

    logger.info("checkpointer_sqlite_ready", url=sqlite_url)
    return saver


def _make_memory_checkpointer():
    """Build an in-process MemorySaver checkpointer."""
    from langgraph.checkpoint.memory import MemorySaver

    saver = MemorySaver()
    logger.info("checkpointer_memory_ready")
    return saver


def _clone_sqlite(src: Path, dst: Path) -> None:
    """Copy an SQLite checkpoint file if dst does not yet exist."""
    import shutil

    if src.exists() and not dst.exists():
        shutil.copy2(src, dst)
        logger.info("checkpointer_cloned", from_path=str(src), to_path=str(dst))


def get_checkpoint_dir() -> Path | None:
    """Return the checkpoint directory path, or None if not yet initialised."""
    return _CHECKPOINT_DIR


def reset_checkpointer() -> None:
    """Clear the module-level singleton — useful in tests only."""
    global _SAVER, _CHECKPOINT_DIR
    _SAVER = None
    _CHECKPOINT_DIR = None
