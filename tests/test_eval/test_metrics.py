"""Tests for evaluation metrics.

Covers all 11 metric functions exported from eval.metrics plus the
compute_weighted_score aggregator.  RAGAS-backed metrics (faithfulness,
answer_relevancy, context_precision) are not exercised here because they
require optional heavy dependencies; their graceful degradation to -1.0
is covered instead.
"""

from __future__ import annotations

import pytest

from eval.metrics import (
    MetricResult,
    compute_answer_relevancy,
    compute_citation_count,
    compute_context_precision,
    compute_disclaimer_present,
    compute_faithfulness,
    compute_no_absolute_claims,
    compute_plan_completion,
    compute_schema_validity,
    compute_tool_call_accuracy,
    compute_weighted_score,
)
from src.schemas.analysis import AnalysisReport


# ---------------------------------------------------------------------------
# MetricResult model
# ---------------------------------------------------------------------------


class TestMetricResult:
    def test_construction_with_required_fields(self) -> None:
        m = MetricResult(name="test_metric", category="agent", score=0.75)
        assert m.name == "test_metric"
        assert m.category == "agent"
        assert m.score == 0.75
        assert m.details == {}

    def test_details_default_is_empty_dict(self) -> None:
        m = MetricResult(name="x", category="rag", score=1.0)
        assert isinstance(m.details, dict)
        assert len(m.details) == 0

    def test_negative_one_is_valid_score(self) -> None:
        """score=-1.0 is the sentinel for 'not computable'."""
        m = MetricResult(name="faithfulness", category="rag", score=-1.0)
        assert m.score == -1.0


# ---------------------------------------------------------------------------
# compute_tool_call_accuracy
# ---------------------------------------------------------------------------


class TestToolCallAccuracy:
    def test_exact_match(self) -> None:
        result = compute_tool_call_accuracy(["rag", "market"], ["rag", "market"])
        assert result.score == 1.0

    def test_order_independent(self) -> None:
        """Jaccard similarity is set-based; order must not matter."""
        result = compute_tool_call_accuracy(["market", "rag"], ["rag", "market"])
        assert result.score == 1.0

    def test_partial_match_expected_superset(self) -> None:
        """Actual tools are a strict subset of expected."""
        result = compute_tool_call_accuracy(["rag", "market"], ["rag"])
        assert 0.0 < result.score < 1.0

    def test_partial_match_actual_superset(self) -> None:
        """Actual tools are a strict superset of expected."""
        result = compute_tool_call_accuracy(["rag"], ["rag", "market"])
        assert 0.0 < result.score < 1.0

    def test_no_match(self) -> None:
        result = compute_tool_call_accuracy(["rag"], ["market"])
        assert result.score == 0.0

    def test_both_empty(self) -> None:
        result = compute_tool_call_accuracy([], [])
        assert result.score == 1.0

    def test_expected_empty_actual_non_empty(self) -> None:
        """Expected is empty but actual has tools → partial credit via Jaccard."""
        result = compute_tool_call_accuracy([], ["rag"])
        # union = {"rag"}, intersection = {} → 0/1 = 0.0
        # When expected is empty and actual is non-empty, union is non-empty so score = 0.
        assert result.score == 0.0

    def test_details_contain_missing_and_extra(self) -> None:
        result = compute_tool_call_accuracy(["rag", "market"], ["rag", "news"])
        assert "missing" in result.details
        assert "extra" in result.details
        assert "market" in result.details["missing"]
        assert "news" in result.details["extra"]

    def test_jaccard_value_three_expected_two_actual_one_overlap(self) -> None:
        """Exact Jaccard: intersection=1, union=4 → 0.25."""
        result = compute_tool_call_accuracy(["a", "b", "c"], ["a", "d"])
        # intersection: {a}, union: {a,b,c,d} → 1/4 = 0.25
        assert result.score == pytest.approx(0.25, abs=1e-6)

    def test_extra_tools_penalised(self) -> None:
        """Calling extra tools that were not expected lowers the score below 1."""
        result = compute_tool_call_accuracy(["rag"], ["rag", "market"])
        assert 0.0 < result.score < 1.0


# ---------------------------------------------------------------------------
# compute_plan_completion
# ---------------------------------------------------------------------------


