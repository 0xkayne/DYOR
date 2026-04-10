"""Tests for the Summarizer memory selector."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from src.memory.selector.summarizer import Summarizer


class TestSummarizer:
    """Tests for the Summarizer class."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing."""
        mock = MagicMock()
        response = MagicMock()
        response.content = "User discussed Ethereum and Solana DeFi strategies."
        mock.ainvoke = AsyncMock(return_value=response)
        return mock

    def test_below_threshold_returns_unchanged(self):
        """Messages below threshold are returned unchanged."""
        summarizer = Summarizer(threshold=10)
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Hello"),
        ]

        result = summarizer.compress(messages)

        assert len(result) == 2
        assert result[0] == messages[0]
        assert result[1] == messages[1]

    def test_threshold_property(self):
        """Threshold returns the configured value."""
        s = Summarizer(threshold=15)
        assert s.threshold == 15

    def test_default_threshold_from_settings(self):
        """Default threshold comes from settings."""
        with patch("src.memory.selector.summarizer.settings") as mock_settings:
            mock_settings.summarization_threshold = 7
            s = Summarizer()
            assert s.threshold == 7

    @pytest.mark.asyncio
    async def test_above_threshold_generates_summary(self, mock_llm):
        """Messages above threshold trigger LLM summarization."""
        summarizer = Summarizer(threshold=3)
        summarizer._llm = mock_llm

        messages = [
            SystemMessage(content="System prompt"),
            HumanMessage(content="What is Ethereum?"),
            HumanMessage(content="Tell me about Solana."),
            HumanMessage(content="Compare their DeFi ecosystems."),
            HumanMessage(content="What about Layer 2s?"),
        ]

        result = await summarizer.compress(messages)

        # Should have: summary SystemMessage + last 3 messages
        assert len(result) == 4
        assert isinstance(result[0], SystemMessage)
        assert "Prior conversation summary:" in result[0].content
        # Last 3 original messages
        assert result[1].content == "Compare their DeFi ecosystems."
        assert result[2].content == "What about Layer 2s?"
        assert result[3].content == "What about Layer 2s?"  # overlapping

    @pytest.mark.asyncio
    async def test_summarization_failure_fallback(self, mock_llm):
        """LLM failure returns all messages unsummarized."""
        summarizer = Summarizer(threshold=2)
        summarizer._llm = mock_llm
        mock_llm.ainvoke.side_effect = Exception("LLM unavailable")

        messages = [
            SystemMessage(content="System"),
            HumanMessage(content="Query 1"),
            HumanMessage(content="Query 2"),
            HumanMessage(content="Query 3"),
        ]

        result = await summarizer.compress(messages)

        # Falls back to unsummarized
        assert len(result) == 4
