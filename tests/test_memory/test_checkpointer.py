"""Tests for the checkpointer module."""

from __future__ import annotations

from src.memory.checkpointer import get_checkpointer


class TestCheckpointer:
    def test_returns_memory_saver(self):
        from langgraph.checkpoint.memory import MemorySaver
        cp = get_checkpointer()
        assert isinstance(cp, MemorySaver)

    def test_singleton_pattern(self):
        cp1 = get_checkpointer()
        cp2 = get_checkpointer()
        assert cp1 is cp2
