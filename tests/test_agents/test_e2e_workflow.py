"""End-to-end workflow test for the multi-agent system.

Tests the full pipeline from query input to structured report output,
mocking external API calls to LLM and MCP servers.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import AgentState
from src.graph.workflow import build_workflow, compile_workflow
from src.guardrails import validate_output


# --- Mock LLM responses ---

ROUTER_RESPONSE = json.dumps({
    "workflow_type": "deep_dive",
    "target_entities": ["Kite AI"],
    "reasoning": "User wants a deep analysis of Kite AI project"
})

PLANNER_RESPONSE = json.dumps({
    "plan": ["rag", "market", "news", "tokenomics"],
    "reasoning": "Deep dive requires all agents"
})

ANALYST_RESPONSE = json.dumps({
    "project_name": "Kite AI",
    "analysis_date": "2026-03-09T00:00:00",
    "workflow_type": "deep_dive",
    "fundamental_analysis": {
        "summary": "Kite AI 是一个专注于去中心化 AI 计算的项目，团队具有丰富的 AI 和区块链经验。"
                   "产品已上线主网，拥有较多的用户基础。赛道处于 AI+Crypto 的热门交叉领域。",
        "team_score": 7.0,
        "product_score": 7.5,
        "track_score": 8.0,
        "tokenomics_score": 6.5,
        "sources": ["kite_ai_research_report_2026.pdf", "ai_crypto_sector_overview.md"]
    },
    "market_data": {
        "current_price": 0.045,
        "price_change_24h": 3.2,
        "price_change_7d": -5.1,
        "market_cap": 45000000,
        "volume_24h": 2300000,
        "technical_summary": "RSI 中性，短期均线上穿长期均线，趋势中性偏多"
    },
    "news_sentiment": {
        "overall_sentiment": "positive",
        "sentiment_score": 0.35,
        "key_events": ["Kite AI 宣布与主要云计算提供商合作", "社区治理提案通过"],
        "news_summary": "近期新闻以正面为主，主要围绕合作伙伴关系和产品进展"
    },
    "tokenomics": {
        "circulating_supply_ratio": 0.45,
        "next_unlock_summary": "下一次解锁在 2026 年 Q2，约释放总量 5%",
        "distribution_summary": "代币分配较为分散，团队持有 20%，社区 40%",
        "tokenomics_risk": "medium"
    },
    "investment_recommendation": {
        "rating": "buy",
        "confidence": 0.65,
        "key_reasons": [
            "AI+Crypto 赛道处于上升期，Kite AI 具有先发优势",
            "产品已上线且有实际用户，非纯概念项目",
            "近期合作伙伴关系拓展表明项目发展健康"
        ],
        "risk_factors": [
            "代币流通比例仅 45%，未来解锁可能带来抛压",
            "AI+Crypto 赛道竞争日趋激烈",
            "市值较小，流动性风险较高"
        ],
        "disclaimer": "本分析仅供参考，不构成投资建议。加密货币投资风险极高，请做好自己的研究。"
    }
})

CRITIC_APPROVE_RESPONSE = json.dumps({
    "approved": True,
    "feedback": "Report is well-structured with balanced analysis.",
    "issues": []
})


def _make_mock_llm_response(content: str) -> MagicMock:
    """Create a mock LLM response with the given content."""
    response = MagicMock()
    response.content = content
    return response


def _make_mock_llm(responses: list[str]) -> MagicMock:
    """Create a mock ChatAnthropic that returns responses in order."""
    mock = MagicMock()
    mock_responses = [_make_mock_llm_response(r) for r in responses]
    mock.ainvoke = AsyncMock(side_effect=mock_responses)
    return mock


@pytest.fixture
def initial_state() -> dict:
    """Create the initial state for testing."""
    return {
        "messages": [],
        "user_query": "分析 Kite AI 是否值得投资",
        "workflow_type": "",
        "target_entities": [],
        "execution_plan": [],
        "rag_result": None,
        "market_data": None,
        "news_data": None,
        "tokenomics_data": None,
        "analysis_report": None,
        "critic_feedback": None,
        "critic_approved": False,
        "revision_count": 0,
    }


@pytest.mark.asyncio
async def test_full_workflow_e2e(initial_state: dict) -> None:
    """Test the complete workflow from query to final report.

    Mocks all external calls (LLM, MCP servers, RAG) and verifies:
    1. The workflow runs to completion
    2. The final report has all required fields
    3. Guardrails validation passes
    4. Disclaimer is present
    """
    # Mock RAG retriever
    mock_retrieval_result = MagicMock()
    mock_retrieval_result.content = "Kite AI 是一个 AI+Crypto 项目，团队经验丰富。"
    mock_retrieval_result.source = "kite_ai_research_report_2026.pdf"
    mock_retrieval_result.project_name = "Kite AI"
    mock_retrieval_result.chunk_index = 0
    mock_retrieval_result.relevance_score = 0.85
    mock_retrieval_result.retrieval_method = "hybrid"

    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(return_value=[mock_retrieval_result])

    # Mock MCP server calls
    mock_price = {
        "current_price": 0.045, "price_change_24h": 3.2, "price_change_7d": -5.1,
        "market_cap": 45000000, "volume_24h": 2300000, "technical_indicators": {},
        "data_source": "coingecko", "fetched_at": datetime.now().isoformat(),
    }
    mock_indicators = {
        "coin_id": "kite-ai", "sma_7": 0.043, "sma_20": 0.042, "rsi_14": 55.0,
        "volatility": 0.05, "data_source": "coingecko", "fetched_at": datetime.now().isoformat(),
    }
    mock_overview = {
        "total_market_cap": 2500000000000, "btc_dominance": 52.5,
        "fear_greed_index": 65, "data_source": "coingecko",
        "fetched_at": datetime.now().isoformat(),
    }
    mock_news_search = {
        "news": [{"title": "Kite AI announces partnership", "sentiment": "positive"}],
        "count": 1, "data_source": "cryptopanic", "fetched_at": datetime.now().isoformat(),
    }
    mock_sentiment = {
        "overall_sentiment": "positive", "sentiment_score": 0.35,
        "key_events": [], "data_source": "cryptopanic",
        "fetched_at": datetime.now().isoformat(),
    }
    mock_unlock = {
        "next_unlock": None, "circulating_supply_ratio": 0.45,
        "top_holders_concentration": 0.2, "unlock_schedule": [],
        "data_source": "local", "fetched_at": datetime.now().isoformat(),
    }
    mock_distribution = {
        "distribution": {"team": 0.2, "community": 0.4, "investors": 0.25, "ecosystem": 0.15},
        "data_source": "local", "fetched_at": datetime.now().isoformat(),
    }

    with (
        # Mock LLMs for router, planner, analyst, critic
        patch("src.agents.router.RouterAgent._call_llm", new_callable=AsyncMock,
              return_value=json.loads(ROUTER_RESPONSE)),
        patch("src.agents.planner.PlannerAgent._call_llm", new_callable=AsyncMock,
              return_value=["rag_agent", "market_agent", "news_agent", "tokenomics_agent"]),
        patch("src.agents.analyst.AnalystAgent._generate", new_callable=AsyncMock,
              return_value=json.loads(ANALYST_RESPONSE)),
        patch("src.agents.critic.CriticAgent._review", new_callable=AsyncMock,
              return_value=json.loads(CRITIC_APPROVE_RESPONSE)),
        # Mock RAG
        patch("src.agents.rag_agent.RAGAgent.__init__", return_value=None),
        patch("src.agents.rag_agent._rag_agent._retriever", mock_retriever, create=True),
        patch("src.agents.rag_agent._rag_agent._retrieve", new_callable=AsyncMock,
              return_value={
                  "results": [{"content": mock_retrieval_result.content,
                               "source": mock_retrieval_result.source,
                               "project_name": "Kite AI", "relevance_score": 0.85}],
                  "sources": ["kite_ai_research_report_2026.pdf"],
                  "query": "分析 Kite AI 是否值得投资",
              }),
        # Mock MCP servers
        patch("src.agents.market_agent.get_price", new_callable=AsyncMock,
              return_value=mock_price),
        patch("src.agents.market_agent.calculate_technical_indicators", new_callable=AsyncMock,
              return_value=mock_indicators),
        patch("src.agents.market_agent.get_market_overview", new_callable=AsyncMock,
              return_value=mock_overview),
        patch("src.agents.news_agent.search_news", new_callable=AsyncMock,
              return_value=mock_news_search),
        patch("src.agents.news_agent.analyze_sentiment", new_callable=AsyncMock,
              return_value=mock_sentiment),
        patch("src.agents.tokenomics_agent.get_unlock_schedule", new_callable=AsyncMock,
              return_value=mock_unlock),
        patch("src.agents.tokenomics_agent.get_token_distribution", new_callable=AsyncMock,
              return_value=mock_distribution),
    ):
        app = compile_workflow()
        result = await app.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": "test_e2e_001"}},
        )

    # Verify workflow completed
    assert result is not None, "Workflow returned None"
    assert result.get("critic_approved") is True, "Critic did not approve"

    # Verify report structure
    report = result.get("analysis_report")
    assert report is not None, "No analysis report generated"
    assert report["project_name"] == "Kite AI"
    assert report["workflow_type"] == "deep_dive"

    # Verify fundamental analysis
    fa = report.get("fundamental_analysis")
    assert fa is not None, "No fundamental analysis"
    assert 1 <= fa["team_score"] <= 10
    assert 1 <= fa["product_score"] <= 10
    assert len(fa["sources"]) > 0, "No sources cited"

    # Verify investment recommendation
    rec = report.get("investment_recommendation")
    assert rec is not None, "No investment recommendation"
    assert rec["rating"] in {"strong_buy", "buy", "hold", "sell", "strong_sell"}
    assert 0 <= rec["confidence"] <= 0.8
    assert len(rec["key_reasons"]) >= 2
    assert len(rec["risk_factors"]) >= 2
    assert rec["disclaimer"], "Disclaimer is empty"

    # Verify guardrails pass
    is_valid, issues = validate_output(report)
    assert is_valid, f"Guardrails validation failed: {issues}"

    # Verify workflow metadata
    assert result.get("workflow_type") == "deep_dive"
    assert "Kite AI" in result.get("target_entities", [])

    print("\n=== E2E Test PASSED ===")
    print(f"Project: {report['project_name']}")
    print(f"Rating: {rec['rating']} (confidence: {rec['confidence']})")
    print(f"Sources: {fa['sources']}")
    print(f"Key reasons: {len(rec['key_reasons'])}")
    print(f"Risk factors: {len(rec['risk_factors'])}")


@pytest.mark.asyncio
async def test_guardrails_reject_and_revision(initial_state: dict) -> None:
    """Test that the critic rejects a bad report and triggers revision.

    The first analyst pass produces a report with forbidden patterns,
    critic rejects it, then the second pass produces a clean report.
    """
    bad_report = json.loads(ANALYST_RESPONSE)
    bad_report["investment_recommendation"]["key_reasons"].append("这个项目一定会涨")

    good_report = json.loads(ANALYST_RESPONSE)

    critic_reject = {
        "approved": False,
        "feedback": "Report contains forbidden absolute language: '一定会涨'",
        "issues": [{"category": "compliance", "severity": "critical",
                    "description": "Absolute investment claim detected"}],
    }
    critic_approve = json.loads(CRITIC_APPROVE_RESPONSE)

    analyst_call_count = 0

    async def mock_analyst_generate(*args, **kwargs):
        nonlocal analyst_call_count
        analyst_call_count += 1
        if analyst_call_count == 1:
            return bad_report
        return good_report

    async def mock_critic_review(report):
        report_text = json.dumps(report, ensure_ascii=False)
        if "一定会涨" in report_text:
            return critic_reject
        return critic_approve

    with (
        patch("src.agents.router.RouterAgent._call_llm", new_callable=AsyncMock,
              return_value=json.loads(ROUTER_RESPONSE)),
        patch("src.agents.planner.PlannerAgent._call_llm", new_callable=AsyncMock,
              return_value=["rag_agent"]),
        patch("src.agents.analyst.AnalystAgent._generate", side_effect=mock_analyst_generate),
        patch("src.agents.critic.CriticAgent._review", side_effect=mock_critic_review),
        patch("src.agents.rag_agent._rag_agent._retrieve", new_callable=AsyncMock,
              return_value={
                  "results": [{"content": "Kite AI analysis", "source": "report.pdf",
                               "project_name": "Kite AI", "relevance_score": 0.8}],
                  "sources": ["report.pdf"], "query": initial_state["user_query"],
              }),
    ):
        app = compile_workflow()
        result = await app.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": "test_revision_001"}},
        )

    assert result.get("critic_approved") is True
    assert analyst_call_count == 2, f"Expected 2 analyst calls, got {analyst_call_count}"

    report = result["analysis_report"]
    report_text = json.dumps(report, ensure_ascii=False)
    assert "一定会涨" not in report_text, "Forbidden pattern still in final report"

    print("\n=== Revision Test PASSED ===")
    print(f"Analyst invocations: {analyst_call_count}")


@pytest.mark.asyncio
async def test_max_revision_count_enforced(initial_state: dict) -> None:
    """Test that revision count is capped at 2 to prevent infinite loops."""
    bad_report = json.loads(ANALYST_RESPONSE)
    bad_report["investment_recommendation"]["confidence"] = 0.95  # Always fails validation

    critic_reject = {
        "approved": False,
        "feedback": "Confidence too high",
        "issues": [{"category": "compliance", "severity": "critical",
                    "description": "Confidence > 0.8"}],
    }

    with (
        patch("src.agents.router.RouterAgent._call_llm", new_callable=AsyncMock,
              return_value=json.loads(ROUTER_RESPONSE)),
        patch("src.agents.planner.PlannerAgent._call_llm", new_callable=AsyncMock,
              return_value=["rag_agent"]),
        patch("src.agents.analyst.AnalystAgent._generate", new_callable=AsyncMock,
              return_value=bad_report),
        patch("src.agents.critic.CriticAgent._review", new_callable=AsyncMock,
              return_value=critic_reject),
        patch("src.agents.rag_agent._rag_agent._retrieve", new_callable=AsyncMock,
              return_value={"results": [], "sources": [], "query": initial_state["user_query"]}),
    ):
        app = compile_workflow()
        result = await app.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": "test_maxrev_001"}},
        )

    # Should auto-approve after max revisions
    assert result.get("critic_approved") is True
    assert result.get("revision_count") >= 2
    print(f"\n=== Max Revision Test PASSED (revision_count={result['revision_count']}) ===")
