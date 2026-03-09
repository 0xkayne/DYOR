"""Tests for the agentic retriever with hybrid search and reranking."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.rag.retriever import (
    AgenticRetriever,
    QueryType,
    RetrievalResult,
    _tokenize_chinese,
)


class TestTokenizeChinese:
    def test_chinese_text(self):
        tokens = _tokenize_chinese("Arbitrum 的技术分析")
        assert len(tokens) > 0
        # Stopword "的" should be filtered
        assert "的" not in tokens

    def test_stopword_filtering(self):
        tokens = _tokenize_chinese("这是什么")
        # 这, 是, 什么 are all stopwords
        assert len(tokens) == 0 or all(t not in {"这", "是", "什么"} for t in tokens)

    def test_english_text(self):
        tokens = _tokenize_chinese("Arbitrum Layer2 Rollup")
        assert len(tokens) > 0
        assert any("arbitrum" in t for t in tokens)

    def test_empty_string(self):
        tokens = _tokenize_chinese("")
        assert tokens == []


class TestClassifyQuery:
    def setup_method(self):
        with patch("src.rag.retriever.BGEEmbeddings"), \
             patch("src.rag.retriever.VectorStore"):
            self.retriever = AgenticRetriever()

    def test_greeting_direct_answer(self):
        assert self.retriever._classify_query("你好") == QueryType.DIRECT_ANSWER
        assert self.retriever._classify_query("hello") == QueryType.DIRECT_ANSWER
        assert self.retriever._classify_query("Hi") == QueryType.DIRECT_ANSWER

    def test_comparison_decomposition(self):
        assert self.retriever._classify_query("ARB 和 OP 的对比") == QueryType.NEEDS_DECOMPOSITION
        result = self.retriever._classify_query("Arbitrum vs Optimism")
        assert result == QueryType.NEEDS_DECOMPOSITION
        assert self.retriever._classify_query("比较 ARB 和 OP") == QueryType.NEEDS_DECOMPOSITION

    def test_normal_retrieval(self):
        assert self.retriever._classify_query("Arbitrum 的团队背景") == QueryType.NEEDS_RETRIEVAL
        assert self.retriever._classify_query("ARB 代币经济学") == QueryType.NEEDS_RETRIEVAL


class TestDecomposeQuery:
    def setup_method(self):
        with patch("src.rag.retriever.BGEEmbeddings"), \
             patch("src.rag.retriever.VectorStore"):
            self.retriever = AgenticRetriever()

    def test_comparison_splits(self):
        subs = self.retriever._decompose_query("ARB和OP的对比")
        assert len(subs) >= 2
        # Should contain sub-queries for each entity
        assert any("ARB" in s for s in subs)
        assert any("OP" in s for s in subs)

    def test_normal_query_unchanged(self):
        subs = self.retriever._decompose_query("Arbitrum 的团队背景")
        assert len(subs) == 1
        assert subs[0] == "Arbitrum 的团队背景"

    def test_max_four(self):
        subs = self.retriever._decompose_query("ARB与OP的比较")
        assert len(subs) <= 4


class TestReciprocalRankFusion:
    def setup_method(self):
        with patch("src.rag.retriever.BGEEmbeddings"), \
             patch("src.rag.retriever.VectorStore"):
            self.retriever = AgenticRetriever()

    def _make_doc(
        self, content: str, source: str, chunk_index: int, score: float = 0.5,
    ) -> Document:
        return Document(
            page_content=content,
            metadata={"source": source, "chunk_index": chunk_index, "score": score},
        )

    def test_merge_two_lists(self):
        dense = [self._make_doc("A", "a.md", 0), self._make_doc("B", "b.md", 0)]
        sparse = [self._make_doc("C", "c.md", 0), self._make_doc("D", "d.md", 0)]
        result = self.retriever._reciprocal_rank_fusion(dense, sparse)
        assert len(result) == 4

    def test_overlapping_docs_higher_score(self):
        doc_shared = self._make_doc("Shared", "shared.md", 0)
        dense = [doc_shared, self._make_doc("B", "b.md", 0)]
        sparse = [self._make_doc("C", "c.md", 0), self._make_doc("Shared copy", "shared.md", 0)]
        result = self.retriever._reciprocal_rank_fusion(dense, sparse)
        # shared.md_0 appears in both lists, should have highest RRF score
        scores = {
            f"{d.metadata['source']}_{d.metadata['chunk_index']}": d.metadata["rrf_score"]
            for d in result
        }
        assert scores["shared.md_0"] > scores.get("b.md_0", 0)
        assert scores["shared.md_0"] > scores.get("c.md_0", 0)

    def test_empty_input(self):
        result = self.retriever._reciprocal_rank_fusion([], [])
        assert result == []


class TestRerank:
    def setup_method(self):
        with patch("src.rag.retriever.BGEEmbeddings"), \
             patch("src.rag.retriever.VectorStore"):
            self.retriever = AgenticRetriever()

    def test_rerank_top_k_truncation(self):
        docs = [
            Document(page_content=f"doc {i}", metadata={"source": f"{i}.md", "chunk_index": 0})
            for i in range(5)
        ]
        mock_ranker = MagicMock()
        mock_ranker.rerank.return_value = [
            {
                "text": f"doc {i}", "score": 0.9 - i * 0.1,
                "meta": {"source": f"{i}.md", "chunk_index": 0},
            }
            for i in range(5)
        ]
        # Set _ranker so the property returns it without loading
        self.retriever._ranker = mock_ranker

        result = self.retriever._rerank("test query", docs, top_k=3)
        assert len(result) == 3

    def test_rerank_sets_score(self):
        docs = [Document(page_content="doc", metadata={"source": "a.md", "chunk_index": 0})]
        mock_ranker = MagicMock()
        mock_ranker.rerank.return_value = [
            {"text": "doc", "score": 0.95, "meta": {"source": "a.md", "chunk_index": 0}}
        ]
        self.retriever._ranker = mock_ranker

        result = self.retriever._rerank("query", docs, top_k=1)
        assert result[0].metadata["score"] == 0.95
        assert result[0].metadata["rerank_score"] == 0.95

    def test_rerank_empty_docs(self):
        result = self.retriever._rerank("query", [], top_k=3)
        assert result == []


class TestCheckSufficiency:
    def setup_method(self):
        with patch("src.rag.retriever.BGEEmbeddings"), \
             patch("src.rag.retriever.VectorStore"):
            self.retriever = AgenticRetriever()

    def test_high_score_sufficient(self):
        docs = [Document(page_content="good", metadata={"score": 0.8})]
        assert self.retriever._check_sufficiency(docs) is True

    def test_low_score_insufficient(self):
        docs = [Document(page_content="bad", metadata={"score": 0.1})]
        assert self.retriever._check_sufficiency(docs) is False

    def test_empty_list_insufficient(self):
        assert self.retriever._check_sufficiency([]) is False


class TestReformulateQuery:
    def setup_method(self):
        with patch("src.rag.retriever.BGEEmbeddings"), \
             patch("src.rag.retriever.VectorStore"):
            self.retriever = AgenticRetriever()

    def test_attempt_1_appends_keywords(self):
        result = self.retriever._reformulate_query("ARB 代币", 1)
        assert "详细分析" in result
        assert "投研报告" in result
        assert "ARB 代币" in result

    def test_attempt_2_simplifies(self):
        result = self.retriever._reformulate_query("Arbitrum 是什么", 2)
        assert "什么" not in result or result != "Arbitrum 是什么"


class TestRetrievePipeline:
    def setup_method(self):
        with patch("src.rag.retriever.BGEEmbeddings"), \
             patch("src.rag.retriever.VectorStore"):
            self.retriever = AgenticRetriever()

    @pytest.mark.asyncio
    async def test_greeting_returns_empty(self):
        result = await self.retriever.retrieve("你好")
        assert result == []

    @pytest.mark.asyncio
    async def test_normal_query_returns_results(self):
        mock_docs = [
            Document(
                page_content=f"Content {i}",
                metadata={
                    "source": f"doc{i}.md", "chunk_index": 0,
                    "project_name": "Test", "score": 0.8 - i * 0.1,
                },
            )
            for i in range(3)
        ]

        self.retriever._dense_search = MagicMock(return_value=mock_docs)
        self.retriever._sparse_search = MagicMock(return_value=[])
        self.retriever._build_bm25_index = MagicMock()

        mock_ranker = MagicMock()
        mock_ranker.rerank.return_value = [
            {"text": f"Content {i}", "score": 0.9 - i * 0.1, "meta": dict(mock_docs[i].metadata)}
            for i in range(3)
        ]
        self.retriever._ranker = mock_ranker

        with patch("src.rag.retriever.graph_rag") as mock_graph_rag:
            mock_graph_rag.find_related = AsyncMock(return_value=[])
            results = await self.retriever.retrieve("Arbitrum 的团队背景")

        assert len(results) > 0
        assert all(isinstance(r, RetrievalResult) for r in results)

    @pytest.mark.asyncio
    async def test_comparison_triggers_decomposition(self):
        mock_docs = [
            Document(
                page_content="Content",
                metadata={
                    "source": "doc.md", "chunk_index": 0,
                    "project_name": "ARB", "score": 0.8,
                },
            )
        ]

        self.retriever._dense_search = MagicMock(return_value=mock_docs)
        self.retriever._sparse_search = MagicMock(return_value=[])

        mock_ranker = MagicMock()
        mock_ranker.rerank.return_value = [
            {"text": "Content", "score": 0.9, "meta": dict(mock_docs[0].metadata)}
        ]
        self.retriever._ranker = mock_ranker

        with patch("src.rag.retriever.graph_rag") as mock_graph_rag:
            mock_graph_rag.find_related = AsyncMock(return_value=[])
            await self.retriever.retrieve("ARB 和 OP 的对比")

        # _dense_search called multiple times (once per sub-query)
        assert self.retriever._dense_search.call_count >= 2

    @pytest.mark.asyncio
    async def test_low_score_triggers_reformulation(self):
        low_score_docs = [
            Document(
                page_content="Low relevance",
                metadata={
                    "source": "doc.md", "chunk_index": 0,
                    "project_name": "Test", "score": 0.1,
                },
            )
        ]

        self.retriever._dense_search = MagicMock(return_value=low_score_docs)
        self.retriever._sparse_search = MagicMock(return_value=[])

        mock_ranker = MagicMock()
        mock_ranker.rerank.return_value = [
            {
                "text": "Low relevance", "score": 0.1,
                "meta": {
                    "source": "doc.md", "chunk_index": 0,
                    "project_name": "Test", "score": 0.1,
                },
            }
        ]
        self.retriever._ranker = mock_ranker

        with patch("src.rag.retriever.graph_rag") as mock_graph_rag:
            mock_graph_rag.find_related = AsyncMock(return_value=[])
            await self.retriever.retrieve("obscure query")

        # Should have called _dense_search more times due to reformulation retries
        assert self.retriever._dense_search.call_count >= 2
