"""Advanced retrieval strategies including hybrid search, reranking, and agentic RAG.

Implements a 6-step AgenticRetriever:
1. Query analysis and classification
2. Query decomposition for complex questions
3. Hybrid search (dense + BM25 with jieba tokenization)
4. Graph enhancement (via graph_rag stub)
5. Reranking with flashrank
6. Self-RAG sufficiency check with query reformulation
"""

from __future__ import annotations

import re
from enum import Enum

import jieba
import structlog
from flashrank import Ranker, RerankRequest
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi

from src.config import settings
from src.rag import graph_rag
from src.rag.embeddings import BGEEmbeddings
from src.rag.vectorstore import VectorStore

logger = structlog.get_logger(__name__)

# Chinese stopwords (common function words)
_CHINESE_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
    "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
    "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
    "它", "们", "那", "些", "什么", "怎么", "如何", "为什么", "哪些",
    "可以", "已经", "但是", "而且", "或者", "因为", "所以", "如果",
    "虽然", "还是", "以及", "关于", "对于", "通过", "进行", "使用",
    "其中", "这个", "那个", "这些", "那些",
}


class QueryType(str, Enum):
    """Classification of query complexity."""

    DIRECT_ANSWER = "direct_answer"
    NEEDS_RETRIEVAL = "needs_retrieval"
    NEEDS_DECOMPOSITION = "needs_decomposition"


class RetrievalResult(BaseModel):
    """A single retrieval result with metadata."""

    content: str = Field(description="The retrieved text content")
    source: str = Field(default="", description="Source document filename")
    project_name: str = Field(default="", description="Project name from metadata")
    chunk_index: int = Field(default=0, description="Chunk index within the document")
    relevance_score: float = Field(default=0.0, description="Relevance score after reranking")
    retrieval_method: str = Field(default="hybrid", description="Method used for retrieval")


def _tokenize_chinese(text: str) -> list[str]:
    """Tokenize text using jieba for Chinese, preserving English tokens.

    Uses jieba.cut_for_search for fine-grained Chinese segmentation.
    English words are preserved as-is. Stopwords are filtered out.

    Args:
        text: Input text (Chinese, English, or mixed).

    Returns:
        List of tokens.
    """
    tokens: list[str] = []
    # Use jieba cut_for_search for fine-grained segmentation
    for token in jieba.cut_for_search(text):
        token = token.strip()
        if not token:
            continue
        if token in _CHINESE_STOPWORDS:
            continue
        # Filter out pure punctuation and whitespace
        if re.match(r"^[\s\W]+$", token) and not re.match(r"^[a-zA-Z0-9]+$", token):
            continue
        tokens.append(token.lower())
    return tokens


