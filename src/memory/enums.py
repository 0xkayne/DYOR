"""Enum definitions for memory module configuration."""

from __future__ import annotations

from enum import Enum


class CheckpointerBackend(str, Enum):
    """Supported checkpoint persistence backends."""

    MEMORY = "memory"
    REDIS = "redis"
    POSTGRES = "postgres"
    REDIS_THEN_POSTGRES = "redis_then_postgres"
