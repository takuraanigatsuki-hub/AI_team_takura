"""Сборка REST API router и lifecycle hooks."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from api.config import get_settings
from api.database import create_tables, reset_engine
from api.routers import auth, items

logger = logging.getLogger(__name__)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(items.router)


async def init_api() -> None:
    settings = get_settings()
    if not settings["api_enabled"]:
        logger.info("REST API v1 disabled (API_V1_ENABLED=false)")
        return
    try:
        await create_tables()
        logger.info("REST API v1: PostgreSQL tables ready")
    except Exception as exc:
        logger.warning("REST API v1: database init skipped (%s)", exc)


async def shutdown_api() -> None:
    from api.database import get_engine

    try:
        engine = get_engine()
        await engine.dispose()
    except Exception:
        pass
    reset_engine()
