"""FastAPI application entry point.

Creates the FastAPI app with:
- Lifespan handler that lazily loads the LangGraph workflow on startup.
- CORS middleware permitting requests from the Streamlit frontend.
- WebSocket, SSE, REST, and report-management routers.
- A ``/health`` liveness endpoint.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import analyze_router, chat_router, reports_router

logger = structlog.get_logger(__name__)

# Maximum number of concurrently executing LangGraph workflows.
_MAX_CONCURRENT_WORKFLOWS = 5

# Directory where analysis reports are persisted.
_REPORTS_DIR = Path("data/saved_reports")


# ---------------------------------------------------------------------------
# Workflow loader
# ---------------------------------------------------------------------------


def _load_workflow() -> Any | None:
    """Attempt to import and build the LangGraph workflow.

    Returns ``None`` gracefully when the ``src.graph.workflow`` module is a
    stub or has not been implemented yet, so the API can still start up.

    Returns:
        A compiled LangGraph application, or None if unavailable.
    """
    try:
        from src.graph.workflow import build_workflow  # type: ignore[import]

        workflow = build_workflow()
        logger.info("LangGraph workflow loaded successfully")
        return workflow
    except (ImportError, AttributeError) as exc:
        logger.warning(
            "LangGraph workflow not available — API running in stub mode",
            reason=str(exc),
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("unexpected error loading workflow", error=str(exc))
        return None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager.

    Initialises shared application state before the server starts accepting
    requests and releases resources (if any) on shutdown.

    Shared state attributes
    -----------------------
    - ``app.state.workflow``     — Compiled LangGraph app or None.
    - ``app.state.semaphore``    — asyncio.Semaphore capping concurrent workflows.
    - ``app.state.result_cache`` — Dict mapping thread_id → cached StreamMessages.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control to FastAPI while the server is running.
    """
    # Ensure the reports directory exists before any requests arrive.
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    app.state.workflow = _load_workflow()
    app.state.semaphore = asyncio.Semaphore(_MAX_CONCURRENT_WORKFLOWS)
    app.state.result_cache = {}

    logger.info(
        "DYOR API started",
        workflow_ready=app.state.workflow is not None,
        max_concurrent_workflows=_MAX_CONCURRENT_WORKFLOWS,
    )

    yield

    logger.info("DYOR API shutting down")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


app = FastAPI(
    title="DYOR Crypto Research API",
    description=(
        "Multi-agent cryptocurrency research assistant powered by LangGraph. "
        "Provides WebSocket streaming, SSE streaming, and REST endpoints for "
        "triggering analysis workflows and managing saved reports."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the Streamlit frontend served on localhost:8501.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers.
app.include_router(chat_router)
app.include_router(analyze_router)
app.include_router(reports_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    """Return the liveness status of the API.

    Returns:
        Dict with ``status`` (always ``"ok"``) and ``workflow_ready`` indicating
        whether the LangGraph workflow was loaded successfully.
    """
    return {
        "status": "ok",
        "workflow_ready": bool(app.state.workflow),
    }
