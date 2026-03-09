"""Tests for the LangGraph multi-agent workflow."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.graph.workflow import build_workflow, compile_workflow


class TestWorkflowImport:
    def test_state_module_importable(self):
        from src.graph import state  # noqa: F401

    def test_workflow_module_importable(self):
        from src.graph import workflow  # noqa: F401


MOCK_ROUTER_RESULT = {"workflow_type": "deep_dive", "target_entities": ["Arbitrum"], "reasoning": "test"}
MOCK_PLANNER_RESULT = ["rag_agent", "market_agent", "news_agent", "tokenomics_agent"]
MOCK_RAG_RESULT = {"results": [{"content": "Arbitrum is L2", "source": "arb.md", "project_name": "Arbitrum", "relevance_score": 0.8}], "sources": ["arb.md"], "query": "test"}
MOCK_MARKET_RESULT = {"entities": {"Arbitrum": {"coin_id": "arbitrum", "price": {"current_price": 1.25}}}, "market_overview": None}
MOCK_NEWS_RESULT = {"entities": {"Arbitrum": {"ticker": "ARB", "news": {"news": []}, "sentiment": {"overall_sentiment": "neutral"}}}}
MOCK_TOKENOMICS_RESULT = {"entities": {"Arbitrum": {"symbol": "ARB", "unlock_schedule": {}, "distribution": {}}}}

MOCK_ANALYST_REPORT = {
    "project_name": "Arbitrum",
    "analysis_date": "2026-03-09T00:00:00",
    "workflow_type": "deep_dive",
    "fundamental_analysis": {
        "summary": "Arbitrum is a leading L2.",
        "team_score": 8.0, "product_score": 7.5, "track_score": 8.0, "tokenomics_score": 6.5,
        "sources": ["arb.md"],
    },
    "market_data": None, "news_sentiment": None, "tokenomics": None,
    "investment_recommendation": {
        "rating": "buy", "confidence": 0.65,
        "key_reasons": ["Strong ecosystem", "Active dev"],
        "risk_factors": ["Token unlocks", "Competition"],
        "disclaimer": "Not financial advice. DYOR.",
    },
}

MOCK_CRITIC_APPROVE = {"approved": True, "feedback": "Good report.", "issues": []}


def _get_initial_state():
    return {
        "messages": [], "user_query": "分析 Arbitrum", "workflow_type": "",
        "target_entities": [], "execution_plan": [],
        "rag_result": None, "market_data": None, "news_data": None, "tokenomics_data": None,
        "analysis_report": None, "critic_feedback": None, "critic_approved": False, "revision_count": 0,
    }


class TestDeepDiveWorkflow:
    @pytest.mark.asyncio
    async def test_deep_dive_output_has_required_fields(self):
        """Deep dive should produce analysis_report with required fields."""
        with (
            patch("src.agents.router.RouterAgent._call_llm", new_callable=AsyncMock, return_value=MOCK_ROUTER_RESULT),
            patch("src.agents.planner.PlannerAgent._call_llm", new_callable=AsyncMock, return_value=MOCK_PLANNER_RESULT),
            patch("src.agents.analyst.AnalystAgent._generate", new_callable=AsyncMock, return_value=MOCK_ANALYST_REPORT),
            patch("src.agents.critic.CriticAgent._review", new_callable=AsyncMock, return_value=MOCK_CRITIC_APPROVE),
            patch("src.agents.rag_agent._rag_agent._retrieve", new_callable=AsyncMock, return_value=MOCK_RAG_RESULT),
            patch("src.agents.market_agent.get_price", new_callable=AsyncMock, return_value={"current_price": 1.25}),
            patch("src.agents.market_agent.calculate_technical_indicators", new_callable=AsyncMock, return_value={}),
            patch("src.agents.market_agent.get_market_overview", new_callable=AsyncMock, return_value={}),
            patch("src.agents.news_agent.search_news", new_callable=AsyncMock, return_value={"news": []}),
            patch("src.agents.news_agent.analyze_sentiment", new_callable=AsyncMock, return_value={"overall_sentiment": "neutral"}),
            patch("src.agents.tokenomics_agent.get_unlock_schedule", new_callable=AsyncMock, return_value={}),
            patch("src.agents.tokenomics_agent.get_token_distribution", new_callable=AsyncMock, return_value={}),
        ):
            app = compile_workflow()
            result = await app.ainvoke(_get_initial_state(), config={"configurable": {"thread_id": "test_dd_01"}})

        assert result is not None
        report = result.get("analysis_report")
        assert report is not None
        assert "project_name" in report
        assert "investment_recommendation" in report

    @pytest.mark.asyncio
    async def test_deep_dive_calls_all_agents(self):
        """Deep dive should set all agent result keys in state."""
        with (
            patch("src.agents.router.RouterAgent._call_llm", new_callable=AsyncMock, return_value=MOCK_ROUTER_RESULT),
            patch("src.agents.planner.PlannerAgent._call_llm", new_callable=AsyncMock, return_value=MOCK_PLANNER_RESULT),
            patch("src.agents.analyst.AnalystAgent._generate", new_callable=AsyncMock, return_value=MOCK_ANALYST_REPORT),
            patch("src.agents.critic.CriticAgent._review", new_callable=AsyncMock, return_value=MOCK_CRITIC_APPROVE),
            patch("src.agents.rag_agent._rag_agent._retrieve", new_callable=AsyncMock, return_value=MOCK_RAG_RESULT),
            patch("src.agents.market_agent.get_price", new_callable=AsyncMock, return_value={"current_price": 1.25}),
            patch("src.agents.market_agent.calculate_technical_indicators", new_callable=AsyncMock, return_value={}),
            patch("src.agents.market_agent.get_market_overview", new_callable=AsyncMock, return_value={}),
            patch("src.agents.news_agent.search_news", new_callable=AsyncMock, return_value={"news": []}),
            patch("src.agents.news_agent.analyze_sentiment", new_callable=AsyncMock, return_value={"overall_sentiment": "neutral"}),
            patch("src.agents.tokenomics_agent.get_unlock_schedule", new_callable=AsyncMock, return_value={}),
            patch("src.agents.tokenomics_agent.get_token_distribution", new_callable=AsyncMock, return_value={}),
        ):
            app = compile_workflow()
            result = await app.ainvoke(_get_initial_state(), config={"configurable": {"thread_id": "test_dd_02"}})

        assert result.get("rag_result") is not None
        assert result.get("market_data") is not None
        assert result.get("news_data") is not None
        assert result.get("tokenomics_data") is not None


class TestCompareWorkflow:
    @pytest.mark.asyncio
    async def test_compare_handles_multiple_projects(self):
        """Compare workflow should handle 2+ projects."""
        router_result = {"workflow_type": "compare", "target_entities": ["ARB", "OP"], "reasoning": "compare"}
        with (
            patch("src.agents.router.RouterAgent._call_llm", new_callable=AsyncMock, return_value=router_result),
            patch("src.agents.planner.PlannerAgent._call_llm", new_callable=AsyncMock, return_value=MOCK_PLANNER_RESULT),
            patch("src.agents.analyst.AnalystAgent._generate", new_callable=AsyncMock, return_value=MOCK_ANALYST_REPORT),
            patch("src.agents.critic.CriticAgent._review", new_callable=AsyncMock, return_value=MOCK_CRITIC_APPROVE),
            patch("src.agents.rag_agent._rag_agent._retrieve", new_callable=AsyncMock, return_value=MOCK_RAG_RESULT),
            patch("src.agents.market_agent.get_price", new_callable=AsyncMock, return_value={"current_price": 1.25}),
            patch("src.agents.market_agent.calculate_technical_indicators", new_callable=AsyncMock, return_value={}),
            patch("src.agents.market_agent.get_market_overview", new_callable=AsyncMock, return_value={}),
            patch("src.agents.news_agent.search_news", new_callable=AsyncMock, return_value={"news": []}),
            patch("src.agents.news_agent.analyze_sentiment", new_callable=AsyncMock, return_value={"overall_sentiment": "neutral"}),
            patch("src.agents.tokenomics_agent.get_unlock_schedule", new_callable=AsyncMock, return_value={}),
            patch("src.agents.tokenomics_agent.get_token_distribution", new_callable=AsyncMock, return_value={}),
        ):
            app = compile_workflow()
            state = _get_initial_state()
            state["user_query"] = "对比 ARB 和 OP"
            result = await app.ainvoke(state, config={"configurable": {"thread_id": "test_cmp_01"}})

        assert result.get("workflow_type") == "compare"
        assert len(result.get("target_entities", [])) >= 2


class TestWorkflowResilience:
    @pytest.mark.asyncio
    async def test_mcp_failure_fallback(self):
        """Workflow should continue even if MCP tool calls fail."""
        with (
            patch("src.agents.router.RouterAgent._call_llm", new_callable=AsyncMock, return_value=MOCK_ROUTER_RESULT),
            patch("src.agents.planner.PlannerAgent._call_llm", new_callable=AsyncMock, return_value=MOCK_PLANNER_RESULT),
            patch("src.agents.analyst.AnalystAgent._generate", new_callable=AsyncMock, return_value=MOCK_ANALYST_REPORT),
            patch("src.agents.critic.CriticAgent._review", new_callable=AsyncMock, return_value=MOCK_CRITIC_APPROVE),
            patch("src.agents.rag_agent._rag_agent._retrieve", new_callable=AsyncMock, return_value=MOCK_RAG_RESULT),
            patch("src.agents.market_agent.get_price", new_callable=AsyncMock, side_effect=Exception("API error")),
            patch("src.agents.market_agent.calculate_technical_indicators", new_callable=AsyncMock, side_effect=Exception("API error")),
            patch("src.agents.market_agent.get_market_overview", new_callable=AsyncMock, side_effect=Exception("API error")),
            patch("src.agents.news_agent.search_news", new_callable=AsyncMock, side_effect=Exception("API error")),
            patch("src.agents.news_agent.analyze_sentiment", new_callable=AsyncMock, side_effect=Exception("API error")),
            patch("src.agents.tokenomics_agent.get_unlock_schedule", new_callable=AsyncMock, side_effect=Exception("API error")),
            patch("src.agents.tokenomics_agent.get_token_distribution", new_callable=AsyncMock, side_effect=Exception("API error")),
        ):
            app = compile_workflow()
            result = await app.ainvoke(_get_initial_state(), config={"configurable": {"thread_id": "test_fail_01"}})

        # Workflow should still complete, analysis report should exist
        assert result is not None
        assert result.get("analysis_report") is not None

    @pytest.mark.asyncio
    async def test_revision_count_max_two(self):
        """Critic should trigger at most 2 revisions (max_revision_count=2)."""
        bad_report = dict(MOCK_ANALYST_REPORT)
        bad_report["investment_recommendation"] = dict(bad_report["investment_recommendation"])
        bad_report["investment_recommendation"]["confidence"] = 0.95

        critic_reject = {"approved": False, "feedback": "Confidence too high", "issues": [{"category": "compliance", "severity": "critical", "description": "Confidence > 0.8"}]}

        with (
            patch("src.agents.router.RouterAgent._call_llm", new_callable=AsyncMock, return_value=MOCK_ROUTER_RESULT),
            patch("src.agents.planner.PlannerAgent._call_llm", new_callable=AsyncMock, return_value=["rag_agent"]),
            patch("src.agents.analyst.AnalystAgent._generate", new_callable=AsyncMock, return_value=bad_report),
            patch("src.agents.critic.CriticAgent._review", new_callable=AsyncMock, return_value=critic_reject),
            patch("src.agents.rag_agent._rag_agent._retrieve", new_callable=AsyncMock, return_value=MOCK_RAG_RESULT),
        ):
            app = compile_workflow()
            result = await app.ainvoke(_get_initial_state(), config={"configurable": {"thread_id": "test_maxrev_02"}})

        assert result.get("critic_approved") is True
        assert result.get("revision_count") >= 2
