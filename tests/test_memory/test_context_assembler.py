"""Tests for the ContextAssembler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from src.memory.selector.context_assembler import ContextAssembler
from src.memory.selector.recall import SimilarityRecall
from src.memory.selector.summarizer import Summarizer


class TestContextAssembler:
    """Tests for the ContextAssembler pipeline."""

    @pytest.fixture
    def mock_checkpointer(self):
        """Mock checkpointer returning sample checkpoint."""
        mock = AsyncMock()
        mock.aget.return_value = {
            "channel_values": {
                "messages": [
                    SystemMessage(content="System"),
                    HumanMessage(content="Query 1"),
                    HumanMessage(content="Query 2"),
                    HumanMessage(content="Query 3"),
                    HumanMessage(content="Query 4"),
                    HumanMessage(content="Query 5"),
                    HumanMessage(content="Query 6"),
                    HumanMessage(content="Query 7"),
                    HumanMessage(content="Query 8"),
                    HumanMessage(content="Query 9"),
                    HumanMessage(content="Query 10"),
                    HumanMessage(content="Query 11"),
                ]
            }
        }
        return mock

    @pytest.mark.asyncio
    async def test_assemble_no_checkpoint(self):
        """Handles missing checkpointer gracefully."""
        mock_summarizer = Summarizer(threshold=100)
        mock_recall = SimilarityRecall(top_k=3)
        mock_recall.retrieve = AsyncMock(return_value=[])

        assembler = ContextAssembler(
            checkpointer=None,
            summarizer=mock_summarizer,
            recall=mock_recall,
            max_context_messages=20,
        )

        result = await assembler.assemble("thread-1", "What is Ethereum?")

        assert result["messages"] == []
        assert result["has_recall"] is False
        assert result["is_summarized"] is False

    @pytest.mark.asyncio
    async def test_assemble_below_threshold_no_summarize(self, mock_checkpointer):
        """Messages below threshold are not summarized."""
        mock_summarizer = Summarizer(threshold=20)
        mock_recall = SimilarityRecall(top_k=3)
        mock_recall.retrieve = AsyncMock(return_value=[])

        assembler = ContextAssembler(
            checkpointer=mock_checkpointer,
            summarizer=mock_summarizer,
            recall=mock_recall,
            max_context_messages=20,
        )

        result = await assembler.assemble("thread-1", "What is Ethereum?")

        assert result["is_summarized"] is False
        assert len(result["messages"]) == 11

    @pytest.mark.asyncio
    async def test_assemble_above_threshold_summarizes(self, mock_checkpointer):
        """Messages above threshold trigger summarization."""
        mock_summarizer = Summarizer(threshold=5)
        mock_summarizer.compress = AsyncMock(
            return_value=[
                SystemMessage(content="Prior summary: User asked about DeFi."),
                HumanMessage(content="Query 9"),
                HumanMessage(content="Query 10"),
                HumanMessage(content="Query 11"),
            ]
        )
        mock_recall = SimilarityRecall(top_k=3)
        mock_recall.retrieve = AsyncMock(return_value=[])

        assembler = ContextAssembler(
            checkpointer=mock_checkpointer,
            summarizer=mock_summarizer,
            recall=mock_recall,
            max_context_messages=20,
        )

        result = await assembler.assemble("thread-1", "What is Ethereum?")

        assert result["is_summarized"] is True
        assert isinstance(result["messages"][0], SystemMessage)
        assert "Prior conversation summary:" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_assemble_injects_recall_as_system_message(self, mock_checkpointer):
        """Similarity recall snippets are injected at position 0."""
        mock_summarizer = Summarizer(threshold=20)
        mock_recall = SimilarityRecall(top_k=3)
        mock_recall.retrieve = AsyncMock(
            return_value=[
                "[Session abc]: Ethereum analysis from yesterday",
                "[Session def]: SOL DeFi comparison",
            ]
        )

        assembler = ContextAssembler(
            checkpointer=mock_checkpointer,
            summarizer=mock_summarizer,
            recall=mock_recall,
            max_context_messages=20,
        )

        result = await assembler.assemble("thread-1", "What about ETH?")

        assert result["has_recall"] is True
        assert isinstance(result["messages"][0], SystemMessage)
        assert "Prior relevant sessions:" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_assemble_truncates_to_max_messages(self):
        """Messages are truncated to max_context_messages."""
        mock_cp = AsyncMock()
        many_messages = [
            SystemMessage(content="System"),
        ] + [
            HumanMessage(content=f"Query {i}") for i in range(30)
        ]
        mock_cp.aget.return_value = {
            "channel_values": {"messages": many_messages}
        }

        mock_summarizer = Summarizer(threshold=100)
        mock_recall = SimilarityRecall(top_k=3)
        mock_recall.retrieve = AsyncMock(return_value=[])

        assembler = ContextAssembler(
            checkpointer=mock_cp,
            summarizer=mock_summarizer,
            recall=mock_recall,
            max_context_messages=10,
        )

        result = await assembler.assemble("thread-1", "What?")

        # Last 10 messages + potential recall (not in this case)
        assert len(result["messages"]) == 10

    @pytest.mark.asyncio
    async def test_assemble_token_estimate(self):
        """Token count estimate is calculated."""
        mock_cp = AsyncMock()
        mock_cp.aget.return_value = {
            "channel_values": {
                "messages": [
                    SystemMessage(content="A" * 400),
                    HumanMessage(content="B" * 400),
                ]
            }
        }

        assembler = ContextAssembler(
            checkpointer=mock_cp,
            max_context_messages=20,
        )

        result = await assembler.assemble("thread-1", "Query")

        # 400 + 400 = 800 chars // 4 = 200 tokens
        assert result["token_count"] == 200
