"""Tests for the planner agent."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.planner import PlannerAgent, _planner, planner_node, _FALLBACK_PLANS


class TestPlannerLLM:
    @pytest.mark.asyncio
    async def test_llm_returns_valid_plan(self):
        """LLM returning valid agent names should produce a valid plan."""
        with patch.object(
            _planner, "_call_llm", new_callable=AsyncMock,
            return_value=["rag_agent", "market_agent"],
        ):
            result = await _planner.invoke("deep_dive", "分析 Arbitrum")
        assert result == ["rag_agent", "market_agent"]

    @pytest.mark.asyncio
    async def test_short_names_normalized(self):
        """Short names like 'rag' should be normalized to 'rag_agent'."""
        with patch.object(
            _planner, "_call_llm", new_callable=AsyncMock,
            return_value=["rag_agent", "market_agent", "news_agent"],
        ):
            result = await _planner.invoke("deep_dive", "test")
        assert all(a.endswith("_agent") for a in result)

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self):
        """Timeout should return fallback plan."""
        with patch.object(
            _planner, "_call_llm", new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            result = await _planner.invoke("deep_dive", "test")
        assert result == _FALLBACK_PLANS["deep_dive"]

    @pytest.mark.asyncio
    async def test_exception_returns_fallback(self):
        """Exception should return fallback plan."""
        with patch.object(
            _planner, "_call_llm", new_callable=AsyncMock,
            side_effect=Exception("LLM error"),
        ):
            result = await _planner.invoke("deep_dive", "test")
        assert result == _FALLBACK_PLANS["deep_dive"]


class TestPlannerFallback:
    def test_deep_dive_fallback(self):
        assert _planner._fallback("deep_dive") == [
            "rag_agent", "market_agent", "news_agent", "tokenomics_agent"
        ]

    def test_qa_fallback(self):
        assert _planner._fallback("qa") == ["rag_agent"]

    def test_brief_fallback(self):
        assert _planner._fallback("brief") == ["rag_agent", "market_agent"]

    def test_unknown_fallback(self):
        assert _planner._fallback("unknown") == ["rag_agent"]


class TestPlannerNode:
    @pytest.mark.asyncio
    async def test_planner_node_returns_plan(self):
        with patch.object(
            _planner, "invoke", new_callable=AsyncMock,
            return_value=["rag_agent"],
        ):
            state = {"workflow_type": "qa", "user_query": "test"}
            result = await planner_node(state)
        assert "execution_plan" in result
        assert result["execution_plan"] == ["rag_agent"]
