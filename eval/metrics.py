"""Metric computation for RAG quality, agent accuracy, and end-to-end evaluation."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class MetricResult(BaseModel):
    """A single metric evaluation result."""

    name: str = Field(description="Metric name")
    category: str = Field(description="Category: rag, agent, or output")
    score: float = Field(description="Score value, -1.0 if not computable")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")


class EvalReport(BaseModel):
    """Evaluation report for a single test case."""

    test_case_id: str = Field(description="Test case identifier")
    query: str = Field(description="Query that was evaluated")
    metrics: list[MetricResult] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, description="Weighted overall score")
    timestamp: datetime = Field(default_factory=datetime.now)


# === RAG Metrics (RAGAS soft dependency) ===

def compute_faithfulness(answer: str, contexts: list[str]) -> MetricResult:
    """Compute faithfulness score using RAGAS if available.

    Measures how much of the answer is grounded in the retrieved contexts.
    Returns -1.0 if RAGAS is not available.

    Args:
        answer: The generated answer text.
        contexts: List of retrieved context strings.

    Returns:
        MetricResult with faithfulness score in [0, 1], or -1.0 if unavailable.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness

        dataset = Dataset.from_dict({
            "question": [""],
            "answer": [answer],
            "contexts": [contexts],
        })
        result = evaluate(dataset, metrics=[faithfulness])
        score = float(result["faithfulness"])
        return MetricResult(name="faithfulness", category="rag", score=score)
    except (ImportError, Exception) as e:
        logger.debug("ragas_faithfulness_unavailable", error=str(e))
        return MetricResult(
            name="faithfulness", category="rag", score=-1.0,
            details={"reason": "RAGAS not available"}
        )


def compute_answer_relevancy(query: str, answer: str) -> MetricResult:
    """Compute answer relevancy score using RAGAS if available.

    Measures how relevant the generated answer is to the original query.
    Returns -1.0 if RAGAS is not available.

    Args:
        query: The original user query.
        answer: The generated answer text.

    Returns:
        MetricResult with answer_relevancy score in [0, 1], or -1.0 if unavailable.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy

        dataset = Dataset.from_dict({
            "question": [query],
            "answer": [answer],
            "contexts": [[""]],
        })
        result = evaluate(dataset, metrics=[answer_relevancy])
        score = float(result["answer_relevancy"])
        return MetricResult(name="answer_relevancy", category="rag", score=score)
    except (ImportError, Exception) as e:
        logger.debug("ragas_answer_relevancy_unavailable", error=str(e))
        return MetricResult(
            name="answer_relevancy", category="rag", score=-1.0,
            details={"reason": "RAGAS not available"}
        )


def compute_context_precision(
    query: str, contexts: list[str], ground_truth: str
) -> MetricResult:
    """Compute context precision score using RAGAS if available.

    Measures what fraction of retrieved contexts are actually relevant to answering
    the query, given the ground truth answer.
    Returns -1.0 if RAGAS is not available.

    Args:
        query: The original user query.
        contexts: List of retrieved context strings.
        ground_truth: The reference/ground truth answer.

    Returns:
        MetricResult with context_precision score in [0, 1], or -1.0 if unavailable.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import context_precision

        dataset = Dataset.from_dict({
            "question": [query],
            "answer": [ground_truth],
            "contexts": [contexts],
            "ground_truth": [ground_truth],
        })
        result = evaluate(dataset, metrics=[context_precision])
        score = float(result["context_precision"])
        return MetricResult(name="context_precision", category="rag", score=score)
    except (ImportError, Exception) as e:
        logger.debug("ragas_context_precision_unavailable", error=str(e))
        return MetricResult(
            name="context_precision", category="rag", score=-1.0,
            details={"reason": "RAGAS not available"}
        )


# === Agent Metrics ===

def compute_tool_call_accuracy(
    expected_tools: list[str], actual_tools: list[str]
) -> MetricResult:
    """Compute tool call accuracy using Jaccard similarity.

    Score = |intersection| / |union|. A score of 1.0 means the agent called
    exactly the right set of tools; lower scores indicate missing or extra calls.

    Args:
        expected_tools: Tool names the agent was expected to call.
        actual_tools: Tool names the agent actually called.

    Returns:
        MetricResult with Jaccard similarity score in [0, 1].
    """
    if not expected_tools and not actual_tools:
        return MetricResult(
            name="tool_call_accuracy", category="agent", score=1.0,
            details={"expected": [], "actual": [], "intersection": []}
        )

    expected_set = set(expected_tools)
    actual_set = set(actual_tools)
    intersection = expected_set & actual_set
    union = expected_set | actual_set

    score = len(intersection) / len(union) if union else 0.0

    return MetricResult(
        name="tool_call_accuracy", category="agent", score=score,
        details={
            "expected": sorted(expected_tools),
            "actual": sorted(actual_tools),
            "intersection": sorted(intersection),
            "missing": sorted(expected_set - actual_set),
            "extra": sorted(actual_set - expected_set),
        }
    )


def compute_plan_completion(
    expected_fields: list[str], actual_output: dict[str, Any]
) -> MetricResult:
    """Compute plan completion as field coverage ratio.

    Score = number of expected fields present in output / total expected fields.
    A field is considered present if its value is not None.

    Args:
        expected_fields: Output field names that should be populated.
        actual_output: The actual output dictionary from the agent.

    Returns:
        MetricResult with completion ratio in [0, 1].
    """
    if not expected_fields:
        return MetricResult(
            name="plan_completion", category="agent", score=1.0,
            details={"expected": [], "present": [], "missing": []}
        )

    present = [f for f in expected_fields if actual_output.get(f) is not None]
    missing = [f for f in expected_fields if actual_output.get(f) is None]
    score = len(present) / len(expected_fields)

    return MetricResult(
        name="plan_completion", category="agent", score=score,
        details={"expected": expected_fields, "present": present, "missing": missing}
    )


