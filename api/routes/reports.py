"""Report management endpoints for CRUD operations on analysis reports.

Stores reports as JSON files under ``data/saved_reports/``.  File names are
UUIDs, which also prevents path-traversal attacks.
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.schemas.analysis import AnalysisReport

logger = structlog.get_logger(__name__)

REPORTS_DIR = Path("data/saved_reports")

reports_router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SaveReportRequest(BaseModel):
    """Request body for saving a new analysis report.

    Attributes:
        report: The complete AnalysisReport to persist.
    """

    report: AnalysisReport


class ReportSummary(BaseModel):
    """Lightweight summary of a stored report used in list responses.

    Attributes:
        id: UUID-based filename (without extension).
        project_name: Name of the analysed project.
        workflow_type: The workflow used to produce the report.
        analysis_date: When the analysis was performed.
    """

    id: str
    project_name: str
    workflow_type: Literal["deep_dive", "compare", "brief", "qa"]
    analysis_date: datetime


class ReportListResponse(BaseModel):
    """Paginated list of report summaries.

    Attributes:
        reports: The list of report summaries.
        total: Total number of stored reports.
    """

    reports: list[ReportSummary]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_uuid(report_id: str) -> None:
    """Raise HTTP 400 if *report_id* is not a valid UUID4 string.

    Args:
        report_id: The candidate report identifier from the URL path.

    Raises:
        HTTPException: 400 if the value is not a valid UUID.
    """
    try:
        uuid.UUID(report_id, version=4)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid report ID format") from exc


def _report_path(report_id: str) -> Path:
    """Return the absolute Path for a report file given its ID.

    Args:
        report_id: A validated UUID string.

    Returns:
        Path object pointing to the JSON file.
    """
    return REPORTS_DIR / f"{report_id}.json"


async def _read_report_file(path: Path) -> dict:
    """Read and JSON-parse a report file asynchronously.

    Args:
        path: Absolute path to the JSON file.

    Returns:
        Parsed report dict.

    Raises:
        HTTPException: 404 if the file does not exist.
    """

    def _read() -> dict:
        if not path.exists():
            raise FileNotFoundError
        return json.loads(path.read_text(encoding="utf-8"))

    try:
        return await asyncio.to_thread(_read)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@reports_router.get("", response_model=ReportListResponse)
async def list_reports() -> ReportListResponse:
    """List all saved analysis reports.

    Returns:
        ReportListResponse containing summaries of all stored reports.
    """

    def _scan() -> list[dict]:
        if not REPORTS_DIR.exists():
            return []
        summaries: list[dict] = []
        for fp in sorted(REPORTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                summaries.append(
                    {
                        "id": fp.stem,
                        "project_name": data.get("project_name", "unknown"),
                        "workflow_type": data.get("workflow_type", "qa"),
                        "analysis_date": data.get("analysis_date", datetime.now().isoformat()),
                    }
                )
            except Exception:  # noqa: BLE001
                logger.warning("skipping unreadable report file", path=str(fp))
        return summaries

    raw_summaries = await asyncio.to_thread(_scan)
    summaries = [ReportSummary(**s) for s in raw_summaries]
    return ReportListResponse(reports=summaries, total=len(summaries))


@reports_router.get("/{report_id}", response_model=AnalysisReport)
async def get_report(report_id: str) -> AnalysisReport:
    """Retrieve a single analysis report by its ID.

    Args:
        report_id: UUID-based report identifier.

    Returns:
        The full AnalysisReport.

    Raises:
        HTTPException: 400 for invalid IDs, 404 if not found.
    """
    _validate_uuid(report_id)
    data = await _read_report_file(_report_path(report_id))
    return AnalysisReport(**data)


@reports_router.post("", status_code=201)
async def save_report(body: SaveReportRequest) -> dict[str, str]:
    """Persist an analysis report and return its generated ID.

    Args:
        body: SaveReportRequest containing the report to store.

    Returns:
        Dict with a single ``id`` key holding the UUID of the saved report.
    """
    report_id = str(uuid.uuid4())
    path = _report_path(report_id)

    def _write() -> None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(body.report.model_dump_json(indent=2), encoding="utf-8")

    await asyncio.to_thread(_write)
    logger.info("report saved", report_id=report_id, project=body.report.project_name)
    return {"id": report_id}


@reports_router.delete("/{report_id}", status_code=204)
async def delete_report(report_id: str) -> None:
    """Delete a saved analysis report.

    Args:
        report_id: UUID-based report identifier.

    Raises:
        HTTPException: 400 for invalid IDs, 404 if not found.
    """
    _validate_uuid(report_id)
    path = _report_path(report_id)

    def _delete() -> None:
        if not path.exists():
            raise FileNotFoundError
        path.unlink()

    try:
        await asyncio.to_thread(_delete)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc

    logger.info("report deleted", report_id=report_id)
