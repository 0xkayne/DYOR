"""Summarization memory selector using LLM for context compression.

When conversation history exceeds a threshold, older messages are
summarized by an LLM to preserve key facts while reducing token count.
"""

from __future__ import annotations

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, SystemMessage

from src.config import settings

logger = structlog.get_logger(__name__)


class Summarizer:
    """Compresses long conversation histories via LLM summarization.

    Keeps the most recent N messages intact and summarizes older ones
    into a single SystemMessage preserving key facts and preferences.
    """

    def __init__(
        self,
        threshold: int | None = None,
        llm_model: str | None = None,
    ) -> None:
        """Initialize the summarizer.

        Args:
            threshold: Number of recent messages to keep without summarization.
                Defaults to settings.summarization_threshold.
            llm_model: LLM model for summarization. Defaults to
                settings.llm_model_sonnet (lightweight model).
        """
        self._threshold = threshold or settings.summarization_threshold
        self._llm_model = llm_model or settings.llm_model_sonnet
        self._llm: ChatAnthropic | None = None

    @property
    def threshold(self) -> int:
        """Return the message count threshold for summarization."""
        return self._threshold

    @property
    def llm(self) -> ChatAnthropic:
        """Lazily initialize and return the ChatAnthropic LLM."""
        if self._llm is None:
            self._llm = ChatAnthropic(
                model=self._llm_model,
                api_key=settings.anthropic_api_key,
                temperature=0.0,
                max_tokens=1024,
            )
        return self._llm

    def _format_messages(self, messages: list[BaseMessage]) -> str:
        """Format messages for summarization prompt.

        Args:
            messages: List of messages to format.

        Returns:
            Formatted string representation.
        """
        parts: list[str] = []
        for msg in messages:
            role = getattr(msg, "type", "unknown")
            content = getattr(msg, "content", "") or ""
            parts.append(f"[{role}] {content}")
        return "\n\n".join(parts)

    async def compress(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """Compress message history if over threshold.

        Args:
            messages: Full message history from checkpoint.

        Returns:
            Compressed message list:
            - If len(messages) <= threshold: unchanged
            - If len(messages) > threshold: summary + recent threshold messages
        """
        if len(messages) <= self._threshold:
            logger.debug("summarizer_below_threshold", count=len(messages))
            return list(messages)

        # Separate older vs recent messages
        recent_msgs = messages[-self._threshold :]
        older_msgs = messages[: -self._threshold]

        logger.info(
            "summarizing_messages",
            older_count=len(older_msgs),
            recent_count=len(recent_msgs),
        )

        # Build summarization prompt
        older_text = self._format_messages(older_msgs)
        summary_prompt = f"""Summarize this conversation history concisely, preserving ALL of the following:
- Key facts and entities mentioned (project names, numbers, dates)
- User preferences and requirements
- Conclusions and decisions made
- Any questions asked and answers provided

Do NOT paraphrase - preserve the actual information.

Conversation to summarize:
{older_text}

Provide a concise summary that captures all key information:"""

        try:
            response = await self.llm.ainvoke([SystemMessage(content=summary_prompt)])
            summary_content = getattr(response, "content", "") or ""
            if isinstance(summary_content, list):
                summary_content = (
                    summary_content[0].get("text", "") if summary_content else ""
                )

            logger.info(
                "summarization_complete",
                summary_length=len(summary_content),
            )

            return [
                SystemMessage(content=f"Prior conversation summary: {summary_content}"),
                *recent_msgs,
            ]
        except Exception as exc:
            logger.error("summarization_failed", error=str(exc))
            # Fallback: return all messages unsummarized
            return list(messages)