# === Output Quality Metrics ===

def compute_schema_validity(output: dict[str, Any], schema_class: type) -> MetricResult:
    """Validate output against a Pydantic schema.

    Score is binary: 1.0 if the output is valid, 0.0 if validation fails.

    Args:
        output: The output dictionary to validate.
        schema_class: The Pydantic model class to validate against.

    Returns:
        MetricResult with score 1.0 (valid) or 0.0 (invalid).
    """
    try:
        schema_class(**output)
        return MetricResult(
            name="schema_validity", category="output", score=1.0,
            details={"schema": schema_class.__name__, "valid": True}
        )
    except Exception as e:
        return MetricResult(
            name="schema_validity", category="output", score=0.0,
            details={"schema": schema_class.__name__, "valid": False, "error": str(e)}
        )


def compute_disclaimer_present(text: str) -> MetricResult:
    """Check if the output contains a disclaimer.

    Score is binary: 1.0 if a disclaimer pattern is found, 0.0 otherwise.
    Covers both Chinese and English disclaimer variants.

    Args:
        text: The output text to check.

    Returns:
        MetricResult with score 1.0 (disclaimer found) or 0.0 (absent).
    """
    disclaimer_patterns = [
        r"not\s+financial\s+advice",
        r"不构成投资建议",
        r"仅供参考",
        r"do\s+your\s+own\s+research",
        r"DYOR",
        r"风险自担",
        r"disclaimer",
        r"免责声明",
    ]

    text_lower = text.lower()
    found = [p for p in disclaimer_patterns if re.search(p, text_lower, re.IGNORECASE)]

    score = 1.0 if found else 0.0
    return MetricResult(
        name="disclaimer_present", category="output", score=score,
        details={"patterns_matched": found}
    )


def compute_no_absolute_claims(text: str) -> MetricResult:
    """Check that text does not contain absolute investment claims.

    Score is binary: 1.0 if no violations found, 0.0 if absolute claims detected.
    A failing score indicates the output may be making irresponsible financial claims.

    Args:
        text: The output text to check.

    Returns:
        MetricResult with score 1.0 (clean) or 0.0 (violations found).
    """
    absolute_patterns = [
        r"一定会涨",
        r"保证.*收益",
        r"guaranteed.*return",
        r"一定.*赚",
        r"稳赚不赔",
        r"肯定会.*涨",
        r"必然.*上涨",
        r"will\s+definitely\s+(?:rise|increase|go\s+up)",
        r"guaranteed\s+profit",
        r"100%.*回报",
    ]

    violations = [p for p in absolute_patterns if re.search(p, text, re.IGNORECASE)]

    score = 1.0 if not violations else 0.0
    return MetricResult(
        name="no_absolute_claims", category="output", score=score,
        details={"violations": violations}
    )


def compute_citation_count(text: str) -> MetricResult:
    """Count citation references in the text.

    Matches common citation formats such as [1], [source: ...], 来源：, etc.
    The raw count is stored in details; score equals the raw count.
    Normalization to [0, 1] happens in compute_weighted_score.

    Args:
        text: The output text to scan for citations.

    Returns:
        MetricResult with score equal to raw citation count (>= 0).
    """
    citation_patterns = [
        r"\[\d+\]",
        r"\[source:.*?\]",
        r"来源[：:]",
        r"数据来源[：:]",
        r"参考[：:]",
        r"Sources?:",
        r"Reference",
    ]

    total_count = 0
    for pattern in citation_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        total_count += len(matches)

    return MetricResult(
        name="citation_count", category="output", score=float(total_count),
        details={"count": total_count}
    )


# === Weighted Score Computation ===

_CATEGORY_WEIGHTS = {"rag": 0.3, "agent": 0.3, "output": 0.4}


def compute_weighted_score(metrics: list[MetricResult]) -> float:
    """Compute weighted overall score from individual metrics.

    Weights: RAG 0.3, Agent 0.3, Output 0.4.
    Unavailable metrics (score == -1.0) are excluded, and their weight
    is redistributed proportionally among available categories.

    The citation_count metric is normalised: any count >= 1 maps to 1.0,
    a count of 0 maps to 0.0, before being averaged with other output metrics.

    Args:
        metrics: List of MetricResult objects from all metric functions.

    Returns:
        Weighted overall score in [0, 1], rounded to 4 decimal places.
    """
    category_scores: dict[str, list[float]] = {"rag": [], "agent": [], "output": []}

    for m in metrics:
        if m.score >= 0.0 and m.category in category_scores:
            # citation_count is a raw count, not 0-1; normalise it
            if m.name == "citation_count":
                normalized = 1.0 if m.score > 0 else 0.0
                category_scores[m.category].append(normalized)
            else:
                category_scores[m.category].append(m.score)

    # Compute average per category
    category_avgs: dict[str, float] = {}
    available_weight = 0.0

    for cat, scores in category_scores.items():
        if scores:
            category_avgs[cat] = sum(scores) / len(scores)
            available_weight += _CATEGORY_WEIGHTS[cat]

    if available_weight == 0:
        return 0.0

    # Redistribute weights proportionally among available categories
    weighted_sum = 0.0
    for cat, avg in category_avgs.items():
        adjusted_weight = _CATEGORY_WEIGHTS[cat] / available_weight
        weighted_sum += avg * adjusted_weight

    return round(weighted_sum, 4)
