"""Tests for the Postgres checkpointer module."""

from __future__ import annotations

import pytest

# PostgresSaver is available in langgraph>=0.4.0
# If not available, skip the module
pytest.importorskip("langgraph.checkpoint.postgres", reason="PostgresSaver requires langgraph>=0.4.0")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest as pytest2

from src.memory.checkpointer_postgres import get_postgres_checkpointer


class TestPostgresCheckpointer:
    """Tests for PostgresSaver checkpointer factory."""

    @pytest2.mark.asyncio
    async def test_singleton_pattern(self):
        """Same instance returned on repeated calls."""
        with patch("src.memory.checkpointer_postgres.PostgresSaver") as mock_saver:
            mock_instance = MagicMock()
            mock_saver.from_conn_string.return_value = mock_instance

            import src.memory.checkpointer_postgres as mod
            mod._instance = None

            cp1 = await get_postgres_checkpointer("postgresql://user:pass@localhost/dyor")
            cp2 = await get_postgres_checkpointer("postgresql://user:pass@localhost/dyor")

            assert cp1 is cp2
            assert mock_saver.from_conn_string.call_count == 1

    @pytest2.mark.asyncio
    async def test_conn_string_passed_correctly(self):
        """Connection string is passed to PostgresSaver.from_conn_string."""
        with patch("src.memory.checkpointer_postgres.PostgresSaver") as mock_saver:
            mock_instance = MagicMock()
            mock_saver.from_conn_string.return_value = mock_instance

            import src.memory.checkpointer_postgres as mod
            mod._instance = None

            await get_postgres_checkpointer("postgresql://user:secret@pg.example.com:5433/mydb")

            mock_saver.from_conn_string.assert_called_once_with(
                "postgresql://user:secret@pg.example.com:5433/mydb"
            )
