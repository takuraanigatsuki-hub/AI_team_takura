"""Настройки REST API из переменных окружения."""

from __future__ import annotations

import os
from functools import lru_cache

DEFAULT_DATABASE_URL = "postgresql+asyncpg://aiteam:aiteam@localhost:5432/aiteam"
DEFAULT_JWT_SECRET = "dev-change-me-api-jwt-secret"


@lru_cache
def get_settings() -> dict:
    return {
        "database_url": os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
        or DEFAULT_DATABASE_URL,
        "jwt_secret": os.environ.get("API_JWT_SECRET", DEFAULT_JWT_SECRET).strip()
        or DEFAULT_JWT_SECRET,
        "jwt_algorithm": "HS256",
        "jwt_expire_minutes": int(os.environ.get("API_JWT_EXPIRE_MINUTES", "60")),
        "api_enabled": os.environ.get("API_V1_ENABLED", "true").lower() not in (
            "0",
            "false",
            "no",
        ),
    }
