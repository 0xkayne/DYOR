"""WebSocket chat endpoint for interactive research conversations.

Provides two real-time transports for streaming LangGraph workflow output:

* ``/ws/chat``        — WebSocket with heartbeat and reconnect-resume support.
* ``/stream/chat``    — Server-Sent Events (SSE) for Streamlit and other HTTP clients.

Both transports use the unified StreamMessage protocol defined in
``api.middleware.streaming``.
"""

import asyncio
import json
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.middleware.streaming import StreamMessage, stream_workflow

logger = structlog.get_logger(__name__)

chat_router = APIRouter(tags=["chat"])

# Heartbeat intervals (seconds).
_PING_INTERVAL = 30
_PONG_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """Incoming chat message from the client.

    Attributes:
        query: The user's natural-language research question.
        thread_id: Optional LangGraph thread ID; generated if omitted.
        workflow_type: Which workflow mode to use (default ``qa``).
    """

    query: str
    thread_id: str | None = None
    workflow_type: str = "qa"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_config(thread_id: str) -> dict[str, Any]:
    """Build the LangGraph RunnableConfig for a given thread.

    Args:
        thread_id: The session / conversation identifier.

    Returns:
        Config dict suitable for ``workflow.ainvoke`` / ``astream_events``.
    """
    return {"configurable": {"thread_id": thread_id}}


async def _run_and_cache(
    workflow_app: Any,
    input_state: dict[str, Any],
    config: dict[str, Any],
    semaphore: asyncio.Semaphore,
    result_cache: dict[str, list[StreamMessage]],
    thread_id: str,
    queue: asyncio.Queue,
) -> None:
    """Execute the workflow and push messages onto *queue*, caching them simultaneously.

    When the queue consumer (WebSocket sender) has already disconnected, messages
    accumulate only in the cache so they can be replayed on reconnect.

    Args:
        workflow_app: Compiled LangGraph application.
        input_state: Initial workflow state.
        config: LangGraph RunnableConfig.
        semaphore: Concurrency-limiting semaphore.
        result_cache: Shared dict mapping thread_id → list of StreamMessages.
        thread_id: Cache key for this execution.
        queue: asyncio.Queue where messages are pushed for the active sender.
    """
    cached: list[StreamMessage] = []
    result_cache[thread_id] = cached

    try:
        async for msg in stream_workflow(workflow_app, input_state, config, semaphore):
            cached.append(msg)
            await queue.put(msg)
    finally:
        # Sentinel tells the sender task that the workflow is finished.
        await queue.put(None)


async def _ws_sender(websocket: WebSocket, queue: asyncio.Queue) -> None:
    """Drain *queue* and forward each StreamMessage over *websocket*.

    Stops when it dequeues the ``None`` sentinel or the WebSocket closes.

    Args:
        websocket: The active WebSocket connection.
        queue: Source queue populated by ``_run_and_cache``.
    """
    while True:
        msg: StreamMessage | None = await queue.get()
        if msg is None:
            break
        try:
            await websocket.send_text(msg.model_dump_json())
        except WebSocketDisconnect:
            break
        except Exception:  # noqa: BLE001
            break


