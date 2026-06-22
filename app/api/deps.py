from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..core.database import get_session
from ..engine.trader import TradeEngine, get_engine


SessionDep = Annotated[Session, Depends(get_session)]


def settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dep)]


def engine_dep() -> TradeEngine:
    return get_engine()


EngineDep = Annotated[TradeEngine, Depends(engine_dep)]


_basic = HTTPBasic(auto_error=False)


def auth_optional(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)] = None,
) -> None:
    """Basic auth, активна только если задан WEB_USER+WEB_PASSWORD."""
    settings = get_settings()
    if not settings.web_user and not settings.web_password:
        return None
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth required",
            headers={"WWW-Authenticate": "Basic"},
        )
    user_ok = secrets.compare_digest(credentials.username, settings.web_user)
    pwd_ok = secrets.compare_digest(credentials.password, settings.web_password)
    if not (user_ok and pwd_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return None


AuthDep = Annotated[None, Depends(auth_optional)]
