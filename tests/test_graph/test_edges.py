"""Tests for graph edge routing functions."""

from __future__ import annotations

from src.graph.edges import route_after_critic, route_after_planner


class TestRouteAfterPlanner:
    def test_full_plan(self):
        state = {"execution_plan": ["rag_agent", "market_agent", "news_agent", "tokenomics_agent"]}
        result = route_after_planner(state)
        assert result == ["rag_agent", "market_agent", "news_agent", "tokenomics_agent"]

    def test_partial_plan(self):
        state = {"execution_plan": ["rag_agent", "market_agent"]}
        result = route_after_planner(state)
        assert result == ["rag_agent", "market_agent"]

    def test_empty_plan_defaults_to_rag(self):
        state = {"execution_plan": []}
        result = route_after_planner(state)
        assert result == ["rag_agent"]

    def test_short_names_mapped(self):
        state = {"execution_plan": ["rag", "market"]}
        result = route_after_planner(state)
        assert result == ["rag_agent", "market_agent"]

    def test_deduplication(self):
        state = {"execution_plan": ["rag_agent", "rag_agent"]}
        result = route_after_planner(state)
        assert result == ["rag_agent"]

    def test_invalid_agents_filtered(self):
        state = {"execution_plan": ["invalid_agent", "rag_agent"]}
        result = route_after_planner(state)
        assert result == ["rag_agent"]


class TestRouteAfterCritic:
    def test_approved_ends(self):
        state = {"critic_approved": True}
        result = route_after_critic(state)
        assert result == "__end__"

    def test_rejected_revises(self):
        state = {"critic_approved": False}
        result = route_after_critic(state)
        assert result == "analyst"

    def test_default_not_approved(self):
        state = {}
        result = route_after_critic(state)
        assert result == "analyst"
