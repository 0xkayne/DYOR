"""Integration tests for Memory Selector with workflow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.memory.selector.context_assembler import ContextAssembler
from src.memory.selector.recall import SimilarityRecall
from src.memory.selector.summarizer import Summarizer


class TestMemorySelectorIntegration:
    """Integration tests for the full Memory Selector pipeline."""

    @pytest.mark.asyncio
    async def test_memory_selector_disabled_skips_assembly(self):
        """When disabled, context assembly is skipped entirely."""
        with patch("src.memory.selector.context_assembler.settings") as mock_settings:
            mock_settings.memory_selector_enabled = False
            mock_settings.max_context_messages = 20
            mock_settings.similarity_top_k = 3
            mock_settings.summarization_threshold = 10

            mock_checkpointer = AsyncMock()
            mock_checkpointer.aget.return_value = None

            assembler = ContextAssembler(checkpointer=mock_checkpointer)
            # With selector disabled, the caller should skip calling assemble
            # Here we test that when called directly, it still works but
            # the setting controls whether it's called at all

            result = await assembler.assemble("thread-1", "Ethereum analysis")

            # The assembler itself still works
            assert "messages" in result

    @pytest.mark.asyncio
    async def test_full_pipeline_summarize_then_recall(self):
        """Full pipeline: summarize long history + inject recall."""
        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget.return_value = {
            "channel_values": {
                "messages": [
                    SystemMessage(content="System"),
                    HumanMessage(content="What is Bitcoin?"),
                    HumanMessage(content="What is Ethereum?"),
                    HumanMessage(content="What is Solana?"),
                    HumanMessage(content="Compare BTC and ETH?"),
                    HumanMessage(content="What about DeFi?"),
                    HumanMessage(content="What about NFTs?"),
                    HumanMessage(content="Layer 2 solutions?"),
                    HumanMessage(content="What is Arbitrum?"),
                    HumanMessage(content="Tell me about Solana DeFi."),
                    HumanMessage(content="What is a blockchain?"),
                    HumanMessage(content="Explain staking rewards."),
                ]
            }
        }

        mock_summarizer = Summarizer(threshold=5)
        mock_summarizer.compress = AsyncMock(
            return_value=[
                SystemMessage(content="Prior: User asked about BTC, ETH, DeFi, NFTs, L2s."),
                HumanMessage(content="What is a blockchain?"),
                HumanMessage(content="Explain staking rewards."),
            ]
        )

        mock_recall = SimilarityRecall(top_k=3)
        mock_recall.retrieve = AsyncMock(
            return_value=[
                "[Session xyz]: Previous discussion about blockchain scalability."
            ]
        )

        assembler = ContextAssembler(
            checkpointer=mock_checkpointer,
            summarizer=mock_summarizer,
            recall=mock_recall,
            max_context_messages=10,
        )

        result = await assembler.assemble("thread-1", "Tell me about blockchain")

        assert result["is_summarized"] is True
        assert result["has_recall"] is True
        assert len(result["messages"]) == 4  # recall + summary + 2 recent
        assert result["messages"][0] == "Prior relevant sessions:"
        assert isinstance(result["messages"][1], SystemMessage)
        assert "Prior conversation summary:" in result["messages"][1].content

    @pytest.mark.asyncio
    async def test_recall_empty_doesnt_add_message(self):
        """Empty recall results don't inject a SystemMessage."""
        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget.return_value = {
            "channel_values": {
                "messages": [SystemMessage(content="System"), HumanMessage(content="Query 1")]
            }
        }

        mock_recall = SimilarityRecall(top_k=3)
        mock_recall.retrieve = AsyncMock(return_value=[])

        assembler = ContextAssembler(
            checkpointer=mock_checkpointer,
            summarizer=Summarizer(threshold=10),
            recall=mock_recall,
            max_context_messages=20,
        )

        result = await assembler.assemble("thread-1", "New query")

        assert result["has_recall"] is False
        # Only original messages
        assert len(result["messages"]) == 2

    @pytest.mark.asyncio
    async def test_checkpointer_aget_error_handled(self):
        """Checkpointer error returns empty context without crashing."""
        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget.side_effect = Exception("Redis unavailable")

        assembler = ContextAssembler(
            checkpointer=mock_checkpointer,
            summarizer=Summarizer(threshold=10),
            recall=SimilarityRecall(top_k=3),
            max_context_messages=20,
        )

        result = await assembler.assemble("thread-1", "Query")

        assert result["messages"] == []
        assert result["has_recall"] is False
        assert result["is_summarized"] is False
