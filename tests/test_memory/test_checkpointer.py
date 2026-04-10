"""Tests for the checkpointer module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.memory.checkpointer import get_checkpointer


class TestCheckpointer:
    """Tests for the checkpointer factory."""

    def setup_method(self):
        """Reset singleton before each test."""
        import src.memory.checkpointer as mod
        mod._checkpointer = None

    def test_returns_memory_saver_by_default(self):
        """Default backend returns MemorySaver."""
        from langgraph.checkpoint.memory import MemorySaver

        cp = get_checkpointer()
        assert isinstance(cp, MemorySaver)

    def test_singleton_pattern(self):
        """Same instance returned on repeated calls."""
        cp1 = get_checkpointer()
        cp2 = get_checkpointer()
        assert cp1 is cp2

    def test_memory_backend_explicit(self):
        """MEMORY backend returns MemorySaver."""
        from langgraph.checkpoint.memory import MemorySaver
        from src.memory.enums import CheckpointerBackend

        cp = get_checkpointer(backend=CheckpointerBackend.MEMORY)
        assert isinstance(cp, MemorySaver)

    def test_redis_backend_when_configured(self):
        """REDIS backend returns RedisSaver when REDIS_URL is set."""
        mock_instance = MagicMock()
        with patch("src.memory.checkpointer.get_redis_checkpointer") as mock_fn:
            mock_fn.return_value = mock_instance
            with patch("src.memory.checkpointer._get_settings") as mock_settings:
                mock_settings.return_value.redis_url = "redis://localhost:6379/0"
                mock_settings.return_value.redis_ttl_seconds = 604800
                mock_settings.return_value.checkpointer_backend = "redis"

                import src.memory.checkpointer as mod
                mod._checkpointer = None

                cp = get_checkpointer(backend=mod.CheckpointerBackend.REDIS)
                assert cp is mock_instance

    def test_parse_backend_invalid_value_defaults_to_memory(self):
        """Invalid backend string falls back to MemorySaver."""
        from langgraph.checkpoint.memory import MemorySaver
        from src.memory.checkpointer import _parse_backend

        result = _parse_backend("invalid_backend")
        assert result.value == "memory"
