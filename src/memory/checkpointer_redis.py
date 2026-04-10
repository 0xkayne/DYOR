"""Redis-based checkpointer wrapper for LangGraph checkpoint persistence.

Provides an async Redis checkpointer with TTL support for session state
survival across service restarts. Wraps langgraph.checkpoint.redis.RedisSaver.

Requires langgraph>=0.4.0 or langgraph[redis] extra.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

_instance: "RedisSaver | None" = None

try:
    from langgraph.checkpoint.redis import RedisSaver
except ImportError:
    RedisSaver = None  # type: ignore[assignment,misc]


def get_redis_checkpointer(
    redis_url: str = "redis://localhost:6379/0",
    ttl_seconds: int = 604800,
) -> "RedisSaver":
    """Return a singleton RedisSaver instance.

    Creates the instance on first call and returns the same
    instance on subsequent calls. The TTL configures automatic
    expiration of checkpoint data.

    Args:
        redis_url: Redis connection URL in format redis://host:port/db.
        ttl_seconds: Time-to-live for checkpoint data in seconds.
            Defaults to 7 days (604800).

    Returns:
        A RedisSaver instance for LangGraph checkpointing.

    Raises:
        ImportError: If langgraph.checkpoint.redis is not available
            (requires langgraph>=0.4.0).
    """
    global _instance
    if _instance is None:
        if RedisSaver is None:
            raise ImportError(
                "RedisSaver requires langgraph>=0.4.0. "
                "Install with: pip install 'langgraph[redis]'"
            )
        logger.info("creating_redis_checkpointer", redis_url=redis_url, ttl_seconds=ttl_seconds)
        _instance = RedisSaver.from_url(
            redis_url,
            ttl=ttl_seconds,
        )
    return _instance
