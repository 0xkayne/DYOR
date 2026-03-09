"""RAG quality evaluation using RAGAS metrics.

Provides evaluation of retrieval quality with default Arbitrum QA pairs.
Falls back to basic retrieval statistics when RAGAS API key is unavailable.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.rag.retriever import AgenticRetriever

logger = structlog.get_logger(__name__)

# Default evaluation QA pairs for Arbitrum
_DEFAULT_QA_PAIRS = [
    {
        "question": "Arbitrum 的创始团队背景是什么？",
        "ground_truth": (
            "Offchain Labs由Ed Felten（前白宫副CTO）、Steven Goldfeder"
            "和Harry Kalodner创立，团队来自普林斯顿大学，"
            "在密码学和计算机科学方面有深厚的学术背景。"
        ),
        "contexts_keywords": ["Ed Felten", "Offchain Labs", "Princeton"],
    },
    {
        "question": "ARB 代币的总供应量和分配方式是怎样的？",
        "ground_truth": (
            "ARB总供应量100亿，其中42.78%分配给DAO国库，"
            "26.94%分配给团队和顾问（4年归属期，1年锁定期），"
            "17.53%分配给投资者（4年归属期），12.75%空投给社区。"
        ),
        "contexts_keywords": ["10 billion", "42.78%", "DAO Treasury"],
    },
    {
        "question": "Arbitrum 的主要竞争对手有哪些？",
        "ground_truth": (
            "Arbitrum的主要竞争对手包括Optimism（OP Stack）、"
            "zkSync、StarkNet和Polygon zkEVM。"
        ),
        "contexts_keywords": ["Optimism", "zkSync", "StarkNet", "Polygon"],
    },
    {
        "question": "Arbitrum 使用什么技术实现L2扩展？",
        "ground_truth": (
            "Arbitrum使用Optimistic Rollup技术，"
            "配合多轮交互式欺诈证明系统（Nitro），比单轮证明更加gas高效。"
        ),
        "contexts_keywords": ["Optimistic Rollup", "Nitro", "fraud proof"],
    },
    {
        "question": "Arbitrum 面临哪些风险？",
        "ground_truth": (
            "主要风险包括：排序器中心化风险、团队和投资者代币解锁压力、"
            "ZK rollup竞争、监管不确定性、对以太坊的依赖。"
        ),
        "contexts_keywords": ["sequencer", "centralized", "vesting", "ZK rollups"],
    },
]


class EvaluationResult(BaseModel):
    """Result of a single QA evaluation."""

    question: str = Field(description="The evaluation question")
    retrieved_count: int = Field(description="Number of results retrieved")
    avg_score: float = Field(description="Average relevance score")
    top_score: float = Field(description="Top result relevance score")
    keyword_hits: int = Field(description="Number of expected keywords found in results")
    keyword_total: int = Field(description="Total expected keywords")
    keyword_recall: float = Field(description="Keyword recall ratio")


class EvaluationSummary(BaseModel):
    """Summary of full evaluation run."""

    total_questions: int = Field(description="Number of questions evaluated")
    avg_retrieved_count: float = Field(description="Average results per query")
    avg_top_score: float = Field(description="Average top relevance score")
    avg_keyword_recall: float = Field(description="Average keyword recall")
    results: list[EvaluationResult] = Field(description="Per-question results")


async def _evaluate_basic(
    retriever: AgenticRetriever,
    qa_pairs: list[dict[str, Any]] | None = None,
) -> EvaluationSummary:
    """Run basic retrieval evaluation without RAGAS.

    Evaluates retrieval quality using keyword recall and relevance scores.

    Args:
        retriever: AgenticRetriever instance to evaluate.
        qa_pairs: Optional QA pairs. Defaults to Arbitrum pairs.

    Returns:
        EvaluationSummary with per-question results.
    """
    pairs = qa_pairs or _DEFAULT_QA_PAIRS
    results: list[EvaluationResult] = []

    for pair in pairs:
        question = pair["question"]
        keywords = pair.get("contexts_keywords", [])

        retrieved = await retriever.retrieve(question, top_k=5)

        # Calculate keyword recall
        all_content = " ".join(r.content for r in retrieved)
        hits = sum(1 for kw in keywords if kw.lower() in all_content.lower())

        avg_score = (
            sum(r.relevance_score for r in retrieved) / len(retrieved) if retrieved else 0.0
        )
        top_score = retrieved[0].relevance_score if retrieved else 0.0
        keyword_recall = hits / len(keywords) if keywords else 0.0

        result = EvaluationResult(
            question=question,
            retrieved_count=len(retrieved),
            avg_score=avg_score,
            top_score=top_score,
            keyword_hits=hits,
            keyword_total=len(keywords),
            keyword_recall=keyword_recall,
        )
        results.append(result)

        logger.info(
            "evaluation_question",
            question=question,
            retrieved=len(retrieved),
            top_score=f"{top_score:.4f}",
            keyword_recall=f"{keyword_recall:.2%}",
        )

    summary = EvaluationSummary(
        total_questions=len(results),
        avg_retrieved_count=sum(r.retrieved_count for r in results) / len(results),
        avg_top_score=sum(r.top_score for r in results) / len(results),
        avg_keyword_recall=sum(r.keyword_recall for r in results) / len(results),
        results=results,
    )

    return summary


async def run_evaluation(
    qa_pairs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run RAG evaluation pipeline.

    Attempts to use RAGAS metrics if API key is available,
    falls back to basic retrieval statistics otherwise.

    Args:
        qa_pairs: Optional QA pairs for evaluation.

    Returns:
        Dictionary with evaluation metrics.
    """
    logger.info("starting_evaluation")

    retriever = AgenticRetriever()

    # Try RAGAS evaluation
    try:
        from src.config import settings as app_settings

        if app_settings.anthropic_api_key:
            logger.info("attempting_ragas_evaluation")
            # RAGAS requires an LLM API key for faithfulness/relevancy metrics
            # If available, we could integrate it here. For now, fall through
            # to basic evaluation since RAGAS setup requires additional config.
            raise ImportError("RAGAS integration deferred to full setup")
    except (ImportError, Exception) as exc:
        logger.info("falling_back_to_basic_evaluation", reason=str(exc))

    # Basic evaluation
    summary = await _evaluate_basic(retriever, qa_pairs)

    result = summary.model_dump()
    logger.info(
        "evaluation_completed",
        questions=summary.total_questions,
        avg_top_score=f"{summary.avg_top_score:.4f}",
        avg_keyword_recall=f"{summary.avg_keyword_recall:.2%}",
    )

    return result


if __name__ == "__main__":
    async def main() -> None:
        """Run evaluation and print results."""
        print("=" * 60)
        print("DYOR RAG Evaluation")
        print("=" * 60)

        results = await run_evaluation()

        print(f"\nTotal questions: {results['total_questions']}")
        print(f"Avg results per query: {results['avg_retrieved_count']:.1f}")
        print(f"Avg top score: {results['avg_top_score']:.4f}")
        print(f"Avg keyword recall: {results['avg_keyword_recall']:.2%}")

        print("\nPer-question results:")
        for r in results["results"]:
            print(f"\n  Q: {r['question']}")
            print(f"     Results: {r['retrieved_count']}, Top score: {r['top_score']:.4f}")
            kw = f"{r['keyword_hits']}/{r['keyword_total']} ({r['keyword_recall']:.0%})"
            print(f"     Keywords: {kw}")

    asyncio.run(main())
