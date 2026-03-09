"""API route definitions.

Re-exports all routers so ``api.main`` can import them from a single location.
"""

from api.routes.analyze import analyze_router
from api.routes.chat import chat_router
from api.routes.reports import reports_router

__all__ = ["chat_router", "analyze_router", "reports_router"]
