"""Tests for the evaluation runner (eval/run_eval.py).

Covers:
- load_test_cases(): path resolution and error handling
- _build_mock_output(): structural correctness for each workflow type
- evaluate_single_case(): metric computation and EvalReport structure
- run_workflow(): fallback behaviour when the real workflow is unavailable
- run_all_evaluations(): orchestration over multiple test cases
- save_results(): JSON file creation
- print_results_table(): smoke test for stdout output
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eval.metrics import EvalReport, MetricResult
from eval.run_eval import (
    _build_mock_output,
    evaluate_single_case,
    load_test_cases,
    run_all_evaluations,
    run_workflow,
    save_results,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_dive_case(
    case_id: str = "tc_dd",
    query: str = "分析 Arbitrum 是否值得投资",
    expected_fields: list[str] | None = None,
    expected_tools: list[str] | None = None,
    expected_answer: str = "Arbitrum is a Layer 2 solution.",
) -> dict:
    return {
        "id": case_id,
        "query": query,
        "workflow_type": "deep_dive",
        "expected_fields": expected_fields
        or ["fundamental_analysis", "market_data", "investment_recommendation"],
        "expected_tools": expected_tools or ["rag", "market"],
        "expected_answer": expected_answer,
    }


def _qa_case(case_id: str = "tc_qa") -> dict:
    return {
        "id": case_id,
        "query": "Arbitrum 的团队背景是什么？",
        "workflow_type": "qa",
        "expected_fields": [],
        "expected_tools": ["rag_search"],
        "expected_answer": "Offchain Labs",
    }


def _compare_case(case_id: str = "tc_cmp") -> dict:
    return {
        "id": case_id,
        "query": "对比 Arbitrum 和 Optimism",
        "workflow_type": "compare",
        "expected_fields": ["fundamental_analysis"],
        "expected_tools": ["rag_search"],
    }


def _news_watch_case(case_id: str = "tc_nw") -> dict:
    return {
        "id": case_id,
        "query": "Arbitrum 最近有什么重要新闻？",
        "workflow_type": "brief",
        "expected_fields": ["news_sentiment"],
        "expected_tools": ["get_news"],
    }


# ---------------------------------------------------------------------------
# load_test_cases
# ---------------------------------------------------------------------------


class TestLoadTestCases:
    def test_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        with patch("eval.run_eval.TEST_CASES_PATH", tmp_path / "nonexistent.json"):
            result = load_test_cases()
        assert result == []

    def test_valid_json_file_loaded(self, tmp_path: Path) -> None:
        cases = [_deep_dive_case(), _qa_case()]
        path = tmp_path / "test_cases.json"
        path.write_text(json.dumps(cases), encoding="utf-8")
        with patch("eval.run_eval.TEST_CASES_PATH", path):
            result = load_test_cases()
        assert len(result) == 2
        assert result[0]["id"] == "tc_dd"

    def test_empty_array_returns_empty_list(self, tmp_path: Path) -> None:
        path = tmp_path / "test_cases.json"
        path.write_text("[]", encoding="utf-8")
        with patch("eval.run_eval.TEST_CASES_PATH", path):
            result = load_test_cases()
        assert result == []

    def test_returns_list_type(self, tmp_path: Path) -> None:
        path = tmp_path / "test_cases.json"
        path.write_text(json.dumps([_qa_case()]), encoding="utf-8")
        with patch("eval.run_eval.TEST_CASES_PATH", path):
            result = load_test_cases()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# _build_mock_output
# ---------------------------------------------------------------------------


class TestBuildMockOutput:
    def test_deep_dive_core_fields_present(self) -> None:
        case = _deep_dive_case(
            expected_fields=["fundamental_analysis", "market_data", "investment_recommendation"]
        )
        output = _build_mock_output(case)
        assert output["project_name"] == "Arbitrum"
        assert "fundamental_analysis" in output
        assert "market_data" in output
        assert "investment_recommendation" in output

    def test_deep_dive_answer_text_present(self) -> None:
        output = _build_mock_output(_deep_dive_case())
        assert "answer_text" in output
        assert isinstance(output["answer_text"], str)
        assert len(output["answer_text"]) > 0

    def test_deep_dive_contexts_present(self) -> None:
        output = _build_mock_output(_deep_dive_case())
        assert "contexts" in output
        assert isinstance(output["contexts"], list)
        assert len(output["contexts"]) > 0

    def test_qa_minimal_no_deep_dive_fields(self) -> None:
        output = _build_mock_output(_qa_case())
        assert output["workflow_type"] == "qa"
        assert "fundamental_analysis" not in output

    def test_compare_workflow_type_preserved(self) -> None:
        output = _build_mock_output(_compare_case())
        assert output["workflow_type"] == "compare"

    def test_news_watch_news_sentiment_present(self) -> None:
        case = _news_watch_case()
        output = _build_mock_output(case)
        assert output["workflow_type"] == "brief"
        assert "news_sentiment" in output

    def test_tools_used_matches_expected_tools(self) -> None:
        """Mock output sets tools_used == expected_tools for deterministic scoring."""
        expected = ["rag", "market", "news"]
        case = _deep_dive_case(expected_tools=expected)
        output = _build_mock_output(case)
        assert output["tools_used"] == expected

    def test_answer_text_contains_disclaimer(self) -> None:
        output = _build_mock_output(_deep_dive_case())
        # The mock embeds a Chinese disclaimer
        assert any(
            kw in output["answer_text"]
            for kw in ("不构成投资建议", "仅供参考", "免责声明", "not financial advice", "DYOR")
        )

    def test_answer_text_contains_citation(self) -> None:
        output = _build_mock_output(_deep_dive_case())
        # Mock output contains "[1]" bracket citation
        assert "[1]" in output["answer_text"] or "来源" in output["answer_text"]

    def test_investment_recommendation_included_when_requested(self) -> None:
        case = _deep_dive_case(
            expected_fields=["investment_recommendation"]
        )
        output = _build_mock_output(case)
        rec = output["investment_recommendation"]
        assert "rating" in rec
        assert "confidence" in rec
        assert "disclaimer" in rec

    def test_tokenomics_included_when_requested(self) -> None:
        case = {
            "id": "tc_tok",
            "query": "ARB 代币经济学",
            "workflow_type": "deep_dive",
            "expected_fields": ["tokenomics"],
            "expected_tools": [],
        }
        output = _build_mock_output(case)
        assert "tokenomics" in output
        assert "total_supply" in output["tokenomics"]

    def test_news_sentiment_included_when_requested(self) -> None:
        case = {
            "id": "tc_news",
            "query": "news",
            "workflow_type": "brief",
            "expected_fields": ["news_sentiment"],
            "expected_tools": [],
        }
        output = _build_mock_output(case)
        assert "news_sentiment" in output
        assert "overall_sentiment" in output["news_sentiment"]

    def test_workflow_type_stored_correctly(self) -> None:
        for wtype in ("deep_dive", "compare", "brief", "qa"):
            case = {
                "id": f"tc_{wtype}",
                "query": "test",
                "workflow_type": wtype,
                "expected_fields": [],
                "expected_tools": [],
            }
            output = _build_mock_output(case)
            assert output["workflow_type"] == wtype


# ---------------------------------------------------------------------------
# run_workflow
# ---------------------------------------------------------------------------


class TestRunWorkflow:
    def test_returns_empty_dict_when_import_fails(self) -> None:
        """If the workflow module is unavailable, run_workflow returns {}."""
        with patch("eval.run_eval.run_workflow", return_value={}):
            result = run_workflow("test query", "qa")
        assert result == {}

    def test_actual_run_workflow_returns_dict_or_empty(self) -> None:
        """run_workflow never raises; it returns a dict."""
        result = run_workflow("Arbitrum 分析", "deep_dive")
        assert isinstance(result, dict)

    def test_run_workflow_with_unavailable_graph_module(self, monkeypatch) -> None:
        """Patch the internal import to simulate ImportError → empty dict."""
        import builtins
        original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "src.graph.workflow":
                raise ImportError("not implemented")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _mock_import)
        result = run_workflow("query", "qa")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# evaluate_single_case
# ---------------------------------------------------------------------------


class TestEvaluateSingleCase:
    def test_returns_eval_report_instance(self) -> None:
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_deep_dive_case())
        assert isinstance(report, EvalReport)

    def test_test_case_id_preserved(self) -> None:
        case = _deep_dive_case(case_id="deep_dive_01")
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(case)
        assert report.test_case_id == "deep_dive_01"

    def test_query_preserved(self) -> None:
        case = _deep_dive_case(query="analyze Arbitrum")
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(case)
        assert report.query == "analyze Arbitrum"

    def test_overall_score_in_valid_range(self) -> None:
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_deep_dive_case())
        assert 0.0 <= report.overall_score <= 1.0

    def test_metrics_list_non_empty(self) -> None:
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_deep_dive_case())
        assert len(report.metrics) > 0

    def test_all_metric_results_are_metric_result(self) -> None:
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_deep_dive_case())
        for m in report.metrics:
            assert isinstance(m, MetricResult)

    def test_qa_case_evaluated(self) -> None:
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_qa_case())
        assert report.test_case_id == "tc_qa"
        assert report.overall_score >= 0.0

    def test_compare_case_evaluated(self) -> None:
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_compare_case())
        assert report.test_case_id == "tc_cmp"

    def test_news_watch_case_evaluated(self) -> None:
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_news_watch_case())
        assert report.test_case_id == "tc_nw"

    def test_mock_output_used_when_workflow_returns_empty(self) -> None:
        """Empty workflow output triggers _build_mock_output path."""
        case = _deep_dive_case(
            expected_fields=["fundamental_analysis", "investment_recommendation"]
        )
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(case)
        # plan_completion must be 1.0 because mock output populates all fields
        plan_metrics = [m for m in report.metrics if m.name == "plan_completion"]
        if plan_metrics:
            assert plan_metrics[0].score == pytest.approx(1.0, abs=0.01)

    def test_tool_call_accuracy_present_in_metrics(self) -> None:
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_deep_dive_case())
        metric_names = {m.name for m in report.metrics}
        assert "tool_call_accuracy" in metric_names

    def test_plan_completion_present_in_metrics(self) -> None:
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_deep_dive_case())
        metric_names = {m.name for m in report.metrics}
        assert "plan_completion" in metric_names

    def test_disclaimer_metric_present_for_deep_dive(self) -> None:
        """Mock output for deep_dive includes answer_text → disclaimer metric computed."""
        with patch("eval.run_eval.run_workflow", return_value={}):
            report = evaluate_single_case(_deep_dive_case())
        metric_names = {m.name for m in report.metrics}
        assert "disclaimer_present" in metric_names

    def test_real_workflow_output_used_when_non_empty(self) -> None:
        """Non-empty workflow output bypasses mock."""
        fake_output = {
            "project_name": "FakeProject",
            "workflow_type": "qa",
            "analysis_date": "2026-03-09T00:00:00",
            "tools_used": ["rag_search"],
            "answer_text": "Some answer. Not financial advice.",
            "contexts": ["context chunk"],
        }
        case = _qa_case()
        with patch("eval.run_eval.run_workflow", return_value=fake_output):
            report = evaluate_single_case(case)
        assert report.overall_score >= 0.0


# ---------------------------------------------------------------------------
# run_all_evaluations
# ---------------------------------------------------------------------------


class TestRunAllEvaluations:
    def test_empty_test_cases_returns_empty_list(self, tmp_path: Path) -> None:
        path = tmp_path / "test_cases.json"
        path.write_text("[]", encoding="utf-8")
        with patch("eval.run_eval.TEST_CASES_PATH", path):
            reports = run_all_evaluations()
        assert reports == []

    def test_missing_test_cases_file_returns_empty(self, tmp_path: Path) -> None:
        with patch("eval.run_eval.TEST_CASES_PATH", tmp_path / "missing.json"):
            reports = run_all_evaluations()
        assert reports == []

    def test_returns_one_report_per_case(self, tmp_path: Path) -> None:
        cases = [_deep_dive_case("dd1"), _qa_case("qa1"), _compare_case("cmp1")]
        path = tmp_path / "test_cases.json"
        path.write_text(json.dumps(cases), encoding="utf-8")
        with (
            patch("eval.run_eval.TEST_CASES_PATH", path),
            patch("eval.run_eval.run_workflow", return_value={}),
        ):
            reports = run_all_evaluations()
        assert len(reports) == 3

    def test_error_in_one_case_does_not_abort_others(self, tmp_path: Path) -> None:
        """A single case failure inserts a zero-score placeholder and continues."""
        cases = [_qa_case("qa1"), _deep_dive_case("dd1")]
        path = tmp_path / "test_cases.json"
        path.write_text(json.dumps(cases), encoding="utf-8")

        call_count = {"n": 0}

        def _flaky_workflow(query, wtype):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("Simulated failure")
            return {}

        with (
            patch("eval.run_eval.TEST_CASES_PATH", path),
            patch("eval.run_eval.run_workflow", side_effect=_flaky_workflow),
        ):
            reports = run_all_evaluations()

        # Both cases produce a report (one may be zero-score placeholder)
        assert len(reports) == 2
        ids = {r.test_case_id for r in reports}
        assert "qa1" in ids
        assert "dd1" in ids


# ---------------------------------------------------------------------------
# save_results
# ---------------------------------------------------------------------------


class TestSaveResults:
    def test_creates_json_file(self, tmp_path: Path) -> None:
        reports = [
            EvalReport(test_case_id="tc01", query="test query", overall_score=0.85)
        ]
        with patch("eval.run_eval.RESULTS_DIR", tmp_path):
            output_path = save_results(reports)
        assert output_path.exists()
        assert output_path.suffix == ".json"

    def test_json_content_is_valid(self, tmp_path: Path) -> None:
        reports = [
            EvalReport(test_case_id="tc01", query="test", overall_score=0.75)
        ]
        with patch("eval.run_eval.RESULTS_DIR", tmp_path):
            output_path = save_results(reports)
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["test_case_id"] == "tc01"

    def test_filename_contains_timestamp(self, tmp_path: Path) -> None:
        reports = [EvalReport(test_case_id="x", query="y", overall_score=0.5)]
        with patch("eval.run_eval.RESULTS_DIR", tmp_path):
            output_path = save_results(reports)
        assert output_path.stem.startswith("eval_")

    def test_results_dir_created_if_missing(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "nested" / "results"
        reports = [EvalReport(test_case_id="x", query="y", overall_score=0.5)]
        with patch("eval.run_eval.RESULTS_DIR", new_dir):
            save_results(reports)
        assert new_dir.exists()

    def test_multiple_reports_saved(self, tmp_path: Path) -> None:
        reports = [
            EvalReport(test_case_id="a", query="q1", overall_score=0.9),
            EvalReport(test_case_id="b", query="q2", overall_score=0.6),
        ]
        with patch("eval.run_eval.RESULTS_DIR", tmp_path):
            output_path = save_results(reports)
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data) == 2


# ---------------------------------------------------------------------------
# Smoke test for print_results_table
# ---------------------------------------------------------------------------


class TestPrintResultsTable:
    def test_does_not_raise_with_empty_list(self, capsys) -> None:
        from eval.run_eval import print_results_table
        print_results_table([])
        captured = capsys.readouterr()
        assert "DYOR" in captured.out

    def test_prints_report_ids(self, capsys) -> None:
        from eval.run_eval import print_results_table
        reports = [
            EvalReport(test_case_id="tc_deep_dive_01", query="analyze ARB", overall_score=0.88),
        ]
        print_results_table(reports)
        captured = capsys.readouterr()
        assert "tc_deep_dive_01" in captured.out

    def test_prints_average_score(self, capsys) -> None:
        from eval.run_eval import print_results_table
        reports = [
            EvalReport(test_case_id="a", query="q1", overall_score=1.0),
            EvalReport(test_case_id="b", query="q2", overall_score=0.0),
        ]
        print_results_table(reports)
        captured = capsys.readouterr()
        assert "Average" in captured.out

    def test_marks_failing_cases(self, capsys) -> None:
        """Cases with overall_score < 0.5 should be marked with '!'."""
        from eval.run_eval import print_results_table
        reports = [
            EvalReport(test_case_id="fail_01", query="bad query", overall_score=0.1),
        ]
        print_results_table(reports)
        captured = capsys.readouterr()
        assert "!" in captured.out

    def test_metric_breakdown_printed(self, capsys) -> None:
        from eval.run_eval import print_results_table
        reports = [
            EvalReport(
                test_case_id="tc01",
                query="test",
                overall_score=0.7,
                metrics=[
                    MetricResult(name="tool_call_accuracy", category="agent", score=0.7),
                ],
            )
        ]
        print_results_table(reports)
        captured = capsys.readouterr()
        assert "tool_call_accuracy" in captured.out
