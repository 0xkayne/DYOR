"""Tests for the Redis checkpointer module."""

from __future__ import annotations

import pytest

# RedisSaver is available in langgraph>=0.4.0
# If not available, skip the module
pytest.importorskip("langgraph.checkpoint.redis", reason="RedisSaver requires langgraph>=0.4.0")

from unittest.mock import MagicMock, patch

from src.memory.checkpointer_redis import get_redis_checkpointer


class TestRedisCheckpointer:
    """Tests for RedisSaver checkpointer factory."""

    def setup_method(self):
        """Reset singleton before each test."""
        import src.memory.checkpointer_redis as mod
        mod._instance = None

    def test_singleton_pattern(self):
        """Same instance returned on repeated calls."""
        with patch("src.memory.checkpointer_redis.RedisSaver") as mock_saver:
            mock_instance = MagicMock()
            mock_saver.from_url.return_value = mock_instance

            cp1 = get_redis_checkpointer()
            cp2 = get_redis_checkpointer()

            assert cp1 is cp2
            assert mock_saver.from_url.call_count == 1

    def test_redis_url_passed_correctly(self):
        """Redis URL is passed to RedisSaver.from_url."""
        with patch("src.memory.checkpointer_redis.RedisSaver") as mock_saver:
            mock_instance = MagicMock()
            mock_saver.from_url.return_value = mock_instance

            cp = get_redis_checkpointer(
                redis_url="redis://custom:6380/5",
                ttl_seconds=3600,
            )

            mock_saver.from_url.assert_called_once_with(
                "redis://custom:6380/5",
                ttl=3600,
            )

    def test_default_ttl(self):
        """Default TTL of 7 days is used."""
        with patch("src.memory.checkpointer_redis.RedisSaver") as mock_saver:
            mock_instance = MagicMock()
            mock_saver.from_url.return_value = mock_instance

            get_redis_checkpointer()

            call_kwargs = mock_saver.from_url.call_args
            assert call_kwargs[1]["ttl"] == 604800