class TestPlanCompletion:
    def test_all_fields_present(self) -> None:
        result = compute_plan_completion(["a", "b"], {"a": 1, "b": 2})
        assert result.score == 1.0

    def test_no_fields_present(self) -> None:
        result = compute_plan_completion(["a", "b"], {"c": 1})
        assert result.score == 0.0

    def test_partial_fields_present(self) -> None:
        result = compute_plan_completion(["a", "b", "c"], {"a": 1, "b": None, "c": 3})
        # 'b' maps to None so it is absent; present = [a, c] → 2/3
        assert result.score == pytest.approx(2 / 3, abs=0.01)

    def test_empty_expected_always_one(self) -> None:
        result = compute_plan_completion([], {"a": 1})
        assert result.score == 1.0

    def test_none_value_counts_as_absent(self) -> None:
        result = compute_plan_completion(["field"], {"field": None})
        assert result.score == 0.0

    def test_falsy_non_none_value_counts_as_present(self) -> None:
        """0, False, and [] are falsy but not None; they count as present."""
        result = compute_plan_completion(["a", "b", "c"], {"a": 0, "b": False, "c": []})
        assert result.score == 1.0

    def test_details_contain_missing_list(self) -> None:
        result = compute_plan_completion(["x", "y"], {"x": 1})
        assert "y" in result.details["missing"]

    def test_single_field_exact_match(self) -> None:
        result = compute_plan_completion(["fundamental_analysis"], {"fundamental_analysis": {"score": 8}})
        assert result.score == 1.0


# ---------------------------------------------------------------------------
# compute_schema_validity
# ---------------------------------------------------------------------------


class TestSchemaValidity:
    def test_valid_minimal_schema(self) -> None:
        data = {"project_name": "Test", "workflow_type": "deep_dive"}
        result = compute_schema_validity(data, AnalysisReport)
        assert result.score == 1.0

    def test_valid_full_schema(self) -> None:
        data = {
            "project_name": "Arbitrum",
            "workflow_type": "deep_dive",
            "analysis_date": "2026-03-09T00:00:00",
        }
        result = compute_schema_validity(data, AnalysisReport)
        assert result.score == 1.0

    def test_invalid_workflow_type(self) -> None:
        data = {"project_name": "Test", "workflow_type": "invalid_type"}
        result = compute_schema_validity(data, AnalysisReport)
        assert result.score == 0.0

    def test_missing_project_name(self) -> None:
        data = {"workflow_type": "qa"}
        result = compute_schema_validity(data, AnalysisReport)
        assert result.score == 0.0

    def test_details_contains_schema_name(self) -> None:
        data = {"project_name": "Test", "workflow_type": "qa"}
        result = compute_schema_validity(data, AnalysisReport)
        assert result.details["schema"] == "AnalysisReport"

    def test_details_contains_error_on_failure(self) -> None:
        data = {"workflow_type": "bad_type"}
        result = compute_schema_validity(data, AnalysisReport)
        assert result.score == 0.0
        assert "error" in result.details

    def test_all_four_valid_workflow_types(self) -> None:
        for wtype in ("deep_dive", "compare", "brief", "qa"):
            data = {"project_name": "X", "workflow_type": wtype}
            result = compute_schema_validity(data, AnalysisReport)
            assert result.score == 1.0, f"Unexpected failure for workflow_type={wtype!r}"


# ---------------------------------------------------------------------------
# compute_disclaimer_present
# ---------------------------------------------------------------------------


class TestDisclaimerPresent:
    def test_english_not_financial_advice(self) -> None:
        result = compute_disclaimer_present("This is not financial advice.")
        assert result.score == 1.0

    def test_chinese_not_investment_advice(self) -> None:
        result = compute_disclaimer_present("本分析不构成投资建议，仅供参考")
        assert result.score == 1.0

    def test_chinese_for_reference_only(self) -> None:
        result = compute_disclaimer_present("以上内容仅供参考，请注意风险。")
        assert result.score == 1.0

    def test_dyor_keyword(self) -> None:
        result = compute_disclaimer_present("Always DYOR before investing.")
        assert result.score == 1.0

    def test_do_your_own_research(self) -> None:
        result = compute_disclaimer_present("Please do your own research.")
        assert result.score == 1.0

    def test_disclaimer_keyword_english(self) -> None:
        result = compute_disclaimer_present("See the full disclaimer at the bottom.")
        assert result.score == 1.0

    def test_chinese_free_disclaimer(self) -> None:
        result = compute_disclaimer_present("免责声明：本报告仅供研究使用。")
        assert result.score == 1.0

    def test_no_disclaimer_plain_text(self) -> None:
        result = compute_disclaimer_present("Arbitrum is a great Layer 2 project.")
        assert result.score == 0.0

    def test_no_disclaimer_empty_string(self) -> None:
        result = compute_disclaimer_present("")
        assert result.score == 0.0

    def test_patterns_matched_detail_populated(self) -> None:
        result = compute_disclaimer_present("DYOR is important.")
        assert len(result.details["patterns_matched"]) > 0

    def test_case_insensitive_matching(self) -> None:
        result = compute_disclaimer_present("dyor before you invest")
        assert result.score == 1.0


