"""Tests for the streaming middleware.

Covers:
- StreamMessage Pydantic model construction and validation
- _agent_from_name() normalisation helper
- langgraph_event_to_messages() event conversion
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from api.middleware.streaming import (
    StreamMessage,
    _agent_from_name,
    langgraph_event_to_messages,
)


# ---------------------------------------------------------------------------
# StreamMessage model
# ---------------------------------------------------------------------------


class TestStreamMessage:
    def test_valid_status_construction(self) -> None:
        """StreamMessage with type='status' is accepted."""
        msg = StreamMessage(
            type="status",
            agent="router",
            content="started",
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert msg.type == "status"
        assert msg.agent == "router"
        assert msg.content == "started"

    def test_valid_token_construction(self) -> None:
        """StreamMessage with type='token' is accepted."""
        msg = StreamMessage(
            type="token",
            agent="analyst",
            content="hello",
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert msg.type == "token"

    def test_valid_result_construction(self) -> None:
        """StreamMessage with type='result' is accepted."""
        msg = StreamMessage(
            type="result",
            agent="workflow",
            content='{"final": true}',
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert msg.type == "result"

    def test_valid_error_construction(self) -> None:
        """StreamMessage with type='error' is accepted."""
        msg = StreamMessage(
            type="error",
            agent="system",
            content="something broke",
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert msg.type == "error"

    def test_invalid_type_raises_validation_error(self) -> None:
        """StreamMessage with an unknown type raises ValidationError."""
        with pytest.raises(ValidationError):
            StreamMessage(
                type="invalid",
                agent="router",
                content="test",
                timestamp=datetime.now(tz=timezone.utc),
            )

    def test_missing_required_field_raises_validation_error(self) -> None:
        """StreamMessage without a required field raises ValidationError."""
        with pytest.raises(ValidationError):
            StreamMessage(  # type: ignore[call-arg]
                type="status",
                agent="router",
                # 'content' and 'timestamp' intentionally omitted
            )

    def test_serialization_preserves_all_fields(self) -> None:
        """model_dump() round-trips all fields."""
        ts = datetime.now(tz=timezone.utc)
        msg = StreamMessage(type="token", agent="analyst", content="hello", timestamp=ts)
        data = msg.model_dump()
        assert data["type"] == "token"
        assert data["agent"] == "analyst"
        assert data["content"] == "hello"
        assert data["timestamp"] == ts

    def test_model_dump_json_mode(self) -> None:
        """model_dump(mode='json') serialises datetime to ISO string."""
        msg = StreamMessage(
            type="status",
            agent="planner",
            content="ok",
            timestamp=datetime.now(tz=timezone.utc),
        )
        data = msg.model_dump(mode="json")
        assert isinstance(data["timestamp"], str)


# ---------------------------------------------------------------------------
# _agent_from_name
# ---------------------------------------------------------------------------


class TestAgentFromName:
    def test_exact_match_router(self) -> None:
        assert _agent_from_name("router") == "router"

    def test_exact_match_analyst(self) -> None:
        assert _agent_from_name("analyst") == "analyst"

    def test_exact_match_critic(self) -> None:
        assert _agent_from_name("critic") == "critic"

    def test_exact_match_planner(self) -> None:
        assert _agent_from_name("planner") == "planner"

    def test_exact_match_rag(self) -> None:
        assert _agent_from_name("rag") == "rag"

    def test_exact_match_market(self) -> None:
        assert _agent_from_name("market") == "market"

    def test_exact_match_news(self) -> None:
        assert _agent_from_name("news") == "news"

    def test_exact_match_tokenomics(self) -> None:
        assert _agent_from_name("tokenomics") == "tokenomics"

    def test_prefixed_name_run_router(self) -> None:
        """'run_router' should resolve to 'router'."""
        assert _agent_from_name("run_router") == "router"

    def test_suffixed_name_analyst_node(self) -> None:
        """'AnalystNode' should resolve to 'analyst' (case-insensitive key lookup)."""
        assert _agent_from_name("AnalystNode") == "analyst"

    def test_unknown_name_lowercased(self) -> None:
        """An unrecognised name is returned lowercased."""
        result = _agent_from_name("UnknownAgent")
        assert result == "unknownagent"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        result = _agent_from_name("")
        assert result == ""

    def test_case_insensitive_key_matching(self) -> None:
        """Keys are matched case-insensitively via lower()."""
        assert _agent_from_name("ROUTER") == "router"
        assert _agent_from_name("Planner") == "planner"


# ---------------------------------------------------------------------------
# langgraph_event_to_messages
# ---------------------------------------------------------------------------


class TestLanggraphEventToMessages:
    # --- on_chain_start ---

    def test_chain_start_produces_status_message(self) -> None:
        event = {"event": "on_chain_start", "name": "router"}
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 1
        assert messages[0].type == "status"
        assert messages[0].agent == "router"

    def test_chain_start_content_contains_name(self) -> None:
        event = {"event": "on_chain_start", "name": "planner"}
        messages = langgraph_event_to_messages(event)
        assert "planner" in messages[0].content.lower()

    def test_chain_start_unknown_agent(self) -> None:
        event = {"event": "on_chain_start", "name": "mystery_node"}
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 1
        assert messages[0].type == "status"

    # --- on_chain_end (top-level) ---

    def test_chain_end_top_level_produces_result(self) -> None:
        event = {
            "event": "on_chain_end",
            "name": "workflow",
            "parent_ids": [],
            "data": {"output": {"result": "done"}},
        }
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 1
        assert messages[0].type == "result"

    def test_chain_end_top_level_dict_output_serialised(self) -> None:
        """Dict output is JSON-serialised into the content field."""
        event = {
            "event": "on_chain_end",
            "name": "workflow",
            "parent_ids": [],
            "data": {"output": {"key": "value"}},
        }
        messages = langgraph_event_to_messages(event)
        import json as _json
        content = messages[0].content
        parsed = _json.loads(content)
        assert parsed["key"] == "value"

    def test_chain_end_top_level_string_output(self) -> None:
        """Non-dict, non-empty output is str()-converted into content."""
        event = {
            "event": "on_chain_end",
            "name": "workflow",
            "parent_ids": [],
            "data": {"output": "plain string"},
        }
        messages = langgraph_event_to_messages(event)
        assert messages[0].content == "plain string"

    def test_chain_end_top_level_empty_output_uses_fallback(self) -> None:
        """Empty/falsy output falls back to '{name} completed'."""
        event = {
            "event": "on_chain_end",
            "name": "workflow",
            "parent_ids": [],
            "data": {"output": ""},
        }
        messages = langgraph_event_to_messages(event)
        assert "completed" in messages[0].content.lower()

    def test_chain_end_nested_ignored(self) -> None:
        """on_chain_end with non-empty parent_ids is ignored (returns empty list)."""
        event = {
            "event": "on_chain_end",
            "name": "sub",
            "parent_ids": ["parent1"],
            "data": {"output": "x"},
        }
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 0

    def test_chain_end_multiple_parents_ignored(self) -> None:
        """on_chain_end with multiple parents is still ignored."""
        event = {
            "event": "on_chain_end",
            "name": "sub",
            "parent_ids": ["p1", "p2"],
            "data": {"output": "x"},
        }
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 0

    # --- on_chat_model_stream ---

    def test_chat_model_stream_with_text_produces_token(self) -> None:
        chunk = MagicMock()
        chunk.content = "hello"
        event = {
            "event": "on_chat_model_stream",
            "name": "analyst",
            "data": {"chunk": chunk},
        }
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 1
        assert messages[0].type == "token"
        assert messages[0].content == "hello"
        assert messages[0].agent == "analyst"

    def test_chat_model_stream_empty_content_produces_no_message(self) -> None:
        """Empty token text should not produce a StreamMessage."""
        chunk = MagicMock()
        chunk.content = ""
        event = {
            "event": "on_chat_model_stream",
            "name": "analyst",
            "data": {"chunk": chunk},
        }
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 0

    def test_chat_model_stream_none_chunk(self) -> None:
        """None chunk should produce no message (not raise)."""
        event = {
            "event": "on_chat_model_stream",
            "name": "analyst",
            "data": {"chunk": None},
        }
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 0

    def test_chat_model_stream_list_content(self) -> None:
        """List-type content blocks should be concatenated into a single token."""
        chunk = MagicMock()
        chunk.content = [{"text": "foo"}, {"text": " bar"}]
        event = {
            "event": "on_chat_model_stream",
            "name": "analyst",
            "data": {"chunk": chunk},
        }
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 1
        assert messages[0].content == "foo bar"

    def test_chat_model_stream_mixed_list_content(self) -> None:
        """List blocks without 'text' key fall back to str()."""
        chunk = MagicMock()
        chunk.content = [{"text": "hello"}, "raw_string_block"]
        event = {
            "event": "on_chat_model_stream",
            "name": "analyst",
            "data": {"chunk": chunk},
        }
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 1
        assert "hello" in messages[0].content

    # --- unknown / other events ---

    def test_unknown_event_produces_no_messages(self) -> None:
        event = {"event": "on_something_else", "name": "test"}
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 0

    def test_missing_event_key_produces_no_messages(self) -> None:
        """A dict without an 'event' key should not raise and return empty."""
        messages = langgraph_event_to_messages({"name": "test"})
        assert len(messages) == 0

    def test_all_messages_have_utc_timestamps(self) -> None:
        """Every emitted StreamMessage carries a timezone-aware UTC timestamp."""
        event = {"event": "on_chain_start", "name": "planner"}
        messages = langgraph_event_to_messages(event)
        assert len(messages) == 1
        ts = messages[0].timestamp
        assert ts.tzinfo is not None
