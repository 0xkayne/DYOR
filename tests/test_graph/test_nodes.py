"""Tests for graph node wrapper functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.nodes import (
    run_analyst,
    run_critic,
    run_market_agent,
    run_news_agent,
    run_planner,
    run_rag_agent,
    run_router,
    run_tokenomics_agent,
)


class TestRunRouter:
    @pytest.mark.asyncio
    async def test_delegates_to_router_node(self):
        expected = {"workflow_type": "qa", "target_entities": []}
        with patch("src.graph.nodes.router_node", new_callable=AsyncMock, return_value=expected):
            result = await run_router({"user_query": "test", "messages": []})
        assert result == expected


class TestRunPlanner:
    @pytest.mark.asyncio
    async def test_delegates_to_planner_node(self):
        expected = {"execution_plan": ["rag_agent"]}
        with patch("src.graph.nodes.planner_node", new_callable=AsyncMock, return_value=expected):
            result = await run_planner({"workflow_type": "qa", "user_query": "test"})
        assert result == expected


class TestRunRagAgent:
    @pytest.mark.asyncio
    async def test_delegates_to_rag_agent_node(self):
        expected = {"rag_result": {"results": []}}
        with patch("src.graph.nodes.rag_agent_node", new_callable=AsyncMock, return_value=expected):
            result = await run_rag_agent({"user_query": "test", "target_entities": []})
        assert result == expected


class TestRunMarketAgent:
    @pytest.mark.asyncio
    async def test_delegates_to_market_agent_node(self):
        expected = {"market_data": {}}
        with patch("src.graph.nodes.market_agent_node", new_callable=AsyncMock, return_value=expected):
            result = await run_market_agent({"target_entities": ["Arbitrum"]})
        assert result == expected


class TestRunNewsAgent:
    @pytest.mark.asyncio
    async def test_delegates_to_news_agent_node(self):
        expected = {"news_data": {}}
        with patch("src.graph.nodes.news_agent_node", new_callable=AsyncMock, return_value=expected):
            result = await run_news_agent({"target_entities": ["Arbitrum"]})
        assert result == expected


class TestRunTokenomicsAgent:
    @pytest.mark.asyncio
    async def test_delegates_to_tokenomics_agent_node(self):
        expected = {"tokenomics_data": {}}
        with patch("src.graph.nodes.tokenomics_agent_node", new_callable=AsyncMock, return_value=expected):
            result = await run_tokenomics_agent({"target_entities": ["Arbitrum"]})
        assert result == expected


class TestRunAnalyst:
    @pytest.mark.asyncio
    async def test_delegates_to_analyst_node(self):
        expected = {"analysis_report": {"project_name": "Test"}}
        with patch("src.graph.nodes.analyst_node", new_callable=AsyncMock, return_value=expected):
            result = await run_analyst({"user_query": "test"})
        assert result == expected


class TestRunCritic:
    @pytest.mark.asyncio
    async def test_delegates_to_critic_node(self):
        expected = {"critic_approved": True, "critic_feedback": "", "revision_count": 0}
        with patch("src.graph.nodes.critic_node", new_callable=AsyncMock, return_value=expected):
            result = await run_critic({"analysis_report": {}})
        assert result == expected
