"""Analysis endpoint for triggering deep-dive and comparison workflows.

Exposes a single ``POST /analyze`` endpoint that synchronously invokes the
LangGraph workflow and returns the full structured report.
"""

import asyncio
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.config import settings
from src.schemas.analysis import AnalysisReport

logger = structlog.get_logger(__name__)

analyze_router = APIRouter(prefix="/analyze", tags=["analyze"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AnalysisRequest(BaseModel):
    """Request body for triggering a full analysis workflow.

    Attributes:
        query: Natural-language research question or project name.
        workflow_type: Which workflow to run (deep_dive, compare, or brief).
        thread_id: Optional LangGraph thread ID for checkpointing; a UUID is
            generated automatically when omitted.
    """

    query: str
    workflow_type: Literal["deep_dive", "compare", "brief"] = "deep_dive"
    thread_id: str = Field(default_factory=lambda: str(uuid4()))


class AnalysisResponse(BaseModel):
    """Response from a completed analysis workflow run.

    Attributes:
        thread_id: The LangGraph thread ID used for this run.
        report: The full structured analysis report.
        completed_at: UTC timestamp when the workflow finished.
    """

    thread_id: str
    report: AnalysisReport
    completed_at: datetime


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@analyze_router.post("", response_model=AnalysisResponse)
async def run_analysis(body: AnalysisRequest, request: Request) -> AnalysisResponse:
    """Invoke the LangGraph analysis workflow and return the complete report.

    Args:
        body: AnalysisRequest with query, workflow type, and optional thread ID.
        request: FastAPI Request used to access ``app.state``.

    Returns:
        AnalysisResponse containing the thread_id, full report, and completion time.

    Raises:
        HTTPException: 503 if the workflow is not yet available; 504 on timeout.
    """
    workflow = request.app.state.workflow
    if workflow is None:
        raise HTTPException(
            status_code=503,
            detail="Workflow not available — the LangGraph graph failed to initialise.",
        )

    semaphore: asyncio.Semaphore = request.app.state.semaphore
    config = {"configurable": {"thread_id": body.thread_id}}
    input_state = {
        "query": body.query,
        "workflow_type": body.workflow_type,
    }

    logger.info(
        "analysis requested",
        thread_id=body.thread_id,
        workflow_type=body.workflow_type,
        query=body.query[:120],
    )

    async def _invoke() -> dict:
        async with semaphore:
            return await workflow.ainvoke(input_state, config=config)

    try:
        raw_result: dict = await asyncio.wait_for(
            _invoke(),
            timeout=float(settings.agent_timeout),
        )
    except asyncio.TimeoutError as exc:
        logger.warning("analysis timed out", thread_id=body.thread_id)
        raise HTTPException(
            status_code=504,
            detail=f"Analysis timed out after {settings.agent_timeout}s.",
        ) from exc

    # The workflow is expected to return an AnalysisReport-compatible dict or object.
    if isinstance(raw_result, AnalysisReport):
        report = raw_result
    elif isinstance(raw_result, dict):
        # Workflows may nest the report inside a "report" key.
        report_data = raw_result.get("report", raw_result)
        report = AnalysisReport(**report_data) if isinstance(report_data, dict) else report_data
    else:
        logger.error("unexpected workflow result type", type=type(raw_result).__name__)
        raise HTTPException(status_code=500, detail="Unexpected workflow result format.")

    completed_at = datetime.now(tz=timezone.utc)
    logger.info("analysis completed", thread_id=body.thread_id, project=report.project_name)
    return AnalysisResponse(thread_id=body.thread_id, report=report, completed_at=completed_at)
