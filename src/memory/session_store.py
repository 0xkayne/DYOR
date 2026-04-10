"""Session archival and ChromaDB indexing for session summaries.

Handles:
- Archiving sessions from hot (Redis) to cold (Postgres) storage
- Generating session summary text for embedding
- Upserting to session_summaries ChromaDB collection
- Deleting from Redis after successful archival
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger(__name__)

# Disable ChromaDB anonymous telemetry
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb

_SESSION_SUMMARIES_COLLECTION = "session_summaries"


def get_session_summaries_collection() -> Any:
    """Get or create the session_summaries ChromaDB collection.

    Returns:
        ChromaDB collection for session summaries with schema:
            {"thread_id": "string", "created_at": "string"}
    """
    from src.rag.vectorstore import _clean_metadata

    persist_dir = settings.chroma_persist_dir
    client = chromadb.PersistentClient(path=persist_dir)

    try:
        collection = client.get_collection(name=_SESSION_SUMMARIES_COLLECTION)
    except Exception:
        collection = client.create_collection(
            name=_SESSION_SUMMARIES_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("session_summaries_collection_created")

    return collection


def _format_session_summary(
    thread_id: str,
    messages: list[Any],
    created_at: str | None = None,
) -> str:
    """Format session messages into a summary string for embedding.

    Args:
        thread_id: The thread identifier.
        messages: List of messages in the session.
        created_at: Session creation timestamp.

    Returns:
        Formatted summary text suitable for embedding.
    """
    timestamp = created_at or datetime.utcnow().isoformat()

    user_messages: list[str] = []
    assistant_messages: list[str] = []

    for msg in messages:
        content = getattr(msg, "content", "") or ""
        if not content:
            continue
        msg_type = getattr(msg, "type", "unknown")
        if msg_type in ("human", "user"):
            user_messages.append(content[:500])
        elif msg_type in ("ai", "assistant"):
            assistant_messages.append(content[:500])

    parts = [f"Session: {thread_id}", f"Created: {timestamp}"]

    if user_messages:
        parts.append(
            f"User queries ({len(user_messages)}): "
            + " | ".join(user_messages[:5])
        )

    if assistant_messages:
        parts.append(
            f"Assistant responses ({len(assistant_messages)}): "
            + " | ".join(assistant_messages[:3])
        )

    return " ".join(parts)


async def archive_session(thread_id: str) -> None:
    """Archive a session from hot to cold storage and index in ChromaDB.

    Pipeline:
    1. Get full checkpoint from PostgresSaver (cold storage)
    2. Generate session summary text
    3. Embed and upsert to session_summaries ChromaDB collection
    4. Delete from Redis (hot storage) after successful archival

    Args:
        thread_id: The conversation thread to archive.
    """
    logger.info("archiving_session", thread_id=thread_id)

    try:
        # Step 1: Get checkpoint from checkpointer
        from src.memory.checkpointer import get_checkpointer

        checkpointer = get_checkpointer()
        config = {"configurable": {"thread_id": thread_id}}

        checkpoint = await checkpointer.aget(config)

        if not checkpoint:
            logger.warning("archive_no_checkpoint", thread_id=thread_id)
            return

        messages = checkpoint.get("channel_values", {}).get("messages", [])
        created_at = checkpoint.get("configurable", {}).get("created_at")

        # Step 2: Generate summary
        summary_text = _format_session_summary(thread_id, messages, created_at)

        # Step 3: Embed and upsert to ChromaDB
        from src.rag.embeddings import BGEEmbeddings

        embedder = BGEEmbeddings()
        embedding = embedder.embed_query(summary_text)

        collection = get_session_summaries_collection()
        collection.upsert(
            ids=[thread_id],
            embeddings=[embedding],
            documents=[summary_text],
            metadatas=[{
                "thread_id": thread_id,
                "created_at": created_at or datetime.utcnow().isoformat(),
            }],
        )

        logger.info(
            "session_indexed",
            thread_id=thread_id,
            summary_length=len(summary_text),
        )

        # Step 4: Delete from Redis if dual-layer checkpointer
        if hasattr(checkpointer, "redis_saver"):
            try:
                await checkpointer.redis_saver.adelete(config)
                logger.info("redis_session_deleted", thread_id=thread_id)
            except Exception as exc:
                logger.warning(
                    "redis_delete_failed",
                    thread_id=thread_id,
                    error=str(exc),
                )

    except Exception as exc:
        logger.error("archive_session_failed", thread_id=thread_id, error=str(exc))
        raise