# ---------------------------------------------------------------------------
# compute_no_absolute_claims
# ---------------------------------------------------------------------------


class TestNoAbsoluteClaims:
    def test_clean_text_returns_one(self) -> None:
        result = compute_no_absolute_claims("This project shows promising growth potential.")
        assert result.score == 1.0

    def test_chinese_absolute_will_rise(self) -> None:
        result = compute_no_absolute_claims("这个项目一定会涨")
        assert result.score == 0.0

    def test_chinese_guaranteed_profit(self) -> None:
        result = compute_no_absolute_claims("保证收益100%")
        assert result.score == 0.0

    def test_english_guaranteed_returns(self) -> None:
        result = compute_no_absolute_claims("This token has guaranteed returns.")
        assert result.score == 0.0

    def test_english_guaranteed_profit_phrase(self) -> None:
        result = compute_no_absolute_claims("guaranteed profit ahead")
        assert result.score == 0.0

    def test_chinese_stable_profit_no_loss(self) -> None:
        result = compute_no_absolute_claims("稳赚不赔，快来购买！")
        assert result.score == 0.0

    def test_english_will_definitely_rise(self) -> None:
        result = compute_no_absolute_claims("The price will definitely rise next week.")
        assert result.score == 0.0

    def test_empty_string_clean(self) -> None:
        result = compute_no_absolute_claims("")
        assert result.score == 1.0

    def test_violations_detail_populated_on_failure(self) -> None:
        result = compute_no_absolute_claims("一定会涨，放心买！")
        assert len(result.details["violations"]) > 0

    def test_violations_detail_empty_on_pass(self) -> None:
        result = compute_no_absolute_claims("Some balanced analysis here.")
        assert result.details["violations"] == []


# ---------------------------------------------------------------------------
# compute_citation_count
# ---------------------------------------------------------------------------


class TestCitationCount:
    def test_bracket_citations(self) -> None:
        result = compute_citation_count("According to [1] and [2], the project is strong.")
        assert result.score >= 2

    def test_single_bracket_citation(self) -> None:
        result = compute_citation_count("See [3] for details.")
        assert result.score >= 1

    def test_chinese_source_prefix(self) -> None:
        result = compute_citation_count("来源：CoinGecko 数据")
        assert result.score >= 1

    def test_chinese_data_source_prefix(self) -> None:
        result = compute_citation_count("数据来源：CryptoPanic API")
        assert result.score >= 1

    def test_multiple_chinese_sources(self) -> None:
        result = compute_citation_count("来源：CoinGecko 数据来源：CryptoPanic")
        assert result.score >= 2

    def test_english_sources_keyword(self) -> None:
        result = compute_citation_count("Sources: CoinGecko, CryptoPanic")
        assert result.score >= 1

    def test_reference_keyword(self) -> None:
        result = compute_citation_count("Reference: arbitrum_report.md")
        assert result.score >= 1

    def test_no_citations(self) -> None:
        result = compute_citation_count("This is plain text without any citations.")
        assert result.score == 0

    def test_empty_string_no_citations(self) -> None:
        result = compute_citation_count("")
        assert result.score == 0

    def test_score_equals_raw_count(self) -> None:
        """score and details['count'] must be consistent."""
        result = compute_citation_count("[1] [2] [3]")
        assert result.score == result.details["count"]

    def test_source_bracket_pattern(self) -> None:
        result = compute_citation_count("[source: CoinGecko API]")
        assert result.score >= 1


# ---------------------------------------------------------------------------
# RAGAS-backed metrics graceful degradation
# ---------------------------------------------------------------------------


class TestRagasMetricsGracefulDegradation:
    """When RAGAS is not installed the metrics return score=-1.0 without raising."""

    def test_faithfulness_returns_metric_result(self) -> None:
        result = compute_faithfulness("some answer", ["some context"])
        assert isinstance(result, MetricResult)
        assert result.name == "faithfulness"
        assert result.category == "rag"
        # Either RAGAS is available (0-1) or unavailable (-1)
        assert result.score == -1.0 or 0.0 <= result.score <= 1.0

    def test_answer_relevancy_returns_metric_result(self) -> None:
        result = compute_answer_relevancy("what is ARB?", "ARB is a governance token.")
        assert isinstance(result, MetricResult)
        assert result.name == "answer_relevancy"
        assert result.score == -1.0 or 0.0 <= result.score <= 1.0

    def test_context_precision_returns_metric_result(self) -> None:
        result = compute_context_precision(
            "what is ARB?", ["ARB is a token"], "ARB is a governance token."
        )
        assert isinstance(result, MetricResult)
        assert result.name == "context_precision"
        assert result.score == -1.0 or 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# compute_weighted_score
