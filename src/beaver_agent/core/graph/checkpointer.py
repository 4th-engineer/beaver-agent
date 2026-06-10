"""SQLite-backed LangGraph checkpointer — replaces the JSON-file Inbox."""

from __future__ import annotations

from pathlib import Path

import structlog
from langgraph.checkpoint.serde.sqlite import SqliteSaver

logger = structlog.get_logger(__name__)

# Module-level singleton — created once, reused across all graph runs.
_SERDE: SqliteSaver | None = None
_CHECKPOINT_DIR: Path | None = None


def get_checkpointer(
    checkpoint_dir: Path | None = None,
    *,
    clone_from: Path | None = None,
) -> SqliteSaver:
    """Return a (singleton) SQLite checkpointer for the Beaver Agent graph.

    Args:
        checkpoint_dir: Directory that holds the SQLite file.
                       Defaults to ``~/.beaver/checkpoints/``.
        clone_from:     If given, copy an existing checkpoint store from this path
                       before starting. Useful for rehydrating state across restarts.
                       (The clone is performed once at first call; subsequent calls
                       return the existing singleton.)

    Returns:
        A ``SqliteSaver`` instance wired to ``checkpoints.sqlite``.
    """
    global _SERDE, _CHECKPOINT_DIR

    if _SERDE is not None:
        return _SERDE

    if checkpoint_dir is None:
        checkpoint_dir = Path.home() / ".beaver" / "checkpoints"

    checkpoint_dir = checkpoint_dir.resolve()
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    db_path = checkpoint_dir / "checkpoints.sqlite"

    # Clone-once semantics
    if clone_from is not None and not db_path.exists():
        import shutil

        src = Path(clone_from)
        if src.exists():
            shutil.copy2(src, db_path)
            logger.info("checkpointer_cloned", from_path=str(src), to_path=str(db_path))

    _SERDE = SqliteSaver.from_conn_string(str(db_path))
    _CHECKPOINT_DIR = checkpoint_dir

    logger.info(
        "checkpointer_ready",
        db_path=str(db_path),
        checkpoint_dir=str(checkpoint_dir),
    )
    return _SERDE


def get_checkpoint_dir() -> Path | None:
    """Return the checkpoint directory path, or None if not yet initialised."""
    return _CHECKPOINT_DIR


def reset_checkpointer() -> None:
    """Clear the module-level singleton — useful in tests only."""
    global _SERDE, _CHECKPOINT_DIR
    _SERDE = None
    _CHECKPOINT_DIR = None
