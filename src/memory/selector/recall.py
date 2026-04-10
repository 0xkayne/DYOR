"""Similarity recall using ChromaDB for cross-session context injection.

When a new query arrives, finds relevant passages from past sessions
by embedding the query and searching the session_summaries collection.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger(__name__)

# Disable ChromaDB anonymous telemetry
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb

_SESSION_SUMMARIES_COLLECTION = "session_summaries"


class SimilarityRecall:
    """Retrieves similar past sessions via ChromaDB embedding search.

    Uses BGE-M3 (same model as RAG) for embedding and queries
    the session_summaries collection with thread_id exclusion.
    """

    def __init__(
        self,
        top_k: int | None = None,
        similarity_threshold: float = 0.7,
    ) -> None:
        """Initialize the recall selector.

        Args:
            top_k: Number of similar sessions to retrieve.
                Defaults to settings.similarity_top_k.
            similarity_threshold: Minimum similarity score (0-1).
                Results below this threshold are excluded.
        """
        self._top_k = top_k or settings.similarity_top_k
        self._threshold = similarity_threshold
        self._embedder: Any | None = None
        self._client: chromadb.PersistentClient | None = None

    @property
    def top_k(self) -> int:
        """Return the number of results to retrieve."""
        return self._top_k

    def _get_embedder(self) -> Any:
        """Lazily initialize and return the BGE embedder."""
        if self._embedder is None:
            from src.rag.embeddings import BGEEmbeddings
            self._embedder = BGEEmbeddings()
        return self._embedder

    def _get_collection(self) -> Any:
        """Get or create the session_summaries ChromaDB collection."""
        if self._client is None:
            persist_dir = settings.chroma_persist_dir
            self._client = chromadb.PersistentClient(path=persist_dir)

        try:
            collection = self._client.get_collection(name=_SESSION_SUMMARIES_COLLECTION)
        except Exception:
            collection = self._client.create_collection(
                name=_SESSION_SUMMARIES_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("session_summaries_collection_created")
        return collection

    async def retrieve(
        self,
        query: str,
        exclude_thread_id: str,
    ) -> list[str]:
        """Retrieve similar session summaries excluding current thread.

        Args:
            query: The current user query for embedding.
            exclude_thread_id: Thread ID to exclude from results.

        Returns:
            List of session summary text snippets with similarity > threshold.
        """
        try:
            embedder = self._get_embedder()
            query_embedding = embedder.embed_query(query)

            collection = self._get_collection()
            count = collection.count()
            if count == 0:
                logger.debug("session_summaries_collection_empty")
                return []

            n_results = min(self._top_k * 2, count)  # Over-fetch to filter

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"thread_id": {"$ne": exclude_thread_id}},
                include=["documents", "metadatas", "distances"],
            )

            snippets: list[str] = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i] if results.get("distances") else 0.0
                    # ChromaDB cosine distance: 0 = identical, 2 = opposite
                    similarity = 1.0 - distance / 2.0

                    if similarity >= self._threshold:
                        metadata_list = results.get("metadatas", [[]])[0]
                        metadata = metadata_list[i] if metadata_list else {}
                        thread_id = metadata.get("thread_id", "unknown") if metadata else "unknown"
                        snippets.append(f"[Session {str(thread_id)[:8]}...]: {doc}")

                    if len(snippets) >= self._top_k:
                        break

            logger.info(
                "similarity_recall_results",
                query_length=len(query),
                results_count=len(snippets),
            )
            return snippets

        except Exception as exc:
            logger.error("similarity_recall_failed", error=str(exc))
            return []
