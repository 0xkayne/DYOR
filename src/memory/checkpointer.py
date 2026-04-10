"""LangGraph checkpoint persistence for conversation state.

Provides configurable checkpoint backends:
- MEMORY: In-memory (MemorySaver), lost on restart
- REDIS: Redis with TTL, fast hot storage
- POSTGRES: PostgreSQL, durable cold storage
- REDIS_THEN_POSTGRES: Dual-layer with Redis primary, Postgres fallback

The factory returns a singleton instance based on configuration.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.memory.enums import CheckpointerBackend

logger = structlog.get_logger(__name__)

_settings: Any = None


def _get_settings() -> Any:
    global _settings
    if _settings is None:
        from src.config import settings as s
        _settings = s
    return _settings


def _parse_backend(value: str) -> CheckpointerBackend:
    """Parse a string value into CheckpointerBackend enum."""
    try:
        return CheckpointerBackend(value)
    except ValueError:
        return CheckpointerBackend.MEMORY


class RedisThenPostgresSaver(BaseCheckpointSaver):
    """Dual-layer checkpointer: writes to both Redis and Postgres, reads from Redis first.

    Write operations: both backends are updated simultaneously via asyncio.gather.
    Read operations: Redis is tried first; on miss/exception, Postgres is queried
    and the result is re-populated in Redis cache.
    """

    def __init__(
        self,
        redis_saver: BaseCheckpointSaver,
        postgres_saver: BaseCheckpointSaver,
    ) -> None:
        """Initialize the dual-layer checkpointer.

        Args:
            redis_saver: The Redis-backed checkpointer (hot storage).
            postgres_saver: The Postgres-backed checkpointer (cold storage).
        """
        self.redis_saver = redis_saver
        self.postgres_saver = postgres_saver

    async def aput(
        self,
        config: dict,
        checkpoint: dict,
        new_versions: dict | None = None,
    ) -> None:
        """Write checkpoint to both Redis and Postgres simultaneously."""
        await asyncio.gather(
            self.redis_saver.aput(config, checkpoint, new_versions),
            self.postgres_saver.aput(config, checkpoint, new_versions),
        )
        logger.debug(
            "dual_checkpointer_write",
            thread_id=config.get("configurable", {}).get("thread_id"),
        )

    async def aget(self, config: dict) -> dict | None:
        """Read checkpoint: try Redis first, fallback to Postgres."""
        try:
            result = await self.redis_saver.aget(config)
            if result is not None:
                return result
        except Exception as exc:
            logger.warning("redis_checkpointer_miss", error=str(exc))

        # Fallback to Postgres
        try:
            result = await self.postgres_saver.aget(config)
            if result is not None:
                await self.redis_saver.aput(config, result, None)
                logger.info(
                    "postgres_fallback_triggered",
                    thread_id=config.get("configurable", {}).get("thread_id"),
                )
            return result
        except Exception as exc:
            logger.error("postgres_checkpointer_error", error=str(exc))
            return None

    async def aget_next_version(
        self,
        current_version: str | None,
        config: dict,
    ) -> str | None:
        """Delegate to Redis saver for version tracking."""
        return await self.redis_saver.aget_next_version(current_version, config)

    async def alist(
        self,
        config: dict | None = None,
        limit: int | None = None,
        before: dict | None = None,
        after: dict | None = None,
    ) -> list[dict]:
        """List checkpoints: try Redis first, fallback to Postgres."""
        try:
            results = await self.redis_saver.alist(config, limit, before, after)
            if results:
                return results
        except Exception as exc:
            logger.warning("redis_list_miss", error=str(exc))

        return await self.postgres_saver.alist(config, limit, before, after)


_checkpointer: BaseCheckpointSaver | None = None


def get_checkpointer(
    backend: CheckpointerBackend | None = None,
) -> BaseCheckpointSaver:
    """Return a singleton checkpointer instance based on configuration.

    If backend is None, reads from settings.checkpointer_backend.
    For REDIS_THEN_POSTGRES mode, returns a dual-layer checkpointer
    that writes to both stores and reads from Redis first.

    Args:
        backend: Optional backend override. Defaults to settings.checkpointer_backend.

    Returns:
        A singleton checkpointer instance.
    """
    global _checkpointer

    if backend is None:
        settings = _get_settings()
        backend = _parse_backend(settings.checkpointer_backend)

    if _checkpointer is not None:
        return _checkpointer

    if backend == CheckpointerBackend.REDIS:
        from src.memory.checkpointer_redis import get_redis_checkpointer

        settings = _get_settings()
        redis_checkpointer = get_redis_checkpointer(
            redis_url=settings.redis_url,
            ttl_seconds=settings.redis_ttl_seconds,
        )
        _checkpointer = redis_checkpointer
        logger.info("checkpointer_initialized", backend="redis")

    elif backend == CheckpointerBackend.POSTGRES:
        logger.warning("postgres_sync_init_falling_back_to_memory")
        _checkpointer = MemorySaver()
        logger.info("checkpointer_initialized", backend="memory")

    elif backend == CheckpointerBackend.REDIS_THEN_POSTGRES:
        from src.memory.checkpointer_redis import get_redis_checkpointer

        settings = _get_settings()
        redis_checkpointer = get_redis_checkpointer(
            redis_url=settings.redis_url,
            ttl_seconds=settings.redis_ttl_seconds,
        )

        if settings.postgres_conn_string:
            from src.memory.checkpointer_postgres import get_postgres_checkpointer

            _postgres_coro = get_postgres_checkpointer(settings.postgres_conn_string)
            _checkpointer = _LazyDualLayerCheckpointer(
                redis_saver=redis_checkpointer,
                postgres_coro=_postgres_coro,
            )
            logger.info("checkpointer_initialized", backend="redis_then_postgres")
        else:
            logger.warning("postgres_not_configured_falling_back_to_redis")
            _checkpointer = redis_checkpointer

    else:  # MEMORY or default
        _checkpointer = MemorySaver()
        logger.info("checkpointer_initialized", backend="memory")

    return _checkpointer


class _LazyDualLayerCheckpointer(BaseCheckpointSaver):
    """Dual-layer checkpointer with lazy Postgres initialization.

    PostgresSaver is async but the factory is sync; this class
    resolves the Postgres checkpointer on first write/read.
    """

    def __init__(
        self,
        redis_saver: BaseCheckpointSaver,
        postgres_coro: Any,
    ) -> None:
        self.redis_saver = redis_saver
        self.postgres_coro = postgres_coro
        self._postgres_saver: BaseCheckpointSaver | None = None
        self._postgres_resolved: bool = False

    async def _get_postgres(self) -> BaseCheckpointSaver:
        if not self._postgres_resolved:
            self._postgres_saver = await self.postgres_coro
            self._postgres_resolved = True
        return self._postgres_saver

    async def aput(
        self,
        config: dict,
        checkpoint: dict,
        new_versions: dict | None = None,
    ) -> None:
        pg = await self._get_postgres()
        await asyncio.gather(
            self.redis_saver.aput(config, checkpoint, new_versions),
            pg.aput(config, checkpoint, new_versions),
        )
        logger.debug(
            "dual_checkpointer_write",
            thread_id=config.get("configurable", {}).get("thread_id"),
        )

    async def aget(self, config: dict) -> dict | None:
        try:
            result = await self.redis_saver.aget(config)
            if result is not None:
                return result
        except Exception as exc:
            logger.warning("redis_checkpointer_miss", error=str(exc))

        pg = await self._get_postgres()
        try:
            result = await pg.aget(config)
            if result is not None:
                await self.redis_saver.aput(config, result, None)
                logger.info(
                    "postgres_fallback_triggered",
                    thread_id=config.get("configurable", {}).get("thread_id"),
                )
            return result
        except Exception as exc:
            logger.error("postgres_checkpointer_error", error=str(exc))
            return None

    async def aget_next_version(
        self,
        current_version: str | None,
        config: dict,
    ) -> str | None:
        return await self.redis_saver.aget_next_version(current_version, config)

    async def alist(
        self,
        config: dict | None = None,
        limit: int | None = None,
        before: dict | None = None,
        after: dict | None = None,
    ) -> list[dict]:
        try:
            results = await self.redis_saver.alist(config, limit, before, after)
            if results:
                return results
        except Exception as exc:
            logger.warning("redis_list_miss", error=str(exc))

        pg = await self._get_postgres()
        return await pg.alist(config, limit, before, after)
