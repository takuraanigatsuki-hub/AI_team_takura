from __future__ import annotations

import sys

from loguru import logger

from .config import get_settings


_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        backtrace=False,
        diagnose=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ),
    )
    _configured = True


__all__ = ["logger", "setup_logging"]
