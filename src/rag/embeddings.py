"""Embedding model wrapper for generating vector representations of text.

Uses BGE-M3 as the primary embedding model with automatic fallback
to bge-small-zh-v1.5 if resource-constrained.
"""

from __future__ import annotations

from typing import Any

import structlog
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

from src.config import settings

logger = structlog.get_logger(__name__)

_PRIMARY_MODEL = "BAAI/bge-m3"
_FALLBACK_MODEL = "BAAI/bge-small-zh-v1.5"


class BGEEmbeddings(Embeddings):
    """LangChain-compatible embedding wrapper around BGE-M3.

    Lazily loads the SentenceTransformer model on first use.
    Falls back to bge-small-zh-v1.5 if BGE-M3 fails to load.
    """

    def __init__(self, model_name: str | None = None, **kwargs: Any) -> None:
        """Initialize BGEEmbeddings.

        Args:
            model_name: Override model name. Defaults to settings.embedding_model.
            **kwargs: Additional arguments passed to SentenceTransformer.
        """
        self._model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None
        self._kwargs = kwargs

    @property
    def model(self) -> SentenceTransformer:
        """Lazily load and return the SentenceTransformer model."""
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self) -> SentenceTransformer:
        """Load the embedding model with automatic fallback.

        Returns:
            Loaded SentenceTransformer model.
        """
        try:
            logger.info("loading_embedding_model", model=self._model_name)
            model = SentenceTransformer(self._model_name, **self._kwargs)
            logger.info("embedding_model_loaded", model=self._model_name)
            return model
        except Exception as exc:
            if self._model_name != _FALLBACK_MODEL:
                logger.warning(
                    "primary_model_failed_falling_back",
                    primary=self._model_name,
                    fallback=_FALLBACK_MODEL,
                    error=str(exc),
                )
                self._model_name = _FALLBACK_MODEL
                return self._load_model()
            raise

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of documents.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []
        logger.debug("embedding_documents", count=len(texts))
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a single query.

        Args:
            text: Query text to embed.

        Returns:
            Embedding vector.
        """
        logger.debug("embedding_query", text_length=len(text))
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
