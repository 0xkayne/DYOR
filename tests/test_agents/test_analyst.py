"""Tests for the analyst agent."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.analyst import AnalystAgent, _analyst, analyst_node, _format_data_section


VALID_REPORT = {
    "project_name": "Arbitrum",
    "analysis_date": "2026-03-09T00:00:00",
    "workflow_type": "deep_dive",
    "fundamental_analysis": {
        "summary": "Good project.",
        "team_score": 8.0,
        "product_score": 7.5,
        "track_score": 8.0,
        "tokenomics_score": 6.5,
        "sources": ["arb.md"],
    },
    "investment_recommendation": {
        "rating": "buy",
        "confidence": 0.65,
        "key_reasons": ["Strong ecosystem"],
        "risk_factors": ["Competition"],
        "disclaimer": "Not financial advice.",
    },
}


class TestAnalystGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_report(self):
        """LLM returning valid JSON should produce a report dict."""
        with patch.object(
            _analyst, "_generate", new_callable=AsyncMock, return_value=VALID_REPORT
        ):
            result = await _analyst.invoke(
                "分析 Arbitrum", None, None, None, None, entities=["Arbitrum"]
            )
        assert result["project_name"] == "Arbitrum"

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self):
        """Timeout should return fallback report."""
        with patch.object(
            _analyst, "_generate", new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            result = await _analyst.invoke(
                "test", None, None, None, None, entities=["Arbitrum"]
            )
        assert result["project_name"] == "Arbitrum"
        assert result["investment_recommendation"]["rating"] == "hold"
        assert result["investment_recommendation"]["confidence"] == 0.1

    @pytest.mark.asyncio
    async def test_exception_returns_fallback(self):
        """Exception should return fallback report."""
        with patch.object(
            _analyst, "_generate", new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            result = await _analyst.invoke(
                "test", None, None, None, None, entities=["Test"]
            )
        assert result["project_name"] == "Test"
        assert "error" in result["fundamental_analysis"]["summary"].lower()


class TestExtractJson:
    def test_extract_from_markdown_json_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = _analyst._extract_json(text)
        assert json.loads(result) == {"key": "value"}

    def test_extract_from_plain_markdown_block(self):
        text = '```\n{"key": "value"}\n```'
        result = _analyst._extract_json(text)
        assert json.loads(result) == {"key": "value"}

    def test_extract_from_raw_json(self):
        text = 'Here is the report: {"key": "value"} done.'
        result = _analyst._extract_json(text)
        assert json.loads(result) == {"key": "value"}

    def test_extract_pure_json(self):
        text = '{"key": "value"}'
        result = _analyst._extract_json(text)
        assert json.loads(result) == {"key": "value"}


class TestFormatDataSection:
    def test_format_with_data(self):
        result = _format_data_section("Test", {"key": "value"})
        assert "Test" in result
        assert "key" in result

    def test_format_with_none(self):
        result = _format_data_section("Test", None)
        assert "unavailable" in result.lower()


class TestAnalystNode:
    @pytest.mark.asyncio
    async def test_analyst_node_returns_report(self):
        with patch.object(
            _analyst, "invoke", new_callable=AsyncMock, return_value=VALID_REPORT
        ):
            state = {
                "user_query": "test",
                "workflow_type": "deep_dive",
                "target_entities": ["Arbitrum"],
                "rag_result": None,
                "market_data": None,
                "news_data": None,
                "tokenomics_data": None,
                "critic_feedback": None,
            }
            result = await analyst_node(state)
        assert "analysis_report" in result
        assert result["analysis_report"]["project_name"] == "Arbitrum"

    @pytest.mark.asyncio
    async def test_analyst_node_injects_disclaimer(self):
        """analyst_node should inject disclaimer when it is empty."""
        report = dict(VALID_REPORT)
        report["investment_recommendation"] = dict(report["investment_recommendation"])
        report["investment_recommendation"]["disclaimer"] = ""
        with patch.object(
            _analyst, "invoke", new_callable=AsyncMock, return_value=report
        ):
            state = {
                "user_query": "test",
                "workflow_type": "deep_dive",
                "target_entities": ["Arbitrum"],
                "rag_result": None,
                "market_data": None,
                "news_data": None,
                "tokenomics_data": None,
                "critic_feedback": None,
            }
            result = await analyst_node(state)
        # inject_disclaimer should have added the RISK_DISCLAIMER
        disc = result["analysis_report"]["investment_recommendation"]["disclaimer"]
        assert len(disc) > 0
