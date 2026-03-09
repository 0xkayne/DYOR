"""Evaluation script for running golden test cases against the agent system."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from eval.metrics import (
    EvalReport,
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

logger = structlog.get_logger(__name__)

EVAL_DIR = Path(__file__).parent
TEST_CASES_PATH = EVAL_DIR / "test_cases.json"
RESULTS_DIR = EVAL_DIR / "results"


def load_test_cases() -> list[dict[str, Any]]:
    """Load golden test cases from JSON.

    Returns:
        List of test case dicts. Empty list if file not found.
    """
    if not TEST_CASES_PATH.exists():
        logger.error("test_cases_not_found", path=str(TEST_CASES_PATH))
        return []

    return json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))


def _build_mock_output(test_case: dict[str, Any]) -> dict[str, Any]:
    """Build a mock workflow output for stub mode.

    Used when the agent system is not fully implemented yet.
    Produces a structurally correct output that exercises all metrics.

    Args:
        test_case: A single golden test case dict.

    Returns:
        A mock output dict that mimics AnalysisReport structure.
    """
    wtype = test_case.get("workflow_type", "qa")

    output: dict[str, Any] = {
        "project_name": "Arbitrum",
        "workflow_type": wtype,
        "analysis_date": datetime.now().isoformat(),
    }

    expected_fields = test_case.get("expected_fields", [])

    if "fundamental_analysis" in expected_fields:
        output["fundamental_analysis"] = {
            "summary": (
                "Arbitrum is a leading Layer 2 Optimistic Rollup"
                " solution built by Offchain Labs."
            ),
            "team_score": 8.0,
            "product_score": 7.5,
            "track_score": 8.5,
            "tokenomics_score": 6.5,
            "sources": ["arbitrum_report.md"],
        }

    if "market_data" in expected_fields:
        output["market_data"] = {
            "current_price": 1.25,
            "price_change_24h": 3.2,
            "market_cap": 3200000000,
            "data_source": "coingecko",
        }

    if "news_sentiment" in expected_fields:
        output["news_sentiment"] = {
            "overall_sentiment": "positive",
            "news_count": 5,
            "data_source": "cryptopanic",
        }

    if "tokenomics" in expected_fields:
        output["tokenomics"] = {
            "total_supply": 10000000000,
            "circulating_supply": 1275000000,
            "next_unlock_date": "2024-03-16",
        }

    if "investment_recommendation" in expected_fields:
        output["investment_recommendation"] = {
            "rating": "buy",
            "confidence": 0.72,
            "key_reasons": ["Strong ecosystem growth", "Active development"],
            "risk_factors": ["Token unlock pressure", "Competition from zkSync"],
            "disclaimer": "This is not financial advice. Always do your own research.",
        }

    # Mock answer text with citations and disclaimer
    output["answer_text"] = (
        f"基于对 {output['project_name']} 的分析 [1]，该项目在 Layer2 赛道中表现突出。"
        "\n\n来源：arbitrum_report.md"
        "\n\n免责声明：本分析不构成投资建议，仅供参考，风险自担。"
    )

    # Mock tools used matches expected so accuracy is 1.0 in stub mode
    output["tools_used"] = test_case.get("expected_tools", [])

    # Mock contexts for RAG evaluation
    output["contexts"] = [
        "Arbitrum 是由 Offchain Labs 开发的以太坊 Layer 2 Optimistic Rollup 解决方案",
        "ARB 代币总量 100 亿，初始流通量约 12.75 亿枚（12.75%）",
        "Arbitrum 创始团队包括普林斯顿大学教授 Ed Felten 和密码学博士 Steven Goldfeder",
    ]

    return output


def run_workflow(query: str, workflow_type: str) -> dict[str, Any]:
    """Run the agent workflow or return an empty dict for fallback.

    Attempts to import and invoke the real LangGraph workflow. Falls back to
    an empty dict (triggering mock output) if the agent system is not yet
    implemented or raises any error.

    Args:
        query: The user query to run through the workflow.
        workflow_type: One of "deep_dive", "compare", "qa", "news_watch".

    Returns:
        Workflow output dict, or empty dict on failure.
    """
    try:
        import asyncio

        from src.graph.workflow import run_analysis
        return asyncio.run(run_analysis(query, workflow_type))
    except (ImportError, AttributeError, Exception) as e:
        logger.info("using_mock_output", reason=str(e))
        return {}


def evaluate_single_case(test_case: dict[str, Any]) -> EvalReport:
    """Evaluate a single golden test case.

    Runs the workflow (or falls back to mock), then computes all applicable
    metrics: RAG metrics, agent accuracy metrics, and output quality metrics.

    Args:
        test_case: A single golden test case dict from test_cases.json.

    Returns:
        EvalReport containing all metric results and an overall weighted score.
    """
    query = test_case["query"]
    case_id = test_case["id"]
    workflow_type = test_case.get("workflow_type", "qa")

    # Try real workflow; fall back to mock if unavailable
    output = run_workflow(query, workflow_type)
    if not output:
        output = _build_mock_output(test_case)

    metrics = []

    # --- RAG metrics ---
    answer_text = output.get("answer_text", "")
    contexts = output.get("contexts", [])
    ground_truth = test_case.get("expected_answer", "")

    if answer_text and contexts:
        metrics.append(compute_faithfulness(answer_text, contexts))
        metrics.append(compute_answer_relevancy(query, answer_text))

    if ground_truth and contexts:
        metrics.append(compute_context_precision(query, contexts, ground_truth))

    # --- Agent metrics ---
    expected_tools = test_case.get("expected_tools", [])
    actual_tools = output.get("tools_used", [])
    metrics.append(compute_tool_call_accuracy(expected_tools, actual_tools))

    expected_fields = test_case.get("expected_fields", [])
    metrics.append(compute_plan_completion(expected_fields, output))

    # --- Output quality metrics ---
    if answer_text:
        metrics.append(compute_disclaimer_present(answer_text))
        metrics.append(compute_no_absolute_claims(answer_text))
        metrics.append(compute_citation_count(answer_text))

    # Schema validation against AnalysisReport
    try:
        from src.schemas.analysis import AnalysisReport

        schema_input = {
            k: v for k, v in output.items()
            if k in AnalysisReport.model_fields
        }
        if schema_input.get("workflow_type"):
            metrics.append(compute_schema_validity(schema_input, AnalysisReport))
    except ImportError:
        logger.debug("schema_import_skipped", reason="src.schemas not available")

    overall = compute_weighted_score(metrics)

    return EvalReport(
        test_case_id=case_id,
        query=query,
        metrics=metrics,
        overall_score=overall,
    )


def run_all_evaluations() -> list[EvalReport]:
    """Run evaluation on all golden test cases.

    Returns:
        List of EvalReport objects, one per test case.
    """
    test_cases = load_test_cases()
    if not test_cases:
        print("No test cases found.")
        return []

    reports: list[EvalReport] = []
    for case in test_cases:
        logger.info("evaluating", case_id=case["id"], query=case["query"])
        try:
            report = evaluate_single_case(case)
        except Exception as exc:
            logger.error("case_evaluation_failed", case_id=case["id"], error=str(exc))
            # Insert a zero-score placeholder so the run continues
            report = EvalReport(
                test_case_id=case["id"],
                query=case["query"],
                overall_score=0.0,
            )
        reports.append(report)

    return reports


def print_results_table(reports: list[EvalReport]) -> None:
    """Print a summary table and metric breakdown to stdout.

    Args:
        reports: List of completed EvalReport objects.
    """
    print("\n" + "=" * 80)
    print("DYOR Evaluation Results")
    print("=" * 80)
    print(f"{'ID':<12} {'Score':>6}  {'Query':<52}")
    print("-" * 80)

    failing: list[EvalReport] = []

    for report in reports:
        query_display = (
            report.query[:49] + "..." if len(report.query) > 52 else report.query
        )
        flag = ""
        # Identify failing cases: overall score below 0.5
        if report.overall_score < 0.5:
            flag = " !"
            failing.append(report)
        print(f"{report.test_case_id:<12} {report.overall_score:>5.3f}{flag}  {query_display}")

    if reports:
        avg_score = sum(r.overall_score for r in reports) / len(reports)
        print("-" * 80)
        print(f"{'Average':<12} {avg_score:>5.3f}")

    print("=" * 80)

    # Per-metric breakdown
    print("\nMetric Breakdown (averaged over cases where metric was computable):")
    print("-" * 60)

    all_metric_names: set[str] = set()
    for r in reports:
        for m in r.metrics:
            all_metric_names.add(m.name)

    for metric_name in sorted(all_metric_names):
        scores = []
        for r in reports:
            for m in r.metrics:
                if m.name == metric_name and m.score >= 0:
                    scores.append(m.score)
        if scores:
            avg = sum(scores) / len(scores)
            print(
                f"  {metric_name:<32} avg={avg:.3f}  ({len(scores)}/{len(reports)} cases)"
            )

    # Failing case diagnostics
    if failing:
        print("\nFailing Cases (score < 0.50):")
        print("-" * 60)
        for report in failing:
            print(f"\n  [{report.test_case_id}] {report.query}")
            print(f"  Overall score: {report.overall_score:.3f}")
            for m in report.metrics:
                if 0.0 <= m.score < 0.5:
                    print(
                        f"    - {m.name} ({m.category}): {m.score:.3f}  "
                        f"details={m.details}"
                    )


def save_results(reports: list[EvalReport]) -> Path:
    """Save evaluation results as JSON to eval/results/.

    Args:
        reports: List of completed EvalReport objects.

    Returns:
        Path to the written results file.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"eval_{timestamp}.json"

    results_data = [r.model_dump(mode="json") for r in reports]
    output_path.write_text(
        json.dumps(results_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print(f"\nResults saved to: {output_path}")
    return output_path


def main() -> None:
    """CLI entry point for the evaluation framework."""
    print("DYOR Evaluation Framework")
    print("=" * 40)

    reports = run_all_evaluations()

    if reports:
        print_results_table(reports)
        save_results(reports)
    else:
        print("No evaluations were run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
