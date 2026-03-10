"""Tests for the market agent."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.market_agent import MarketAgent, _market_agent, market_agent_node, _resolve_coin_id


class TestCoinIdResolve:
    @pytest.mark.asyncio
    async def test_known_mapping(self):
        assert await _resolve_coin_id("ARB") == "arbitrum"
        assert await _resolve_coin_id("Bitcoin") == "bitcoin"

    @pytest.mark.asyncio
    async def test_unknown_passthrough(self):
        with patch(
            "src.mcp_servers.market_server.resolve_coin_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            assert await _resolve_coin_id("unknowntoken") == "unknowntoken"


class TestMarketAgentInvoke:
    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        with (
            patch(
                "src.agents.market_agent.get_price",
                new_callable=AsyncMock,
                return_value={"current_price": 1.25},
            ),
            patch(
                "src.agents.market_agent.calculate_technical_indicators",
                new_callable=AsyncMock,
                return_value={"rsi": 55},
            ),
            patch(
                "src.agents.market_agent.get_market_overview",
                new_callable=AsyncMock,
                return_value={"total_market_cap": 2.5e12},
            ),
        ):
            result = await _market_agent.invoke(["Arbitrum"])
        assert "entities" in result
        assert "Arbitrum" in result["entities"]
        assert result["market_overview"] is not None

    @pytest.mark.asyncio
    async def test_partial_tool_failure(self):
        with (
            patch(
                "src.agents.market_agent.get_price",
                new_callable=AsyncMock,
                side_effect=Exception("API error"),
            ),
            patch(
                "src.agents.market_agent.calculate_technical_indicators",
                new_callable=AsyncMock,
                return_value={"rsi": 55},
            ),
            patch(
                "src.agents.market_agent.get_market_overview",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await _market_agent.invoke(["Arbitrum"])
        assert "entities" in result
        entity_data = result["entities"]["Arbitrum"]
        assert "error" in entity_data.get("price", {})

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self):
        with patch.object(
            _market_agent, "_fetch_all", new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            result = await _market_agent.invoke(["Arbitrum"])
        assert result["market_overview"] is None
        assert "error" in result["entities"]["Arbitrum"]


class TestMarketAgentNode:
    @pytest.mark.asyncio
    async def test_node_no_entities(self):
        state = {"target_entities": []}
        result = await market_agent_node(state)
        assert result["market_data"] is None

    @pytest.mark.asyncio
    async def test_node_with_entities(self):
        with patch.object(
            _market_agent, "invoke", new_callable=AsyncMock,
            return_value={"entities": {}, "market_overview": None},
        ):
            state = {"target_entities": ["Arbitrum"]}
            result = await market_agent_node(state)
        assert result["market_data"] is not None
