"""Postgres-based checkpointer wrapper for LangGraph checkpoint persistence.

Provides durable cold storage for session checkpoints using PostgreSQL.
Wraps langgraph.checkpoint.postgres.PostgresSaver with async support.

Requires langgraph>=0.4.0 or langgraph[postgres] extra.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

_instance: "PostgresSaver | None" = None

try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    PostgresSaver = None  # type: ignore[assignment,misc]


async def get_postgres_checkpointer(
    conn_string: str,
) -> "PostgresSaver":
    """Return a singleton PostgresSaver instance.

    Creates the instance on first call and returns the same
    instance on subsequent calls. Uses async connection for
    non-blocking operations.

    Args:
        conn_string: PostgreSQL connection string in format:
            postgresql://user:pass@host:port/dbname

    Returns:
        A PostgresSaver instance for LangGraph checkpointing.

    Raises:
        ImportError: If langgraph.checkpoint.postgres is not available
            (requires langgraph>=0.4.0).
    """
    global _instance
    if _instance is None:
        if PostgresSaver is None:
            raise ImportError(
                "PostgresSaver requires langgraph>=0.4.0. "
                "Install with: pip install 'langgraph[postgres]'"
            )
        logger.info("creating_postgres_checkpointer", conn_string=conn_string[:20] + "...")
        _instance = PostgresSaver.from_conn_string(conn_string)
    return _instance
