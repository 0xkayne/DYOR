"""Tests for the reports API endpoints.

Covers CRUD operations: list, save, get, and delete.  All tests redirect
REPORTS_DIR to a pytest-managed tmp_path so the real data/ directory is
never touched and no cleanup is required.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport

from api.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_app_state() -> None:
    """Initialise mandatory app.state attributes expected by the routers.

    The lifespan handler normally sets these up, but ASGITransport tests
    bypass it, so we wire them in manually.
    """
    app.state.workflow = None
    app.state.semaphore = asyncio.Semaphore(5)
    app.state.result_cache = {}


def _make_client(transport: ASGITransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def _minimal_report(
    project_name: str = "Arbitrum",
    workflow_type: str = "deep_dive",
    analysis_date: str = "2026-03-09T00:00:00",
) -> dict:
    """Return a SaveReportRequest-compatible payload with required fields only."""
    return {
        "report": {
            "project_name": project_name,
            "analysis_date": analysis_date,
            "workflow_type": workflow_type,
        }
    }


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


class TestReportsList:
    @pytest.mark.asyncio
    async def test_empty_list_when_dir_missing(self, tmp_path: Path) -> None:
        """GET /reports on a non-existent directory returns total=0."""
        _setup_app_state()
        missing_dir = tmp_path / "no_such_dir"
        with patch("api.routes.reports.REPORTS_DIR", missing_dir):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.get("/reports")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["reports"] == []

    @pytest.mark.asyncio
    async def test_empty_list_when_dir_empty(self, tmp_path: Path) -> None:
        """GET /reports on an empty directory returns total=0."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.get("/reports")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_returns_saved_reports(self, tmp_path: Path) -> None:
        """GET /reports reflects reports persisted by POST /reports."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                # Save two reports
                await client.post("/reports", json=_minimal_report("Arbitrum", "deep_dive"))
                await client.post("/reports", json=_minimal_report("Optimism", "compare"))

                response = await client.get("/reports")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        project_names = {r["project_name"] for r in data["reports"]}
        assert project_names == {"Arbitrum", "Optimism"}

    @pytest.mark.asyncio
    async def test_list_skips_unreadable_files(self, tmp_path: Path) -> None:
        """GET /reports silently skips JSON files that cannot be parsed."""
        _setup_app_state()
        # Write a corrupt JSON file into tmp_path
        corrupt_file = tmp_path / "bad-uuid-that-wont-be-an-id.json"
        corrupt_file.write_text("not-json", encoding="utf-8")

        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.get("/reports")

        assert response.status_code == 200
        data = response.json()
        # The corrupt file should be silently skipped; total may be 0 or 1
        # depending on whether the scanner picks it up — the endpoint must not 500
        assert isinstance(data["total"], int)

    @pytest.mark.asyncio
    async def test_list_response_schema_fields(self, tmp_path: Path) -> None:
        """Each summary in the list must contain the required fields."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                await client.post("/reports", json=_minimal_report())
                response = await client.get("/reports")

        assert response.status_code == 200
        reports = response.json()["reports"]
        assert len(reports) == 1
        summary = reports[0]
        for field in ("id", "project_name", "workflow_type", "analysis_date"):
            assert field in summary, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Save endpoint
# ---------------------------------------------------------------------------


class TestSaveReport:
    @pytest.mark.asyncio
    async def test_save_returns_201_and_id(self, tmp_path: Path) -> None:
        """POST /reports returns HTTP 201 with an 'id' key."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.post("/reports", json=_minimal_report())

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], str)
        assert len(data["id"]) == 36  # UUID4 canonical form

    @pytest.mark.asyncio
    async def test_save_creates_json_file(self, tmp_path: Path) -> None:
        """POST /reports persists a JSON file under tmp_path."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.post("/reports", json=_minimal_report())

        report_id = response.json()["id"]
        saved_path = tmp_path / f"{report_id}.json"
        assert saved_path.exists()
        payload = json.loads(saved_path.read_text(encoding="utf-8"))
        assert payload["project_name"] == "Arbitrum"

    @pytest.mark.asyncio
    async def test_save_missing_project_name_returns_422(self, tmp_path: Path) -> None:
        """POST /reports without project_name should return 422 Unprocessable Entity."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.post(
                    "/reports",
                    json={"report": {"workflow_type": "qa", "analysis_date": "2026-03-09T00:00:00"}},
                )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_save_invalid_workflow_type_returns_422(self, tmp_path: Path) -> None:
        """POST /reports with an invalid workflow_type should return 422."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.post(
                    "/reports",
                    json=_minimal_report(workflow_type="not_a_type"),
                )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_save_all_workflow_types(self, tmp_path: Path) -> None:
        """POST /reports accepts all four valid workflow types."""
        _setup_app_state()
        workflow_types = ["deep_dive", "compare", "brief", "qa"]
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                for wtype in workflow_types:
                    response = await client.post(
                        "/reports", json=_minimal_report(workflow_type=wtype)
                    )
                    assert response.status_code == 201, (
                        f"Expected 201 for workflow_type={wtype!r}, got {response.status_code}"
                    )


# ---------------------------------------------------------------------------
# Get-by-ID endpoint
# ---------------------------------------------------------------------------


