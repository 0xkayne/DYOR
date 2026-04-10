"""Tests for the dual-layer checkpointer (Redis + Postgres)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.memory.checkpointer import RedisThenPostgresSaver


class TestRedisThenPostgresSaver:
    """Tests for the dual-layer checkpointer."""

    @pytest.mark.asyncio
    async def test_dual_write_calls_both_savers(self):
        """aput writes to both Redis and Postgres."""
        mock_redis = AsyncMock()
        mock_pg = AsyncMock()

        dual = RedisThenPostgresSaver(
            redis_saver=mock_redis,
            postgres_saver=mock_pg,
        )

        config = {"configurable": {"thread_id": "test-thread"}}
        checkpoint = {"channel_values": {"messages": []}}

        await dual.aput(config, checkpoint)

        mock_redis.aput.assert_awaited_once_with(config, checkpoint, None)
        mock_pg.aput.assert_awaited_once_with(config, checkpoint, None)

    @pytest.mark.asyncio
    async def test_read_redis_hit_returns_result(self):
        """Redis hit returns result without querying Postgres."""
        mock_redis = AsyncMock()
        mock_pg = AsyncMock()
        mock_redis.aget.return_value = {"channel_values": {"messages": []}}

        dual = RedisThenPostgresSaver(
            redis_saver=mock_redis,
            postgres_saver=mock_pg,
        )

        config = {"configurable": {"thread_id": "test-thread"}}
        result = await dual.aget(config)

        assert result == {"channel_values": {"messages": []}}
        mock_redis.aget.assert_awaited_once()
        mock_pg.aget.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_read_redis_miss_falls_back_to_postgres(self):
        """Redis miss triggers Postgres fallback and re-populates Redis."""
        mock_redis = AsyncMock()
        mock_pg = AsyncMock()
        mock_redis.aget.return_value = None
        mock_pg.aget.return_value = {"channel_values": {"messages": [1, 2, 3]}}

        dual = RedisThenPostgresSaver(
            redis_saver=mock_redis,
            postgres_saver=mock_pg,
        )

        config = {"configurable": {"thread_id": "test-thread"}}
        result = await dual.aget(config)

        assert result == {"channel_values": {"messages": [1, 2, 3]}}
        mock_pg.aget.assert_awaited_once()
        # Redis cache should be re-populated
        mock_redis.aput.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_prefers_redis(self):
        """alist returns Redis results if available."""
        mock_redis = AsyncMock()
        mock_pg = AsyncMock()
        mock_redis.alist.return_value = [{"id": "1"}, {"id": "2"}]

        dual = RedisThenPostgresSaver(
            redis_saver=mock_redis,
            postgres_saver=mock_pg,
        )

        result = await dual.alist(limit=10)

        assert len(result) == 2
        mock_pg.alist.assert_not_awaited()