class AgenticRetriever:
    """Agentic retriever with hybrid search, reranking, and self-RAG.

    Performs 6-step retrieval:
    1. Query analysis (classify complexity)
    2. Query decomposition (for complex queries)
    3. Hybrid search (dense + BM25 with RRF fusion)
    4. Graph enhancement (via knowledge graph)
    5. Reranking (flashrank)
    6. Self-RAG (sufficiency check + reformulation)
    """

    def __init__(self) -> None:
        """Initialize the AgenticRetriever with required components."""
        self._embedder = BGEEmbeddings()
        self._store = VectorStore()
        self._ranker: Ranker | None = None
        self._bm25: BM25Okapi | None = None
        self._bm25_docs: list[Document] = []
        self._bm25_corpus: list[list[str]] = []

    @property
    def ranker(self) -> Ranker:
        """Lazily load the flashrank reranker model."""
        if self._ranker is None:
            logger.info("loading_reranker", model="ms-marco-MiniLM-L-12-v2")
            self._ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank")
            logger.info("reranker_loaded")
        return self._ranker

    def _build_bm25_index(self) -> None:
        """Build BM25 index from all documents in the vector store."""
        all_docs = self._store.get_all_documents()
        if not all_docs:
            logger.warning("no_documents_for_bm25")
            self._bm25 = None
            self._bm25_docs = []
            self._bm25_corpus = []
            return

        self._bm25_docs = all_docs
        self._bm25_corpus = [_tokenize_chinese(doc.page_content) for doc in all_docs]

        # Filter out empty token lists to prevent BM25 errors
        valid_indices = [i for i, tokens in enumerate(self._bm25_corpus) if tokens]
        if not valid_indices:
            logger.warning("all_documents_empty_after_tokenization")
            self._bm25 = None
            return

        self._bm25_docs = [all_docs[i] for i in valid_indices]
        self._bm25_corpus = [self._bm25_corpus[i] for i in valid_indices]

        self._bm25 = BM25Okapi(self._bm25_corpus)
        logger.info("bm25_index_built", document_count=len(self._bm25_docs))

    def _classify_query(self, query: str) -> QueryType:
        """Classify the query type using rule-based heuristics.

        Args:
            query: User query string.

        Returns:
            QueryType classification.
        """
        # Simple greetings
        greetings = {"你好", "hi", "hello", "hey", "嗨", "哈喽", "您好"}
        if query.strip().lower() in greetings:
            return QueryType.DIRECT_ANSWER

        # Comparison / decomposition triggers
        decomposition_triggers = ["对比", "比较", "vs", "VS", "和.*区别", "与.*不同"]
        for trigger in decomposition_triggers:
            if re.search(trigger, query):
                return QueryType.NEEDS_DECOMPOSITION

        return QueryType.NEEDS_RETRIEVAL

    def _decompose_query(self, query: str) -> list[str]:
        """Decompose a complex query into sub-queries.

        Uses heuristic splitting for comparison queries.

        Args:
            query: Complex query to decompose.

        Returns:
            List of 2-4 sub-queries.
        """
        sub_queries = [query]

        # For comparison queries, extract entities and create per-entity queries
        comparison_match = re.search(
            r"(.+?)(?:和|与|vs|VS|跟|还是)(.+?)(?:的)?(?:对比|比较|区别|不同|差异|优劣)",
            query,
        )
        if comparison_match:
            entity_a = comparison_match.group(1).strip()
            entity_b = comparison_match.group(2).strip()
            sub_queries = [
                f"{entity_a} 的特点和优势",
                f"{entity_b} 的特点和优势",
                query,  # Keep original for context
            ]
        else:
            # Generic decomposition: keep original + extract key topic
            # Try to identify the main subject
            sub_queries = [query]

        logger.debug("query_decomposed", original=query, sub_queries=sub_queries)
        return sub_queries[:4]  # Max 4 sub-queries

    def _dense_search(self, query: str, k: int) -> list[Document]:
        """Perform dense vector similarity search.

        Args:
            query: Query string.
            k: Number of results.

        Returns:
            List of Documents with scores.
        """
        query_embedding = self._embedder.embed_query(query)
        return self._store.similarity_search(query_embedding, k=k)

    def _sparse_search(self, query: str, k: int) -> list[Document]:
        """Perform BM25 sparse retrieval with jieba tokenization.

        Args:
            query: Query string.
            k: Number of results.

        Returns:
            List of Documents with BM25 scores in metadata.
        """
        if self._bm25 is None:
            self._build_bm25_index()

        if self._bm25 is None or not self._bm25_docs:
            return []

        query_tokens = _tokenize_chinese(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # Get top-k indices
        scored_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:k]

        results: list[Document] = []
        for idx in scored_indices:
            if scores[idx] > 0:
                doc = self._bm25_docs[idx]
                metadata = dict(doc.metadata)
                metadata["bm25_score"] = float(scores[idx])
                metadata["score"] = float(scores[idx])
                results.append(
                    Document(page_content=doc.page_content, metadata=metadata)
                )

        logger.debug("bm25_search_completed", results=len(results))
        return results

    def _reciprocal_rank_fusion(
        self,
        dense_results: list[Document],
        sparse_results: list[Document],
        k: int = 60,
    ) -> list[Document]:
        """Merge dense and sparse results using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank_i)) for each result list.

        Args:
            dense_results: Results from dense search.
            sparse_results: Results from BM25 search.
            k: RRF constant (default 60).

        Returns:
            Merged and sorted list of Documents.
        """
        doc_scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}

        def _doc_key(doc: Document) -> str:
            return f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', 0)}"

        # Score dense results
        for rank, doc in enumerate(dense_results):
            key = _doc_key(doc)
            doc_scores[key] = doc_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            doc_map[key] = doc

        # Score sparse results
        for rank, doc in enumerate(sparse_results):
            key = _doc_key(doc)
            doc_scores[key] = doc_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            if key not in doc_map:
                doc_map[key] = doc

        # Sort by RRF score
        sorted_keys = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)

        results: list[Document] = []
        for key in sorted_keys:
            doc = doc_map[key]
            metadata = dict(doc.metadata)
            metadata["rrf_score"] = doc_scores[key]
            metadata["score"] = doc_scores[key]
            results.append(
                Document(page_content=doc.page_content, metadata=metadata)
            )

        logger.debug("rrf_fusion_completed", total_results=len(results))
        return results

    def _rerank(self, query: str, documents: list[Document], top_k: int) -> list[Document]:
        """Rerank documents using flashrank.

        Args:
            query: Original query.
            documents: Documents to rerank.
            top_k: Number of top results to return.

        Returns:
            Reranked list of Documents.
        """
        if not documents:
            return []

        # Prepare passages for flashrank
        passages = [
            {"id": i, "text": doc.page_content, "meta": doc.metadata}
            for i, doc in enumerate(documents)
        ]

        rerank_request = RerankRequest(query=query, passages=passages)
        reranked = self.ranker.rerank(rerank_request)

        results: list[Document] = []
        for item in reranked[:top_k]:
            metadata = dict(item["meta"]) if isinstance(item.get("meta"), dict) else {}
            metadata["rerank_score"] = float(item["score"])
            metadata["score"] = float(item["score"])
            results.append(
                Document(page_content=item["text"], metadata=metadata)
            )

        logger.debug("reranking_completed", input=len(documents), output=len(results))
        return results

    async def _hybrid_search(self, query: str, k: int) -> list[Document]:
        """Perform hybrid search combining dense and sparse retrieval.

        Args:
            query: Query string.
            k: Number of results to retrieve from each method.

        Returns:
            Fused list of Documents.
        """
        dense_results = self._dense_search(query, k=k)
        sparse_results = self._sparse_search(query, k=k)

        logger.info(
            "hybrid_search",
            dense_count=len(dense_results),
            sparse_count=len(sparse_results),
        )

        fused = self._reciprocal_rank_fusion(dense_results, sparse_results)
        return fused

    def _check_sufficiency(self, results: list[Document], threshold: float = 0.3) -> bool:
        """Check if retrieval results are sufficient.

        Args:
            results: Retrieval results to check.
            threshold: Minimum score threshold for the top result.

        Returns:
            True if results are sufficient, False otherwise.
        """
        if not results:
            return False

        top_score = results[0].metadata.get("score", 0.0)
        return float(top_score) > threshold

    def _reformulate_query(self, query: str, attempt: int) -> str:
        """Reformulate a query for retry.

        Uses simple heuristics to modify the query.

        Args:
            query: Original query.
            attempt: Current retry attempt number.

        Returns:
            Reformulated query string.
        """
        if attempt == 1:
            # First retry: add context keywords
            return f"{query} 详细分析 投研报告"
        else:
            # Second retry: simplify
            # Remove common question words and keep keywords
            simplified = re.sub(r"(什么|怎么|如何|为什么|哪些|有哪些|是什么)", "", query)
            return simplified.strip() or query

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        """Execute the full agentic retrieval pipeline.

        6-step process:
        1. Query analysis
        2. Query decomposition (if needed)
        3. Hybrid search (dense + BM25 + RRF)
        4. Graph enhancement
        5. Reranking with flashrank
        6. Self-RAG sufficiency check

        Args:
            query: User query string.
            top_k: Number of results to return. Defaults to settings.reranker_top_k.

        Returns:
            List of RetrievalResult objects.
        """
        top_k = top_k or settings.reranker_top_k

        # Step 1: Query analysis
        query_type = self._classify_query(query)
        logger.info("query_classified", query=query, type=query_type.value)

        if query_type == QueryType.DIRECT_ANSWER:
            return []

        # Step 2: Query decomposition
        if query_type == QueryType.NEEDS_DECOMPOSITION:
            sub_queries = self._decompose_query(query)
        else:
            sub_queries = [query]

        # Step 3: Hybrid search for each sub-query
        all_results: list[Document] = []
        retrieval_k = settings.retriever_top_k

        for sub_query in sub_queries:
            results = await self._hybrid_search(sub_query, k=retrieval_k)
            all_results.extend(results)

        # Deduplicate by content
        seen_keys: set[str] = set()
        unique_results: list[Document] = []
        for doc in all_results:
            key = f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', 0)}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_results.append(doc)

        # Step 4: Graph enhancement
        project_name = ""
        if unique_results:
            project_name = str(unique_results[0].metadata.get("project_name", ""))

        if project_name:
            graph_docs = await graph_rag.find_related(project_name)
            unique_results.extend(graph_docs)

        # Step 5: Reranking
        reranked = self._rerank(query, unique_results, top_k=max(top_k, 5))

        # Step 6: Self-RAG sufficiency check
        max_retries = 2
        current_query = query

        for attempt in range(1, max_retries + 1):
            if self._check_sufficiency(reranked):
                break

            logger.info(
                "insufficient_results_reformulating",
                attempt=attempt,
                max_retries=max_retries,
            )
            current_query = self._reformulate_query(current_query, attempt)
            retry_results = await self._hybrid_search(current_query, k=retrieval_k)
            combined = unique_results + retry_results

            # Deduplicate again
            seen_keys_retry: set[str] = set()
            deduped: list[Document] = []
            for doc in combined:
                key = f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', 0)}"
                if key not in seen_keys_retry:
                    seen_keys_retry.add(key)
                    deduped.append(doc)

            reranked = self._rerank(query, deduped, top_k=max(top_k, 5))

        # Convert to RetrievalResult
        final_results: list[RetrievalResult] = []
        for doc in reranked[:top_k]:
            method = "hybrid"
            if len(sub_queries) > 1:
                method = "hybrid+decomposition"

            final_results.append(
                RetrievalResult(
                    content=doc.page_content,
                    source=str(doc.metadata.get("source", "")),
                    project_name=str(doc.metadata.get("project_name", "")),
                    chunk_index=int(doc.metadata.get("chunk_index", 0)),
                    relevance_score=float(doc.metadata.get("score", 0.0)),
                    retrieval_method=method,
                )
            )

        logger.info("retrieval_completed", query=query, results=len(final_results))
        return final_results