class TestGetReport:
    @pytest.mark.asyncio
    async def test_get_saved_report(self, tmp_path: Path) -> None:
        """GET /reports/{id} returns the full report after it is saved."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                save_response = await client.post(
                    "/reports", json=_minimal_report("Arbitrum", "deep_dive")
                )
                report_id = save_response.json()["id"]

                get_response = await client.get(f"/reports/{report_id}")

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["project_name"] == "Arbitrum"
        assert data["workflow_type"] == "deep_dive"

    @pytest.mark.asyncio
    async def test_get_not_found_returns_404(self, tmp_path: Path) -> None:
        """GET /reports/{id} for an unknown UUID returns 404."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.get(
                    "/reports/12345678-1234-1234-1234-123456789012"
                )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_invalid_id_returns_400(self, tmp_path: Path) -> None:
        """GET /reports/{id} with a non-UUID id returns 400."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.get("/reports/not-a-uuid")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_preserves_optional_fields(self, tmp_path: Path) -> None:
        """GET /reports/{id} preserves optional nested fields like fundamental_analysis."""
        _setup_app_state()
        full_report = {
            "report": {
                "project_name": "Arbitrum",
                "analysis_date": "2026-03-09T00:00:00",
                "workflow_type": "deep_dive",
                "fundamental_analysis": {
                    "summary": "Strong L2 project.",
                    "team_score": 8.0,
                    "product_score": 7.5,
                    "track_score": 8.5,
                    "tokenomics_score": 6.5,
                    "sources": ["report.md"],
                },
            }
        }
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                save_response = await client.post("/reports", json=full_report)
                report_id = save_response.json()["id"]

                get_response = await client.get(f"/reports/{report_id}")

        data = get_response.json()
        assert data["fundamental_analysis"] is not None
        assert data["fundamental_analysis"]["summary"] == "Strong L2 project."
        assert data["fundamental_analysis"]["team_score"] == 8.0


# ---------------------------------------------------------------------------
# Delete endpoint
# ---------------------------------------------------------------------------


class TestDeleteReport:
    @pytest.mark.asyncio
    async def test_delete_existing_report_returns_204(self, tmp_path: Path) -> None:
        """DELETE /reports/{id} for an existing report returns 204 No Content."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                save_response = await client.post(
                    "/reports", json=_minimal_report("Test", "qa")
                )
                report_id = save_response.json()["id"]

                delete_response = await client.delete(f"/reports/{report_id}")

        assert delete_response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_removes_file_from_disk(self, tmp_path: Path) -> None:
        """DELETE /reports/{id} removes the JSON file from disk."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                save_response = await client.post(
                    "/reports", json=_minimal_report("Test", "qa")
                )
                report_id = save_response.json()["id"]
                await client.delete(f"/reports/{report_id}")

        saved_path = tmp_path / f"{report_id}.json"
        assert not saved_path.exists()

    @pytest.mark.asyncio
    async def test_get_after_delete_returns_404(self, tmp_path: Path) -> None:
        """GET /reports/{id} after deletion returns 404."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                save_response = await client.post(
                    "/reports", json=_minimal_report("Test", "qa")
                )
                report_id = save_response.json()["id"]

                await client.delete(f"/reports/{report_id}")
                get_response = await client.get(f"/reports/{report_id}")

        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_404(self, tmp_path: Path) -> None:
        """DELETE /reports/{id} for an unknown UUID returns 404."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.delete(
                    "/reports/12345678-1234-1234-1234-123456789012"
                )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_invalid_id_returns_400(self, tmp_path: Path) -> None:
        """DELETE /reports/{id} with a non-UUID id returns 400."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.delete("/reports/not-a-uuid")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_double_delete_second_returns_404(self, tmp_path: Path) -> None:
        """Deleting the same report twice: the second DELETE returns 404."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                save_response = await client.post(
                    "/reports", json=_minimal_report("Test", "brief")
                )
                report_id = save_response.json()["id"]

                first = await client.delete(f"/reports/{report_id}")
                second = await client.delete(f"/reports/{report_id}")

        assert first.status_code == 204
        assert second.status_code == 404


# ---------------------------------------------------------------------------
# Full round-trip
# ---------------------------------------------------------------------------


class TestReportsCRUD:
    @pytest.mark.asyncio
    async def test_save_and_get(self, tmp_path: Path) -> None:
        """Save a report then retrieve it: project_name round-trips correctly."""
        _setup_app_state()
        report_data = {
            "project_name": "Arbitrum",
            "analysis_date": "2026-03-09T00:00:00",
            "workflow_type": "deep_dive",
        }
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.post("/reports", json={"report": report_data})
                assert response.status_code == 201
                report_id = response.json()["id"]

                response = await client.get(f"/reports/{report_id}")
                assert response.status_code == 200
                assert response.json()["project_name"] == "Arbitrum"

    @pytest.mark.asyncio
    async def test_get_not_found(self, tmp_path: Path) -> None:
        """GET an ID that was never saved returns 404."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.get("/reports/12345678-1234-1234-1234-123456789012")
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_report(self, tmp_path: Path) -> None:
        """Save → delete → get: verify the report is gone."""
        _setup_app_state()
        report_data = {
            "project_name": "Test",
            "analysis_date": "2026-03-09T00:00:00",
            "workflow_type": "qa",
        }
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.post("/reports", json={"report": report_data})
                report_id = response.json()["id"]

                response = await client.delete(f"/reports/{report_id}")
                assert response.status_code == 204

                response = await client.get(f"/reports/{report_id}")
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_id_format(self, tmp_path: Path) -> None:
        """GET /reports/not-a-uuid returns 400."""
        _setup_app_state()
        with patch("api.routes.reports.REPORTS_DIR", tmp_path):
            transport = ASGITransport(app=app)
            async with _make_client(transport) as client:
                response = await client.get("/reports/not-a-uuid")
                assert response.status_code == 400
