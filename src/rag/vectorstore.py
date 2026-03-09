"""Vector database operations for storing and querying document embeddings.

Uses ChromaDB PersistentClient for durable vector storage with
metadata filtering support.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
import structlog
from langchain_core.documents import Document

from src.config import settings

logger = structlog.get_logger(__name__)

_COLLECTION_NAME = "dyor_reports"


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Clean metadata values for ChromaDB compatibility.

    ChromaDB only accepts str, int, float, bool as metadata values.
    None is converted to empty string, lists/dicts are converted to str.

    Args:
        metadata: Raw metadata dictionary.

    Returns:
        Cleaned metadata with only ChromaDB-compatible types.
    """
    cleaned: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            cleaned[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        elif isinstance(value, (list, dict)):
            cleaned[key] = str(value)
        else:
            cleaned[key] = str(value)
    return cleaned


class VectorStore:
    """ChromaDB-backed vector store for document embeddings.

    Manages a persistent ChromaDB collection for storing and querying
    document chunks with their embeddings and metadata.
    """

    def __init__(self, persist_dir: str | None = None) -> None:
        """Initialize the vector store.

        Args:
            persist_dir: Directory for ChromaDB persistence.
                Defaults to settings.chroma_persist_dir.
        """
        self._persist_dir = persist_dir or settings.chroma_persist_dir
        Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "vectorstore_initialized",
            persist_dir=self._persist_dir,
            collection=_COLLECTION_NAME,
        )

    def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]],
    ) -> None:
        """Add documents with their embeddings to the collection.

        Args:
            documents: List of LangChain Documents to store.
            embeddings: Corresponding embedding vectors.
        """
        if not documents:
            return

        ids = []
        metadatas = []
        contents = []

        for i, doc in enumerate(documents):
            doc_id = f"{doc.metadata.get('source', 'unknown')}_{doc.metadata.get('chunk_index', i)}"
            ids.append(doc_id)
            metadatas.append(_clean_metadata(doc.metadata))
            contents.append(doc.page_content)

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=contents,
        )
        logger.info("documents_added", count=len(documents))

    def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Query the collection for similar documents.

        Args:
            query_embedding: Query embedding vector.
            k: Number of results to return.
            where: Optional metadata filter for ChromaDB.

        Returns:
            List of Documents with similarity score in metadata.
        """
        query_params: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(k, self._collection.count()) if self._collection.count() > 0 else k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_params["where"] = where

        if self._collection.count() == 0:
            logger.warning("empty_collection_query")
            return []

        results = self._collection.query(**query_params)

        documents: list[Document] = []
        for i in range(len(results["ids"][0])):
            metadata = dict(results["metadatas"][0][i]) if results["metadatas"] else {}
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score: 1 - distance/2
            distance = results["distances"][0][i] if results["distances"] else 0.0
            metadata["score"] = 1.0 - distance / 2.0
            documents.append(
                Document(
                    page_content=results["documents"][0][i] if results["documents"] else "",
                    metadata=metadata,
                )
            )

        logger.debug("similarity_search_completed", results=len(documents))
        return documents

    def get_all_documents(self) -> list[Document]:
        """Retrieve all documents from the collection.

        Returns:
            List of all stored Documents.
        """
        if self._collection.count() == 0:
            return []

        results = self._collection.get(include=["documents", "metadatas"])
        documents: list[Document] = []
        for i in range(len(results["ids"])):
            metadata = dict(results["metadatas"][i]) if results["metadatas"] else {}
            documents.append(
                Document(
                    page_content=results["documents"][i] if results["documents"] else "",
                    metadata=metadata,
                )
            )
        return documents

    def delete_collection(self) -> None:
        """Delete the entire collection."""
        self._client.delete_collection(_COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("collection_deleted", collection=_COLLECTION_NAME)

    def get_collection_stats(self) -> dict[str, Any]:
        """Get statistics about the collection.

        Returns:
            Dictionary with collection statistics.
        """
        count = self._collection.count()
        return {
            "collection_name": _COLLECTION_NAME,
            "document_count": count,
            "persist_dir": self._persist_dir,
        }
