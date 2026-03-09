"""Tests for the tokenomics agent."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.tokenomics_agent import (
    TokenomicsAgent,
    _tokenomics_agent,
    tokenomics_agent_node,
    _resolve_symbol,
)


class TestSymbolResolve:
    def test_known_mapping(self):
        assert _resolve_symbol("arbitrum") == "ARB"
        assert _resolve_symbol("bitcoin") == "BTC"

    def test_unknown_uppercases(self):
        assert _resolve_symbol("unknowntoken") == "UNKNOWNTOKEN"


class TestTokenomicsAgentInvoke:
    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        with (
            patch(
                "src.agents.tokenomics_agent.get_unlock_schedule",
                new_callable=AsyncMock,
                return_value={"schedule": []},
            ),
            patch(
                "src.agents.tokenomics_agent.get_token_distribution",
                new_callable=AsyncMock,
                return_value={"distribution": {}},
            ),
        ):
            result = await _tokenomics_agent.invoke(["Arbitrum"])
        assert "entities" in result
        assert "Arbitrum" in result["entities"]

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        with (
            patch(
                "src.agents.tokenomics_agent.get_unlock_schedule",
                new_callable=AsyncMock,
                side_effect=Exception("err"),
            ),
            patch(
                "src.agents.tokenomics_agent.get_token_distribution",
                new_callable=AsyncMock,
                return_value={"distribution": {}},
            ),
        ):
            result = await _tokenomics_agent.invoke(["Arbitrum"])
        entity_data = result["entities"]["Arbitrum"]
        assert "error" in entity_data.get("unlock_schedule", {})

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self):
        with patch.object(
            _tokenomics_agent, "_fetch_all", new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            result = await _tokenomics_agent.invoke(["Arbitrum"])
        assert "error" in result["entities"]["Arbitrum"]


class TestTokenomicsAgentNode:
    @pytest.mark.asyncio
    async def test_node_no_entities(self):
        state = {"target_entities": []}
        result = await tokenomics_agent_node(state)
        assert result["tokenomics_data"] is None

    @pytest.mark.asyncio
    async def test_node_with_entities(self):
        with patch.object(
            _tokenomics_agent, "invoke", new_callable=AsyncMock,
            return_value={"entities": {}},
        ):
            state = {"target_entities": ["Arbitrum"]}
            result = await tokenomics_agent_node(state)
        assert result["tokenomics_data"] is not None
