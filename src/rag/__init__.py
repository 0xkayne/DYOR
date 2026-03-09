"""RAG engine module for document processing, embedding, retrieval, and evaluation.

Public API:
    - BGEEmbeddings: Embedding model wrapper
    - VectorStore: ChromaDB vector store
    - AgenticRetriever: Full retrieval pipeline
    - ingest_reports: Batch document ingestion
    - run_evaluation: RAGAS evaluation runner
"""

from src.rag.embeddings import BGEEmbeddings
from src.rag.evaluator import run_evaluation
from src.rag.ingest import ingest_reports
from src.rag.retriever import AgenticRetriever
from src.rag.vectorstore import VectorStore

__all__ = [
    "BGEEmbeddings",
    "VectorStore",
    "AgenticRetriever",
    "ingest_reports",
    "run_evaluation",
]
