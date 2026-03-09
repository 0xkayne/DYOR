"""Tests for the critic agent."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.critic import (
    CriticAgent,
    _check_forbidden_patterns,
    _check_required_fields,
    _critic,
    critic_node,
)


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


class TestForbiddenPatterns:
    def test_clean_text_no_issues(self):
        issues = _check_forbidden_patterns("This is a normal analysis report.")
        assert len(issues) == 0

    def test_english_forbidden_pattern(self):
        issues = _check_forbidden_patterns("This investment has guaranteed returns.")
        assert len(issues) > 0
        assert issues[0]["severity"] == "critical"

    def test_chinese_forbidden_pattern(self):
        issues = _check_forbidden_patterns("这个项目保证收益，稳赚不赔")
        assert len(issues) > 0

    def test_risk_free_detected(self):
        issues = _check_forbidden_patterns("This is a risk-free investment.")
        assert len(issues) > 0

    def test_chinese_absolute_detected(self):
        issues = _check_forbidden_patterns("一定会涨")
        assert len(issues) > 0


class TestRequiredFields:
    def test_valid_report_no_issues(self):
        issues = _check_required_fields(VALID_REPORT)
        # Should have no critical issues
        critical = [i for i in issues if i["severity"] == "critical"]
        assert len(critical) == 0

    def test_missing_project_name(self):
        report = dict(VALID_REPORT)
        report["project_name"] = ""
        issues = _check_required_fields(report)
        descriptions = [i["description"] for i in issues]
        assert any("project_name" in d for d in descriptions)

    def test_invalid_workflow_type(self):
        report = dict(VALID_REPORT)
        report["workflow_type"] = "invalid"
        issues = _check_required_fields(report)
        descriptions = [i["description"] for i in issues]
        assert any("workflow_type" in d for d in descriptions)

    def test_missing_disclaimer(self):
        report = dict(VALID_REPORT)
        report["investment_recommendation"] = dict(report["investment_recommendation"])
        report["investment_recommendation"]["disclaimer"] = ""
        issues = _check_required_fields(report)
        descriptions = [i["description"] for i in issues]
        assert any("disclaimer" in d for d in descriptions)

    def test_missing_recommendation(self):
        report = dict(VALID_REPORT)
        report["investment_recommendation"] = None
        issues = _check_required_fields(report)
        descriptions = [i["description"] for i in issues]
        assert any("investment_recommendation" in d for d in descriptions)


class TestCriticInvoke:
    @pytest.mark.asyncio
    async def test_approved_report(self):
        """Clean report should be approved."""
        result = {"approved": True, "feedback": "Good.", "issues": []}
        with patch.object(
            _critic, "_review", new_callable=AsyncMock, return_value=result
        ):
            res = await _critic.invoke(VALID_REPORT)
        assert res["approved"] is True

    @pytest.mark.asyncio
    async def test_timeout_auto_approves(self):
        """Timeout should auto-approve."""
        with patch.object(
            _critic, "_review", new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            res = await _critic.invoke(VALID_REPORT)
        assert res["approved"] is True

    @pytest.mark.asyncio
    async def test_exception_auto_approves(self):
        """Exception should auto-approve."""
        with patch.object(
            _critic, "_review", new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            res = await _critic.invoke(VALID_REPORT)
        assert res["approved"] is True


class TestCriticNode:
    @pytest.mark.asyncio
    async def test_approved_sets_state(self):
        result = {"approved": True, "feedback": "Good.", "issues": []}
        with patch.object(
            _critic, "invoke", new_callable=AsyncMock, return_value=result
        ):
            with patch("src.agents.critic.validate_output", return_value=(True, [])):
                state = {"analysis_report": VALID_REPORT, "revision_count": 0}
                res = await critic_node(state)
        assert res["critic_approved"] is True

    @pytest.mark.asyncio
    async def test_rejected_increments_revision(self):
        result = {"approved": False, "feedback": "Bad.", "issues": []}
        with patch.object(
            _critic, "invoke", new_callable=AsyncMock, return_value=result
        ):
            with patch("src.agents.critic.validate_output", return_value=(True, [])):
                state = {"analysis_report": VALID_REPORT, "revision_count": 0}
                res = await critic_node(state)
        assert res["critic_approved"] is False
        assert res["revision_count"] == 1

    @pytest.mark.asyncio
    async def test_max_revision_auto_approves(self):
        """At max revision count, should auto-approve."""
        state = {"analysis_report": VALID_REPORT, "revision_count": 2}
        res = await critic_node(state)
        assert res["critic_approved"] is True

    @pytest.mark.asyncio
    async def test_no_report_rejects(self):
        state = {"analysis_report": None, "revision_count": 0}
        res = await critic_node(state)
        assert res["critic_approved"] is False
