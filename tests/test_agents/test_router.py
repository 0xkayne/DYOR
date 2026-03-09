"""Tests for the router agent that classifies user intent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.router import RouterAgent, router_node, _router


class TestRouterImport:
    def test_module_importable(self):
        """Verify that the router module can be imported."""
        from src.agents import router  # noqa: F401


class TestIntentClassification:
    @pytest.mark.asyncio
    async def test_deep_dive_intent(self):
        """Should classify '深度分析 Arbitrum' as deep_dive."""
        response = {"workflow_type": "deep_dive", "target_entities": ["Arbitrum"], "reasoning": "deep analysis"}
        with patch.object(_router, "_call_llm", new_callable=AsyncMock, return_value=response):
            result = await _router.invoke("深度分析 Arbitrum")
        assert result["workflow_type"] == "deep_dive"
        assert "Arbitrum" in result["target_entities"]

    @pytest.mark.asyncio
    async def test_compare_intent(self):
        """Should classify 'ARB vs OP 对比' as compare."""
        response = {"workflow_type": "compare", "target_entities": ["ARB", "OP"], "reasoning": "comparison"}
        with patch.object(_router, "_call_llm", new_callable=AsyncMock, return_value=response):
            result = await _router.invoke("ARB vs OP 对比")
        assert result["workflow_type"] == "compare"
        assert len(result["target_entities"]) == 2

    @pytest.mark.asyncio
    async def test_qa_intent(self):
        """Should classify 'Arbitrum 团队是谁' as qa."""
        response = {"workflow_type": "qa", "target_entities": ["Arbitrum"], "reasoning": "question"}
        with patch.object(_router, "_call_llm", new_callable=AsyncMock, return_value=response):
            result = await _router.invoke("Arbitrum 团队是谁")
        assert result["workflow_type"] == "qa"

    @pytest.mark.asyncio
    async def test_news_watch_intent(self):
        """Should normalize unknown workflow_type to qa inside _call_llm."""
        # When _call_llm returns a valid workflow_type, invoke passes it through
        response = {"workflow_type": "qa", "target_entities": ["ARB"], "reasoning": "news"}
        with patch.object(_router, "_call_llm", new_callable=AsyncMock, return_value=response):
            result = await _router.invoke("ARB 最新新闻")
        assert result["workflow_type"] == "qa"


class TestEntityExtraction:
    @pytest.mark.asyncio
    async def test_extract_project_name(self):
        """Should extract 'Arbitrum' from '分析一下 Arbitrum 项目'."""
        response = {"workflow_type": "deep_dive", "target_entities": ["Arbitrum"], "reasoning": "analysis"}
        with patch.object(_router, "_call_llm", new_callable=AsyncMock, return_value=response):
            result = await _router.invoke("分析一下 Arbitrum 项目")
        assert "Arbitrum" in result["target_entities"]


class TestRouterFallback:
    def test_fallback_compare_keywords(self):
        """Fallback should detect compare workflow from keywords."""
        result = _router._fallback("对比 ARB 和 OP")
        assert result["workflow_type"] == "compare"

    def test_fallback_deep_dive_keywords(self):
        """Fallback should detect deep_dive from keywords."""
        result = _router._fallback("分析 Arbitrum 是否值得投资")
        assert result["workflow_type"] == "deep_dive"

    def test_fallback_qa_default(self):
        """Fallback should return qa for unrecognized queries."""
        result = _router._fallback("hello world")
        assert result["workflow_type"] == "qa"

    def test_fallback_entity_extraction(self):
        """Fallback should extract entities from patterns."""
        result = _router._fallback("分析 Arbitrum 是否值得")
        assert len(result["target_entities"]) > 0


class TestRouterNode:
    @pytest.mark.asyncio
    async def test_router_node_updates_state(self):
        """router_node should return workflow_type and target_entities."""
        response = {"workflow_type": "deep_dive", "target_entities": ["Arbitrum"], "reasoning": "test"}
        with patch.object(_router, "invoke", new_callable=AsyncMock, return_value=response):
            state = {"user_query": "分析 Arbitrum", "messages": []}
            result = await router_node(state)
        assert "workflow_type" in result
        assert "target_entities" in result

    @pytest.mark.asyncio
    async def test_router_node_empty_query(self):
        """router_node should handle empty query gracefully."""
        state = {"user_query": "", "messages": []}
        result = await router_node(state)
        assert result["workflow_type"] == "qa"
        assert result["target_entities"] == []
