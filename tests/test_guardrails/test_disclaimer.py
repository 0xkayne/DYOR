"""Tests for the disclaimer injection."""

from __future__ import annotations

from src.guardrails.disclaimer import inject_disclaimer, RISK_DISCLAIMER


class TestRiskDisclaimer:
    def test_disclaimer_constant_non_empty(self):
        assert len(RISK_DISCLAIMER) > 0
        assert "DYOR" in RISK_DISCLAIMER

    def test_disclaimer_constant_contains_risk_warning(self):
        assert "风险" in RISK_DISCLAIMER


class TestInjectDisclaimer:
    def test_missing_disclaimer_injected(self):
        report = {"investment_recommendation": {"disclaimer": ""}}
        result = inject_disclaimer(report)
        assert result["investment_recommendation"]["disclaimer"] == RISK_DISCLAIMER

    def test_existing_disclaimer_kept(self):
        report = {"investment_recommendation": {"disclaimer": "My custom disclaimer"}}
        result = inject_disclaimer(report)
        assert result["investment_recommendation"]["disclaimer"] == "My custom disclaimer"

    def test_no_recommendation_creates_one(self):
        report = {"project_name": "Test"}
        result = inject_disclaimer(report)
        assert result["investment_recommendation"]["disclaimer"] == RISK_DISCLAIMER

    def test_non_dict_report_returns_as_is(self):
        result = inject_disclaimer("not a dict")
        assert result == "not a dict"

    def test_none_disclaimer_injected(self):
        report = {"investment_recommendation": {"rating": "buy"}}
        result = inject_disclaimer(report)
        assert result["investment_recommendation"]["disclaimer"] == RISK_DISCLAIMER
