"""Tests for the output validator guardrail."""

from __future__ import annotations

from src.guardrails.output_validator import validate_output, FORBIDDEN_PATTERNS


def _make_valid_report() -> dict:
    return {
        "project_name": "Arbitrum",
        "analysis_date": "2026-03-09T00:00:00",
        "fundamental_analysis": {
            "summary": "Good project.",
            "team_score": 8.0, "product_score": 7.5, "track_score": 8.0, "tokenomics_score": 6.5,
            "sources": ["arb.md"],
        },
        "investment_recommendation": {
            "rating": "buy", "confidence": 0.65,
            "key_reasons": ["Strong ecosystem"], "risk_factors": ["Competition"],
            "disclaimer": "Not financial advice.",
        },
    }


class TestValidReport:
    def test_valid_report_passes(self):
        is_valid, issues = validate_output(_make_valid_report())
        assert is_valid is True
        assert len(issues) == 0


class TestMissingFields:
    def test_missing_project_name(self):
        report = _make_valid_report()
        del report["project_name"]
        is_valid, issues = validate_output(report)
        assert is_valid is False
        assert any("project_name" in i for i in issues)

    def test_none_project_name(self):
        report = _make_valid_report()
        report["project_name"] = None
        is_valid, issues = validate_output(report)
        assert is_valid is False

    def test_missing_analysis_date(self):
        report = _make_valid_report()
        del report["analysis_date"]
        is_valid, issues = validate_output(report)
        assert is_valid is False

    def test_missing_fundamental_analysis(self):
        report = _make_valid_report()
        report["fundamental_analysis"] = None
        is_valid, issues = validate_output(report)
        assert is_valid is False

    def test_missing_investment_recommendation(self):
        report = _make_valid_report()
        report["investment_recommendation"] = None
        is_valid, issues = validate_output(report)
        assert is_valid is False


class TestScoreRanges:
    def test_score_below_1(self):
        report = _make_valid_report()
        report["fundamental_analysis"]["team_score"] = 0
        is_valid, issues = validate_output(report)
        assert is_valid is False
        assert any("team_score" in i for i in issues)

    def test_score_above_10(self):
        report = _make_valid_report()
        report["fundamental_analysis"]["product_score"] = 11
        is_valid, issues = validate_output(report)
        assert is_valid is False


class TestConfidence:
    def test_confidence_above_08(self):
        report = _make_valid_report()
        report["investment_recommendation"]["confidence"] = 0.9
        is_valid, issues = validate_output(report)
        assert is_valid is False
        assert any("0.8" in i for i in issues)

    def test_confidence_at_08(self):
        report = _make_valid_report()
        report["investment_recommendation"]["confidence"] = 0.8
        is_valid, issues = validate_output(report)
        assert is_valid is True


class TestDisclaimer:
    def test_empty_disclaimer(self):
        report = _make_valid_report()
        report["investment_recommendation"]["disclaimer"] = ""
        is_valid, issues = validate_output(report)
        assert is_valid is False
        assert any("disclaimer" in i for i in issues)


class TestSources:
    def test_empty_sources(self):
        report = _make_valid_report()
        report["fundamental_analysis"]["sources"] = []
        is_valid, issues = validate_output(report)
        assert is_valid is False
        assert any("sources" in i for i in issues)


class TestForbiddenPatterns:
    def test_chinese_forbidden(self):
        report = _make_valid_report()
        report["fundamental_analysis"]["summary"] = "这个项目一定会成功"
        is_valid, issues = validate_output(report)
        assert is_valid is False
        assert any("一定" in i for i in issues)

    def test_english_forbidden(self):
        report = _make_valid_report()
        report["fundamental_analysis"]["summary"] = "This is guaranteed to succeed"
        is_valid, issues = validate_output(report)
        assert is_valid is False


class TestNonDictInput:
    def test_non_dict(self):
        is_valid, issues = validate_output("not a dict")
        assert is_valid is False
        assert any("dictionary" in i.lower() for i in issues)

    def test_none_input(self):
        is_valid, issues = validate_output(None)
        assert is_valid is False
