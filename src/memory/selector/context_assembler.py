"""Context assembler combining summarization and recall for LLM context.

The ContextAssembler orchestrates the full memory selection pipeline:
1. Load raw checkpoint messages
2. Compress via summarization if over threshold
3. Retrieve similar sessions via recall
4. Truncate to max_context_messages
5. Estimate token count
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from langchain_core.messages import BaseMessage, SystemMessage

from src.config import settings

if TYPE_CHECKING:
    from langgraph.checkpoint.serde.base import BaseCheckpointSaver

from src.memory.selector.recall import SimilarityRecall
from src.memory.selector.summarizer import Summarizer

logger = structlog.get_logger(__name__)


class ContextAssembler:
    """Assembles compressed LLM context from checkpoint history.

    Combines summarization and similarity recall to produce
    a context dict with messages, flags, and token estimate.
    """

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
        summarizer: Summarizer | None = None,
        recall: SimilarityRecall | None = None,
        max_context_messages: int | None = None,
    ) -> None:
        """Initialize the context assembler.

        Args:
            checkpointer: LangGraph checkpointer for loading history.
            summarizer: Summarizer instance. Defaults to new Summarizer().
            recall: SimilarityRecall instance. Defaults to new SimilarityRecall().
            max_context_messages: Maximum messages to return.
                Defaults to settings.max_context_messages.
        """
        self._checkpointer = checkpointer
        self._summarizer = summarizer or Summarizer()
        self._recall = recall or SimilarityRecall()
        self._max_messages = max_context_messages or settings.max_context_messages

    async def assemble(
        self,
        thread_id: str,
        user_query: str,
    ) -> dict[str, Any]:
        """Assemble complete context for a new LLM call.

        Pipeline:
        1. Load raw checkpoint messages from checkpointer
        2. Summarize if over threshold
        3. Recall similar sessions (inject as SystemMessage at position 0)
        4. Truncate to max_context_messages from end
        5. Estimate token count (rough: total_chars // 4)

        Args:
            thread_id: The conversation thread identifier.
            user_query: Current user query for similarity recall.

        Returns:
            Dict with keys:
                - messages: list of BaseMessage to inject
                - has_recall: bool (whether recall was added)
                - is_summarized: bool (whether history was compressed)
                - token_count: int (approximate)
        """
        # Step 1: Load raw checkpoint messages
        raw_messages: list[BaseMessage] = []
        if self._checkpointer is not None:
            try:
                config = {"configurable": {"thread_id": thread_id}}
                checkpoint = await self._checkpointer.aget(config)
                if checkpoint and "channel_values" in checkpoint:
                    raw_messages = checkpoint["channel_values"].get("messages", [])
            except Exception as exc:
                logger.warning(
                    "checkpoint_load_failed",
                    thread_id=thread_id,
                    error=str(exc),
                )

        # Step 2: Summarize if over threshold
        if len(raw_messages) > self._summarizer.threshold:
            messages = await self._summarizer.compress(raw_messages)
            is_summarized = True
            logger.info(
                "context_summarized",
                original=len(raw_messages),
                compressed=len(messages),
            )
        else:
            messages = list(raw_messages)
            is_summarized = False

        # Step 3: Recall similar sessions
        similar_snippets = await self._recall.retrieve(
            query=user_query,
            exclude_thread_id=thread_id,
        )
        has_recall = len(similar_snippets) > 0

        if has_recall:
            recall_msg = SystemMessage(
                content="Prior relevant sessions:\n" + "\n---\n".join(similar_snippets)
            )
            messages = [recall_msg] + messages
            logger.info("recall_injected", snippets=len(similar_snippets))

        # Step 4: Truncate to max_context_messages
        if len(messages) > self._max_messages:
            messages = messages[-self._max_messages :]
            logger.debug("context_truncated", max_messages=self._max_messages)

        # Step 5: Estimate token count (rough: total_chars // 4)
        token_count = sum(
            len(getattr(m, "content", "") or "") for m in messages
        ) // 4

        return {
            "messages": messages,
            "has_recall": has_recall,
            "is_summarized": is_summarized,
            "token_count": token_count,
        }
