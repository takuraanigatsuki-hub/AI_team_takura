"""Async SQLAlchemy engine и сессии."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from api.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    pass


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings["database_url"]
        connect_args: dict = {}
        pool_kwargs: dict = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            pool_kwargs["poolclass"] = StaticPool
        _engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            connect_args=connect_args,
            **pool_kwargs,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def reset_engine(database_url: str | None = None) -> None:
    """Сброс пула — для тестов и смены DATABASE_URL."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
    if database_url is not None:
        get_settings.cache_clear()
        import os

        os.environ["DATABASE_URL"] = database_url


async def create_tables() -> None:
    from api import models  # noqa: F401

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
