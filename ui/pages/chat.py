"""Chat page for interactive research conversations."""

import json
import uuid

import httpx
import streamlit as st

AGENT_DISPLAY_NAMES = {
    "router": "Router",
    "planner": "Planner",
    "rag": "RAG Retriever",
    "market": "Market Analyst",
    "news": "News Analyst",
    "tokenomics": "Tokenomics Analyst",
    "analyst": "Lead Analyst",
    "critic": "Critic",
}

AGENT_STEP_ICONS = {
    "router": "🔀",
    "planner": "📋",
    "rag": "🔍",
    "market": "📊",
    "news": "📰",
    "tokenomics": "🪙",
    "analyst": "✍️",
    "critic": "🔎",
}


def render_chat_page() -> None:
    """Render the main chat interface with message history and streaming input."""
    st.header("Research Chat")
    st.caption("Ask about any crypto project — I'll run a full analysis for you.")

    _render_chat_history()

    query = st.chat_input(
        "Ask about any crypto project...",
        disabled=st.session_state.get("is_streaming", False),
    )

    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        _stream_response(query)


def _render_chat_history() -> None:
    """Render all existing messages from session state chat history."""
    for msg in st.session_state.chat_history:
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        report = msg.get("report")

        with st.chat_message(role):
            if content:
                st.markdown(content)
            if report:
                with st.expander("View Analysis Report"):
                    from ui.components.report_card import render_full_report
                    render_full_report(report)


def _stream_response(query: str) -> None:
    """Stream an assistant response from the SSE endpoint and update the UI.

    Opens a streaming HTTP connection to /stream/chat, parses SSE events,
    and incrementally updates a placeholder with the typed response.
    On completion, saves the accumulated text and optional report to
    session state chat history.

    Args:
        query: The user query string to send to the API.
    """
    if not st.session_state.thread_id:
        st.session_state.thread_id = str(uuid.uuid4())

    accumulated_text = ""
    st.session_state.is_streaming = True
    report = None

    with st.chat_message("assistant"):
        text_placeholder = st.empty()
        status_container = st.container()

        try:
            with httpx.Client(
                timeout=httpx.Timeout(300.0, connect=10.0)
            ) as client:
                with client.stream(
                    "GET",
                    f"{st.session_state.api_base_url}/stream/chat",
                    params={
                        "query": query,
                        "thread_id": st.session_state.thread_id,
                    },
                ) as response:
                    response.raise_for_status()

                    buffer = ""
                    active_statuses: dict[str, st.delta_generator.DeltaGenerator] = {}

                    for chunk in response.iter_text():
                        buffer += chunk

                        # SSE events are separated by double newlines
                        while "\n\n" in buffer:
                            event_str, buffer = buffer.split("\n\n", 1)
                            _process_sse_event(
                                event_str,
                                text_placeholder,
                                status_container,
                                active_statuses,
                            )
                            # Retrieve updated state from event processing
                            accumulated_text = st.session_state.get(
                                "_stream_accumulated", accumulated_text
                            )
                            new_report = st.session_state.pop("_stream_report", None)
                            if new_report is not None:
                                report = new_report

            # Finalize display — remove cursor
            if accumulated_text:
                text_placeholder.markdown(accumulated_text)
            elif not report:
                text_placeholder.markdown("_(No text response received)_")

            if report:
                st.session_state.current_report = report
                with st.expander("View Analysis Report", expanded=True):
                    from ui.components.report_card import render_full_report
                    render_full_report(report)

        except httpx.ConnectError:
            st.error(
                "Cannot connect to the backend server. "
                "Please ensure it is running with: "
                "`uv run uvicorn api.main:app --reload`"
            )
        except httpx.TimeoutException:
            st.error(
                "Request timed out. The analysis may be taking longer than expected. "
                "Please try again."
            )
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 404:
                st.error(
                    "The streaming endpoint `/stream/chat` was not found on the backend. "
                    "Please check that the API version supports SSE streaming."
                )
            else:
                st.error(f"Server error {status_code}: {e.response.text[:300]}")
        except Exception as e:
            st.error(f"Unexpected error during streaming: {str(e)[:300]}")
        finally:
            # Clean up temporary session state keys
            st.session_state.pop("_stream_accumulated", None)
            st.session_state.pop("_stream_report", None)
            st.session_state.is_streaming = False

    # Save completed message to history
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": accumulated_text,
            "report": report,
        }
    )


def _process_sse_event(
    event_str: str,
    text_placeholder,
    status_container,
    active_statuses: dict,
) -> None:
    """Parse and handle a single SSE event block.

    Mutates session state keys _stream_accumulated and _stream_report
    as side effects so _stream_response can read updated values.

    Args:
        event_str: Raw SSE event block string (multiple "key: value" lines).
        text_placeholder: Streamlit empty() container for incremental text.
        status_container: Streamlit container for status indicators.
        active_statuses: Dict tracking agent -> status widget references.
    """
    accumulated_text = st.session_state.get("_stream_accumulated", "")

    for line in event_str.split("\n"):
        if not line.startswith("data: "):
            continue

        data_str = line[6:].strip()
        if not data_str or data_str == "[DONE]":
            continue

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            # Treat as raw text token if not JSON
            accumulated_text += data_str
            text_placeholder.markdown(accumulated_text + "▌")
            st.session_state["_stream_accumulated"] = accumulated_text
            continue

        event_type = data.get("type", "")
        content = data.get("content", "")
        agent = data.get("agent", "")

        if event_type == "status":
            display_name = AGENT_DISPLAY_NAMES.get(agent, agent.replace("_", " ").title())
            icon = AGENT_STEP_ICONS.get(agent, "")
            status_label = f"{icon} {display_name}: {content}" if icon else f"{display_name}: {content}"
            with status_container:
                st.status(status_label, state="running")

        elif event_type == "token":
            token = content if isinstance(content, str) else ""
            accumulated_text += token
            text_placeholder.markdown(accumulated_text + "▌")
            st.session_state["_stream_accumulated"] = accumulated_text

        elif event_type == "result":
            if isinstance(content, dict):
                st.session_state["_stream_report"] = content
            elif isinstance(content, str) and content.strip():
                try:
                    parsed = json.loads(content)
                    st.session_state["_stream_report"] = parsed
                except json.JSONDecodeError:
                    # Treat as final text, not a report
                    accumulated_text += content
                    st.session_state["_stream_accumulated"] = accumulated_text

        elif event_type == "error":
            error_msg = content if isinstance(content, str) else str(content)
            with status_container:
                st.error(f"Agent error: {error_msg}")

        elif event_type == "done":
            # Stream completed normally
            pass

    # Ensure final accumulated text is stored
    if "_stream_accumulated" not in st.session_state:
        st.session_state["_stream_accumulated"] = accumulated_text
