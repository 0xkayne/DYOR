"""Tests for the RAG agent."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.rag_agent import RAGAgent, _rag_agent, rag_agent_node


def _make_retrieval_result(content, source, project, chunk_idx, score):
    r = MagicMock()
    r.content = content
    r.source = source
    r.project_name = project
    r.chunk_index = chunk_idx
    r.relevance_score = score
    return r


class TestRAGAgentRetrieve:
    @pytest.mark.asyncio
    async def test_retrieve_returns_formatted(self):
        formatted = {
            "results": [
                {
                    "content": "content1",
                    "source": "src.md",
                    "project_name": "Test",
                    "relevance_score": 0.9,
                }
            ],
            "sources": ["src.md"],
            "query": "test",
        }
        with patch.object(
            _rag_agent, "_retrieve", new_callable=AsyncMock, return_value=formatted
        ):
            res = await _rag_agent.invoke("test", ["Test"])
        assert len(res["results"]) == 1
        assert res["results"][0]["source"] == "src.md"

    @pytest.mark.asyncio
    async def test_timeout_returns_empty(self):
        with patch.object(
            _rag_agent, "_retrieve", new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            res = await _rag_agent.invoke("test", [])
        assert res["results"] == []
        assert res["sources"] == []

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self):
        with patch.object(
            _rag_agent, "_retrieve", new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            res = await _rag_agent.invoke("test", [])
        assert res["results"] == []


class TestRAGAgentNode:
    @pytest.mark.asyncio
    async def test_node_returns_rag_result(self):
        with patch.object(
            _rag_agent, "invoke", new_callable=AsyncMock,
            return_value={"results": [], "sources": [], "query": "test"},
        ):
            state = {"user_query": "test", "target_entities": []}
            res = await rag_agent_node(state)
        assert "rag_result" in res

    @pytest.mark.asyncio
    async def test_node_empty_query_returns_none(self):
        state = {"user_query": "", "target_entities": []}
        res = await rag_agent_node(state)
        assert res["rag_result"] is None
