"""Abstract base class for memory selectors."""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.messages import BaseMessage


class AbstractMemorySelector(ABC):
    """Abstract interface for memory selectors.

    Memory selectors load and compress conversation history
    for injection into LLM context.
    """

    @abstractmethod
    async def load_context(
        self,
        thread_id: str,
        user_query: str,
        max_tokens: int,
    ) -> list[BaseMessage]:
        """Load compressed message history for LLM context.

        Args:
            thread_id: The conversation thread identifier.
            user_query: Current user query for similarity recall.
            max_tokens: Maximum tokens to return.

        Returns:
            List of BaseMessage objects ready for LLM context.
        """

    @abstractmethod
    async def archive_session(self, thread_id: str) -> None:
        """Archive session from hot to cold storage.

        Args:
            thread_id: The conversation thread to archive.
        """
