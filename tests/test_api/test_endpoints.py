"""Tests for the FastAPI endpoints."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from httpx import ASGITransport

from api.main import app


class TestApiImport:
    def test_api_module_importable(self):
        from api import main  # noqa: F401


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        """GET /health should return 200."""
        app.state.workflow = None
        app.state.semaphore = asyncio.Semaphore(5)
        app.state.result_cache = {}
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestAnalyzeEndpoint:
    @pytest.mark.asyncio
    async def test_post_analyze_success(self):
        """POST /analyze with valid payload should return 200."""
        mock_workflow = MagicMock()
        mock_result = {
            "project_name": "Arbitrum",
            "analysis_date": "2026-03-09T00:00:00",
            "workflow_type": "deep_dive",
        }
        mock_workflow.ainvoke = AsyncMock(return_value={"report": mock_result})

        app.state.workflow = mock_workflow
        app.state.semaphore = asyncio.Semaphore(5)
        app.state.result_cache = {}

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze", json={"query": "分析 Arbitrum", "workflow_type": "deep_dive"})
        assert response.status_code == 200
        data = response.json()
        assert "report" in data
        assert "thread_id" in data

    @pytest.mark.asyncio
    async def test_post_analyze_validation_error(self):
        """POST /analyze with missing fields should return 422."""
        app.state.workflow = MagicMock()
        app.state.semaphore = asyncio.Semaphore(5)
        app.state.result_cache = {}
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_analyze_returns_schema(self):
        """Response should match AnalysisResponse schema."""
        mock_workflow = MagicMock()
        mock_result = {
            "project_name": "Arbitrum",
            "analysis_date": "2026-03-09T00:00:00",
            "workflow_type": "deep_dive",
        }
        mock_workflow.ainvoke = AsyncMock(return_value={"report": mock_result})

        app.state.workflow = mock_workflow
        app.state.semaphore = asyncio.Semaphore(5)
        app.state.result_cache = {}

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze", json={"query": "test"})
        data = response.json()
        assert "completed_at" in data


class TestWebSocketChat:
    @pytest.mark.asyncio
    async def test_websocket_connect(self):
        """WebSocket /ws/chat should accept connections."""
        from starlette.testclient import TestClient

        app.state.workflow = None
        app.state.semaphore = asyncio.Semaphore(5)
        app.state.result_cache = {}

        client = TestClient(app)
        import json
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"query": "test", "workflow_type": "qa"}))
            data = ws.receive_text()
            msg = json.loads(data)
            # Should get an error since workflow is None
            assert msg["type"] == "error"

    @pytest.mark.asyncio
    async def test_websocket_stream_response(self):
        """WebSocket should stream response from cached results."""
        from starlette.testclient import TestClient
        from api.middleware.streaming import StreamMessage
        from datetime import datetime, timezone

        cached_msg = StreamMessage(
            type="result", agent="analyst", content="test result",
            timestamp=datetime.now(tz=timezone.utc),
        )
        thread_id = "cached-thread-123"

        app.state.workflow = MagicMock()
        app.state.semaphore = asyncio.Semaphore(5)
        app.state.result_cache = {thread_id: [cached_msg]}

        client = TestClient(app)
        import json
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_text(json.dumps({"query": "test", "thread_id": thread_id, "workflow_type": "qa"}))
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "result"
            assert msg["content"] == "test result"


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_error_response_format(self):
        """workflow=None should return 503."""
        app.state.workflow = None
        app.state.semaphore = asyncio.Semaphore(5)
        app.state.result_cache = {}

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze", json={"query": "test"})
        assert response.status_code == 503