# ---------------------------------------------------------------------------


class TestComputeWeightedScore:
    def test_all_perfect_scores_returns_one(self) -> None:
        metrics = [
            MetricResult(name="tool_call_accuracy", category="agent", score=1.0),
            MetricResult(name="plan_completion", category="agent", score=1.0),
            MetricResult(name="schema_validity", category="output", score=1.0),
            MetricResult(name="disclaimer_present", category="output", score=1.0),
            MetricResult(name="faithfulness", category="rag", score=1.0),
        ]
        score = compute_weighted_score(metrics)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_all_zero_scores_returns_zero(self) -> None:
        metrics = [
            MetricResult(name="tool_call_accuracy", category="agent", score=0.0),
            MetricResult(name="schema_validity", category="output", score=0.0),
            MetricResult(name="faithfulness", category="rag", score=0.0),
        ]
        score = compute_weighted_score(metrics)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_unavailable_ragas_metric_excluded(self) -> None:
        """score=-1.0 metrics are excluded; remaining weight is redistributed."""
        metrics = [
            MetricResult(name="faithfulness", category="rag", score=-1.0),
            MetricResult(name="tool_call_accuracy", category="agent", score=1.0),
            MetricResult(name="schema_validity", category="output", score=1.0),
        ]
        score = compute_weighted_score(metrics)
        assert 0.0 < score <= 1.0

    def test_empty_metrics_returns_zero(self) -> None:
        score = compute_weighted_score([])
        assert score == 0.0

    def test_citation_count_normalised_to_one_when_positive(self) -> None:
        """citation_count > 0 normalises to 1.0 inside output category."""
        metrics = [
            MetricResult(name="citation_count", category="output", score=5.0),
        ]
        score = compute_weighted_score(metrics)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_citation_count_zero_normalised_to_zero(self) -> None:
        """citation_count = 0 normalises to 0.0."""
        metrics = [
            MetricResult(name="citation_count", category="output", score=0.0),
        ]
        score = compute_weighted_score(metrics)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_only_agent_metrics_available(self) -> None:
        """When only agent-category metrics exist the full weight goes to them."""
        metrics = [
            MetricResult(name="tool_call_accuracy", category="agent", score=0.8),
            MetricResult(name="plan_completion", category="agent", score=0.6),
        ]
        score = compute_weighted_score(metrics)
        # average of [0.8, 0.6] = 0.7, redistributed weight = 1.0
        assert score == pytest.approx(0.7, abs=0.01)

    def test_only_output_metrics_available(self) -> None:
        metrics = [
            MetricResult(name="disclaimer_present", category="output", score=1.0),
            MetricResult(name="no_absolute_claims", category="output", score=1.0),
        ]
        score = compute_weighted_score(metrics)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_return_value_rounded_to_four_decimal_places(self) -> None:
        metrics = [
            MetricResult(name="tool_call_accuracy", category="agent", score=1 / 3),
        ]
        score = compute_weighted_score(metrics)
        # 4 decimal places → round(1/3, 4) = 0.3333
        assert score == round(score, 4)

    def test_all_categories_with_perfect_output_zero_rag_agent(self) -> None:
        """Mixed scores: only output=1.0, rag=0.0, agent=0.0 → weighted sum < 1."""
        metrics = [
            MetricResult(name="faithfulness", category="rag", score=0.0),
            MetricResult(name="tool_call_accuracy", category="agent", score=0.0),
            MetricResult(name="schema_validity", category="output", score=1.0),
        ]
        score = compute_weighted_score(metrics)
        # (0.0*0.3 + 0.0*0.3 + 1.0*0.4) / 1.0 = 0.4
        assert score == pytest.approx(0.4, abs=0.01)

    def test_unknown_category_ignored(self) -> None:
        """Metrics with an unknown category do not crash and are silently excluded."""
        metrics = [
            MetricResult(name="custom_metric", category="custom", score=1.0),
            MetricResult(name="schema_validity", category="output", score=1.0),
        ]
        score = compute_weighted_score(metrics)
        # Only the output metric contributes; score should be 1.0
        assert score == pytest.approx(1.0, abs=0.01)
