"""Streaming response middleware for real-time analysis progress.

Converts LangGraph astream_events v2 events into a unified StreamMessage protocol
shared by both WebSocket and SSE transports.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any, Literal

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

# Mapping from LangGraph node/chain names to the agent label used in the protocol.
_CHAIN_NAME_TO_AGENT: dict[str, str] = {
    "router": "router",
    "planner": "planner",
    "rag": "rag",
    "market": "market",
    "news": "news",
    "tokenomics": "tokenomics",
    "analyst": "analyst",
    "critic": "critic",
}


def _now_iso() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


def _agent_from_name(name: str) -> str:
    """Extract a normalised agent label from a LangGraph node/chain name.

    Args:
        name: The raw ``name`` field from a LangGraph stream event.

    Returns:
        A lowercase agent label matching one of the protocol-defined agent names,
        or the lowercased raw name if no mapping is found.
    """
    lower = name.lower()
    for key, label in _CHAIN_NAME_TO_AGENT.items():
        if key in lower:
            return label
    return lower


class StreamMessage(BaseModel):
    """Unified streaming message format shared by WebSocket and SSE transports.

    Attributes:
        type: Message category — status, token, result, or error.
        agent: The agent that produced this message.
        content: Human-readable or JSON content payload.
        timestamp: UTC timestamp when the message was created.
    """

    type: Literal["status", "token", "result", "error"]
    agent: str
    content: str
    timestamp: datetime


def langgraph_event_to_messages(event: dict[str, Any]) -> list[StreamMessage]:
    """Convert a single LangGraph astream_events v2 event to StreamMessage list.

    Handles three event kinds:
    - ``on_chain_start``  → status message indicating the agent has started.
    - ``on_chat_model_stream`` → token message with partial LLM output.
    - ``on_chain_end`` (top-level only) → result message with serialised output.

    Args:
        event: A raw event dict yielded by ``workflow.astream_events(..., version="v2")``.

    Returns:
        A list of StreamMessage objects (usually 0 or 1 item).
    """
    kind: str = event.get("event", "")
    name: str = event.get("name", "unknown")
    agent = _agent_from_name(name)
    messages: list[StreamMessage] = []

    if kind == "on_chain_start":
        messages.append(
            StreamMessage(
                type="status",
                agent=agent,
                content=f"{name} started",
                timestamp=_now_iso(),
            )
        )

    elif kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        token_text: str = ""
        if chunk is not None:
            # LangChain AIMessageChunk carries content as str or list of dicts.
            raw_content = getattr(chunk, "content", "")
            if isinstance(raw_content, str):
                token_text = raw_content
            elif isinstance(raw_content, list):
                # Tool-use chunks may embed text blocks as dicts.
                token_text = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in raw_content
                )
        if token_text:
            messages.append(
                StreamMessage(
                    type="token",
                    agent=agent,
                    content=token_text,
                    timestamp=_now_iso(),
                )
            )

    elif kind == "on_chain_end":
        # Only emit a result for top-level chain completions (no parent run).
        parent_ids: list[str] = event.get("parent_ids", [])
        if not parent_ids:
            output = event.get("data", {}).get("output", "")
            if isinstance(output, dict):
                import json

                content = json.dumps(output, ensure_ascii=False, default=str)
            else:
                content = str(output) if output else f"{name} completed"
            messages.append(
                StreamMessage(
                    type="result",
                    agent=agent,
                    content=content,
                    timestamp=_now_iso(),
                )
            )

    return messages


async def stream_workflow(
    workflow_app: Any,
    input_state: dict[str, Any],
    config: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> AsyncGenerator[StreamMessage, None]:
    """Stream LangGraph workflow execution as StreamMessage objects.

    Acquires the semaphore before invoking the workflow so the maximum number
    of concurrent LLM-backed workflows is bounded.  Exceptions from the
    workflow are caught and converted into error StreamMessages so the
    transport layer always receives a clean stream.

    Args:
        workflow_app: A compiled LangGraph application with an ``astream_events`` method.
        input_state: The initial state dict passed to the workflow.
        config: LangGraph RunnableConfig (must include ``configurable.thread_id``).
        semaphore: An asyncio.Semaphore that caps concurrent workflow executions.

    Yields:
        StreamMessage objects in chronological order.
    """
    async with semaphore:
        try:
            async for event in workflow_app.astream_events(
                input_state, config=config, version="v2"
            ):
                for msg in langgraph_event_to_messages(event):
                    yield msg
        except asyncio.CancelledError:
            logger.info("stream_workflow cancelled", config=config)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("stream_workflow error", error=str(exc), config=config)
            yield StreamMessage(
                type="error",
                agent="system",
                content=str(exc),
                timestamp=_now_iso(),
            )