async def _ws_heartbeat(websocket: WebSocket, pong_event: asyncio.Event) -> None:
    """Send ping frames periodically and close the socket if no pong arrives.

    Args:
        websocket: The active WebSocket connection.
        pong_event: An asyncio.Event that is set each time a pong is received.

    Raises:
        WebSocketDisconnect: When the heartbeat timeout is exceeded.
    """
    while True:
        await asyncio.sleep(_PING_INTERVAL)
        try:
            await websocket.send_text(json.dumps({"type": "ping"}))
        except Exception:  # noqa: BLE001
            return

        # Wait up to (PONG_TIMEOUT - PING_INTERVAL) seconds for a pong.
        wait_seconds = max(_PONG_TIMEOUT - _PING_INTERVAL, 1)
        try:
            await asyncio.wait_for(pong_event.wait(), timeout=float(wait_seconds))
            pong_event.clear()
        except asyncio.TimeoutError:
            logger.warning("ws heartbeat timeout — closing connection")
            try:
                await websocket.close(code=1001)
            except Exception:  # noqa: BLE001
                pass
            return


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@chat_router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    """Stream analysis progress and results over a WebSocket connection.

    Protocol
    --------
    1. Client connects and sends a JSON-encoded ChatMessage.
    2. Server checks ``result_cache`` for cached messages from a prior run and
       replays them immediately if present.
    3. Otherwise the LangGraph workflow is started in a background task; messages
       are forwarded as they arrive.
    4. Server sends ``{"type": "ping"}`` every 30 s; client must reply with
       ``{"type": "pong"}`` within 60 s or the connection is closed.
    5. On client disconnect the workflow continues running; its output is cached
       under *thread_id* so a reconnecting client can retrieve it.

    Args:
        websocket: The incoming WebSocket connection managed by FastAPI/Starlette.
    """
    await websocket.accept()
    app = websocket.app
    workflow = app.state.workflow
    semaphore: asyncio.Semaphore = app.state.semaphore
    result_cache: dict[str, list[StreamMessage]] = app.state.result_cache

    pong_event = asyncio.Event()
    pong_event.set()  # Treat connection as alive at startup.

    # Start background heartbeat monitor.
    heartbeat_task = asyncio.create_task(_ws_heartbeat(websocket, pong_event))

    try:
        raw = await websocket.receive_text()
    except WebSocketDisconnect:
        heartbeat_task.cancel()
        return

    # Parse the incoming ChatMessage.
    try:
        chat_msg = ChatMessage(**json.loads(raw))
    except Exception as exc:  # noqa: BLE001
        err = StreamMessage(
            type="error",
            agent="system",
            content=f"Invalid message format: {exc}",
            timestamp=__import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc),
        )
        await websocket.send_text(err.model_dump_json())
        heartbeat_task.cancel()
        return

    thread_id = chat_msg.thread_id or str(uuid4())

    # If this thread already has a cached result (e.g. reconnect), replay immediately.
    if thread_id in result_cache:
        cached_msgs = result_cache.pop(thread_id)
        for msg in cached_msgs:
            try:
                await websocket.send_text(msg.model_dump_json())
            except WebSocketDisconnect:
                break
        heartbeat_task.cancel()
        return

    # Check workflow availability.
    if workflow is None:
        err = StreamMessage(
            type="error",
            agent="system",
            content="Workflow not available — the LangGraph graph failed to initialise.",
            timestamp=__import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc),
        )
        await websocket.send_text(err.model_dump_json())
        heartbeat_task.cancel()
        return

    input_state = {
        "query": chat_msg.query,
        "workflow_type": chat_msg.workflow_type,
    }
    config = _build_config(thread_id)
    queue: asyncio.Queue = asyncio.Queue()

    # Launch workflow execution and WebSocket sending concurrently.
    workflow_task = asyncio.create_task(
        _run_and_cache(workflow, input_state, config, semaphore, result_cache, thread_id, queue)
    )
    sender_task = asyncio.create_task(_ws_sender(websocket, queue))

    # Also listen for pong messages from the client while the workflow runs.
    async def _receive_loop() -> None:
        try:
            while True:
                text = await websocket.receive_text()
                try:
                    data = json.loads(text)
                    if data.get("type") == "pong":
                        pong_event.set()
                except Exception:  # noqa: BLE001
                    pass
        except WebSocketDisconnect:
            pass

    receive_task = asyncio.create_task(_receive_loop())

    try:
        # Wait until the sender finishes (workflow done) or client disconnects.
        done, pending = await asyncio.wait(
            {sender_task, receive_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    except Exception:  # noqa: BLE001
        pass
    finally:
        heartbeat_task.cancel()
        # workflow_task must always run to completion so the cache is populated.
        # We do NOT cancel it.
        if not workflow_task.done():
            logger.info(
                "ws client disconnected — workflow continues in background",
                thread_id=thread_id,
            )

    logger.info("ws_chat session ended", thread_id=thread_id)


# ---------------------------------------------------------------------------
# SSE endpoint
# ---------------------------------------------------------------------------


@chat_router.get("/stream/chat")
async def sse_chat(
    request: Request,
    query: str,
    thread_id: str | None = None,
    workflow_type: str = "qa",
) -> EventSourceResponse:
    """Stream analysis progress and results via Server-Sent Events.

    This endpoint is the recommended interface for Streamlit and other HTTP
    clients that cannot use raw WebSocket connections.  Message format is
    identical to the WebSocket transport.

    Args:
        request: FastAPI Request object (used to access ``app.state``).
        query: Natural-language research question.
        thread_id: Optional LangGraph thread ID; generated if omitted.
        workflow_type: Which workflow mode to use (default ``qa``).

    Returns:
        An EventSourceResponse streaming StreamMessage JSON objects.
    """
    app = request.app
    workflow = app.state.workflow
    semaphore: asyncio.Semaphore = app.state.semaphore
    result_cache: dict[str, list[StreamMessage]] = app.state.result_cache

    resolved_thread_id = thread_id or str(uuid4())
    config = _build_config(resolved_thread_id)

    async def _event_generator():
        # Replay cached result if available.
        if resolved_thread_id in result_cache:
            cached_msgs = result_cache.pop(resolved_thread_id)
            for msg in cached_msgs:
                yield {"data": msg.model_dump_json()}
            return

        if workflow is None:
            from datetime import datetime, timezone

            err = StreamMessage(
                type="error",
                agent="system",
                content="Workflow not available — the LangGraph graph failed to initialise.",
                timestamp=datetime.now(tz=timezone.utc),
            )
            yield {"data": err.model_dump_json()}
            return

        input_state = {"query": query, "workflow_type": workflow_type}

        async for msg in stream_workflow(workflow, input_state, config, semaphore):
            # Respect client disconnect.
            if await request.is_disconnected():
                logger.info("sse client disconnected", thread_id=resolved_thread_id)
                break
            yield {"data": msg.model_dump_json()}

    return EventSourceResponse(_event_generator())
