from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _build_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        db_path = url.split("sqlite:///", 1)[-1]
        if db_path and not db_path.startswith(":memory:"):
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False}, future=True)
    return create_engine(url, future=True)


def configure(url: str | None = None) -> Engine:
    global _engine, _SessionLocal
    settings = get_settings()
    final_url = url or settings.database_url
    _engine = _build_engine(final_url)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        configure()
    assert _engine is not None
    return _engine


def init_db() -> None:
    from ..models import db as _models  # noqa: F401  ensure models import

    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a SQLAlchemy session."""
    get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
