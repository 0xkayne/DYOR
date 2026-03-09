"""Shared test fixtures for the DYOR test suite."""

import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.documents import Document


@pytest.fixture
def fixture_dir() -> Path:
    """Path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture(fixture_dir: Path):
    """Load a JSON fixture file by name."""
    def _load(name: str) -> dict[str, Any]:
        path = fixture_dir / name
        return json.loads(path.read_text(encoding="utf-8"))
    return _load


@pytest.fixture
def sample_markdown_content() -> str:
    """Sample markdown content with YAML front matter, headings, Chinese text, and images."""
    return '''---
project_name: Arbitrum
track: Layer2
date: "2024-01-15"
author: "Test Analyst"
keywords:
  - Layer2
  - Rollup
---

# Arbitrum 深度研究报告

## 项目概述

Arbitrum 是一个 Optimistic Rollup 解决方案，由 Offchain Labs 团队开发。

![架构图](images/architecture.png)

## 团队背景

Analyst: Test Analyst

团队成员包括多位来自普林斯顿大学的研究人员。创始人 Ed Felten 曾担任白宫技术顾问。

<img src="team.jpg" alt="团队照片" />

## 技术分析

### Optimistic Rollup 原理

Arbitrum 采用欺诈证明机制，挑战期为 7 天。

### 性能指标

TPS 可达 40,000+，Gas 费用相比以太坊主网降低 95%。

## 代币经济学

ARB 代币总量 100 亿，2024-03-16 将解锁大量代币。

## 风险因素

1. 竞争激烈
2. 技术风险
3. 监管不确定性
'''


@pytest.fixture
def sample_markdown_file(tmp_path: Path, sample_markdown_content: str) -> Path:
    """Write sample markdown to a temporary file and return the path."""
    file_path = tmp_path / "arbitrum_research_report.md"
    file_path.write_text(sample_markdown_content, encoding="utf-8")
    return file_path


@pytest.fixture
def mock_settings(monkeypatch):
    """Override settings for testing."""
    from src.config import settings
    monkeypatch.setattr(settings, "chunk_size", 200)
    monkeypatch.setattr(settings, "chunk_overlap", 50)
    monkeypatch.setattr(settings, "reranker_top_k", 3)
    monkeypatch.setattr(settings, "retriever_top_k", 5)
    monkeypatch.setattr(settings, "chroma_persist_dir", "/tmp/test_chroma")
    return settings


@pytest.fixture
def mock_llm_factory():
    """Create a configurable mock ChatAnthropic that returns specified JSON content."""
    from unittest.mock import AsyncMock, MagicMock

    def _create(response_content: str) -> MagicMock:
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = response_content
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        return mock_llm

    return _create


@pytest.fixture
def initial_state() -> dict:
    """Standard AgentState initial dict with all fields initialized."""
    return {
        "messages": [],
        "user_query": "分析 Arbitrum 是否值得投资",
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


@pytest.fixture
def valid_report() -> dict:
    """A minimal compliant report dict that passes guardrails validation."""
    return {
        "project_name": "Arbitrum",
        "analysis_date": "2026-03-09T00:00:00",
        "workflow_type": "deep_dive",
        "fundamental_analysis": {
            "summary": "Arbitrum is a leading L2 solution.",
            "team_score": 8.0,
            "product_score": 7.5,
            "track_score": 8.0,
            "tokenomics_score": 6.5,
            "sources": ["arbitrum_report.md"],
        },
        "market_data": None,
        "news_sentiment": None,
        "tokenomics": None,
        "investment_recommendation": {
            "rating": "buy",
            "confidence": 0.65,
            "key_reasons": ["Strong ecosystem", "Active development"],
            "risk_factors": ["Token unlock pressure", "Competition"],
            "disclaimer": "This is not financial advice. Always do your own research.",
        },
    }


@pytest.fixture
def async_client():
    """httpx.AsyncClient with ASGITransport for API testing."""
    import httpx
    from httpx import ASGITransport

    from api.main import app

    async def _create():
        transport = ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://test")

    return _create


@pytest.fixture
def mock_agent_settings(monkeypatch):
    """Override settings for testing with safe defaults."""
    from src.config import settings
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(settings, "agent_timeout", 5)
    monkeypatch.setattr(settings, "max_revision_count", 2)
    return settings


@pytest.fixture
def sample_documents() -> list[Document]:
    """Create 5 sample Document objects with metadata."""
    return [
        Document(
            page_content="Arbitrum 是一个 Optimistic Rollup 解决方案，由 Offchain Labs 团队开发。",
            metadata={
                "source": "arbitrum_report.md",
                "project_name": "Arbitrum",
                "chunk_index": 0,
                "section_title": "项目概述",
                "language": "zh",
                "score": 0.85,
            },
        ),
        Document(
            page_content="ARB 代币总量 100 亿，流通量约 12.75 亿。代币用于治理投票。",
            metadata={
                "source": "arbitrum_report.md",
                "project_name": "Arbitrum",
                "chunk_index": 1,
                "section_title": "代币经济学",
                "language": "zh",
                "score": 0.72,
            },
        ),
        Document(
            page_content="Optimism uses the OP Stack and has a different fraud proof mechanism.",
            metadata={
                "source": "optimism_report.md",
                "project_name": "Optimism",
                "chunk_index": 0,
                "section_title": "Overview",
                "language": "en",
                "score": 0.65,
            },
        ),
        Document(
            page_content=(
                "团队成员包括多位来自普林斯顿大学的研究人员。"
                "创始人 Ed Felten 曾担任白宫技术顾问。"
            ),
            metadata={
                "source": "arbitrum_report.md",
                "project_name": "Arbitrum",
                "chunk_index": 2,
                "section_title": "团队背景",
                "language": "zh",
                "score": 0.58,
            },
        ),
        Document(
            page_content=(
                "zkSync Era uses zero-knowledge proofs"
                " for transaction validation on Ethereum L2."
            ),
            metadata={
                "source": "zksync_report.md",
                "project_name": "zkSync",
                "chunk_index": 0,
                "section_title": "Technology",
                "language": "en",
                "score": 0.45,
            },
        ),
    ]
