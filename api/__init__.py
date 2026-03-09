"""FastAPI backend for the DYOR crypto research assistant.

Re-exports the ``app`` instance so it can be referenced as ``api:app`` or
``api.app`` by deployment tooling.
"""

from api.main import app

__all__ = ["app"]
