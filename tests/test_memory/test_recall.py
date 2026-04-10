"""Tests for the SimilarityRecall memory selector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.memory.selector.recall import SimilarityRecall


class TestSimilarityRecall:
    """Tests for the SimilarityRecall class."""

    def test_top_k_property(self):
        """top_k returns the configured value."""
        recall = SimilarityRecall(top_k=5)
        assert recall.top_k == 5

    def test_default_top_k_from_settings(self):
        """Default top_k comes from settings."""
        with patch("src.memory.selector.recall.settings") as mock_settings:
            mock_settings.similarity_top_k = 7
            recall = SimilarityRecall()
            assert recall.top_k == 7

    @pytest.mark.asyncio
    async def test_empty_collection_returns_empty(self):
        """Empty ChromaDB collection returns empty list."""
        recall = SimilarityRecall()

        with patch.object(recall, "_get_collection") as mock_coll:
            mock_collection = MagicMock()
            mock_collection.count.return_value = 0
            mock_coll.return_value = mock_collection

            result = await recall.retrieve(
                query="What about Ethereum?",
                exclude_thread_id="thread-123",
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_returns_top_k_above_threshold(self):
        """Only results above similarity threshold are returned."""
        recall = SimilarityRecall(top_k=2, similarity_threshold=0.6)

        with patch.object(recall, "_get_collection") as mock_coll:
            with patch.object(recall, "_get_embedder") as mock_embed:
                mock_embed.return_value.embed_query.return_value = [0.1] * 768

                mock_collection = MagicMock()
                mock_collection.count.return_value = 3
                mock_collection.query.return_value = {
                    "documents": [["Session A content"], ["Session B content"], ["Session C content"]],
                    "metadatas": [[{"thread_id": "thread-A"}, {"thread_id": "thread-B"}, {"thread_id": "thread-C"}]],
                    "distances": [[0.3, 0.5, 0.9]],  # cosine distances
                }
                mock_coll.return_value = mock_collection

                result = await recall.retrieve(
                    query="Ethereum analysis",
                    exclude_thread_id="thread-X",
                )

                # similarity = 1 - 0.3/2 = 0.85 >= 0.6 ✓
                # similarity = 1 - 0.5/2 = 0.75 >= 0.6 ✓
                # similarity = 1 - 0.9/2 = 0.55 < 0.6 ✗
                assert len(result) == 2
                assert "thread-A" in result[0] or "thread-B" in result[1]
                assert "thread-C" not in str(result)

    @pytest.mark.asyncio
    async def test_excludes_current_thread(self):
        """Current thread_id is excluded from results."""
        recall = SimilarityRecall(top_k=3)

        with patch.object(recall, "_get_collection") as mock_coll:
            with patch.object(recall, "_get_embedder") as mock_embed:
                mock_embed.return_value.embed_query.return_value = [0.1] * 768

                mock_collection = MagicMock()
                mock_collection.count.return_value = 1
                mock_collection.query.return_value = {
                    "documents": [["Session for current thread"]],
                    "metadatas": [[{"thread_id": "thread-123"}]],
                    "distances": [[0.1]],
                }
                mock_coll.return_value = mock_collection

                # Query excluding thread-123
                result = await recall.retrieve(
                    query="analysis",
                    exclude_thread_id="thread-123",
                )

                # The where filter should have been called with $ne
                call_kwargs = mock_collection.query.call_args
                assert call_kwargs[1]["where"] == {"thread_id": {"$ne": "thread-123"}}

    @pytest.mark.asyncio
    async def test_chroma_error_returns_empty_list(self):
        """ChromaDB error returns empty list gracefully."""
        recall = SimilarityRecall()

        with patch.object(recall, "_get_collection") as mock_coll:
            mock_coll.side_effect = Exception("ChromaDB unavailable")

            result = await recall.retrieve(
                query="Ethereum",
                exclude_thread_id="thread-123",
            )

            assert result == []
