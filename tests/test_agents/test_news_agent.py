"""Tests for the news agent."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.news_agent import NewsAgent, _news_agent, news_agent_node, _resolve_ticker


class TestTickerResolve:
    def test_known_mapping(self):
        assert _resolve_ticker("arbitrum") == "ARB"
        assert _resolve_ticker("bitcoin") == "BTC"

    def test_unknown_uppercases(self):
        assert _resolve_ticker("unknowntoken") == "UNKNOWNTOKEN"


class TestNewsAgentInvoke:
    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        with (
            patch(
                "src.agents.news_agent.search_news",
                new_callable=AsyncMock,
                return_value={"news": [{"title": "test"}]},
            ),
            patch(
                "src.agents.news_agent.analyze_sentiment",
                new_callable=AsyncMock,
                return_value={"overall_sentiment": "positive"},
            ),
        ):
            result = await _news_agent.invoke(["Arbitrum"])
        assert "entities" in result
        assert "Arbitrum" in result["entities"]

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        with (
            patch(
                "src.agents.news_agent.search_news",
                new_callable=AsyncMock,
                side_effect=Exception("err"),
            ),
            patch(
                "src.agents.news_agent.analyze_sentiment",
                new_callable=AsyncMock,
                return_value={"sentiment": "neutral"},
            ),
        ):
            result = await _news_agent.invoke(["Arbitrum"])
        entity_data = result["entities"]["Arbitrum"]
        assert "error" in entity_data.get("news", {})

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self):
        with patch.object(
            _news_agent, "_fetch_all", new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            result = await _news_agent.invoke(["Arbitrum"])
        assert "error" in result["entities"]["Arbitrum"]


class TestNewsAgentNode:
    @pytest.mark.asyncio
    async def test_node_no_entities(self):
        state = {"target_entities": []}
        result = await news_agent_node(state)
        assert result["news_data"] is None

    @pytest.mark.asyncio
    async def test_node_with_entities(self):
        with patch.object(
            _news_agent, "invoke", new_callable=AsyncMock,
            return_value={"entities": {}},
        ):
            state = {"target_entities": ["Arbitrum"]}
            result = await news_agent_node(state)
        assert result["news_data"] is not None
