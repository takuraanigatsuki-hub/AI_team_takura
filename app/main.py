from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .api.deps import auth_optional
from .api.routes_agent import router as agent_router
from .api.routes_analytics import router as analytics_router
from .api.routes_bot import router as bot_router
from .api.routes_market import router as market_router
from .api.routes_metrics import router as metrics_router
from .api.routes_strategy import router as strategy_router
from .agent.loop import get_agent
from .telegram.bot import get_telegram_bot
from .telegram.notifier import get_notifier
from .core.config import get_settings
from .core.database import init_db
from .core.logging import logger, setup_logging
from .engine.trader import get_engine


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    setup_logging()
    init_db()
    logger.info("Trade {} starting; mode={}", __version__, get_settings().mode)
    settings = get_settings()
    if settings.telegram_bot_token:
        try:
            await get_telegram_bot().start()
        except Exception as exc:
            logger.warning("telegram bot start failed: {}", exc)
    daily_task: asyncio.Task | None = None
    if settings.telegram_bot_token and settings.telegram_chat_id:
        daily_task = asyncio.create_task(
            _daily_summary_loop(settings), name="telegram-daily-summary"
        )
    if settings.agent_enabled and settings.llm_api_key:
        try:
            await get_agent().start()
        except Exception as exc:
            logger.warning("agent auto-start failed: {}", exc)
    yield
    if daily_task is not None:
        daily_task.cancel()
    try:
        await get_telegram_bot().stop()
    except Exception:
        pass
    try:
        await get_agent().stop()
    except Exception:
        pass
    engine = get_engine()
    try:
        await engine.stop()
    except Exception:
        pass


async def _daily_summary_loop(settings) -> None:
    """Раз в сутки в указанный час UTC шлёт сводку в Telegram."""
    import asyncio
    from datetime import datetime, timedelta, timezone

    while True:
        try:
            now = datetime.now(timezone.utc)
            target = now.replace(
                hour=settings.telegram_daily_summary_hour_utc,
                minute=0, second=0, microsecond=0,
            )
            if target <= now:
                target += timedelta(days=1)
            await asyncio.sleep((target - now).total_seconds())
            engine = get_engine()
            s = engine.status()
            await get_notifier().notify_daily_summary(
                equity=s.equity, daily_pnl=s.daily_pnl,
                daily_pnl_pct=s.daily_pnl_pct, mode=s.mode,
                open_positions=0,  # короткая сводка; точное число — командой /status
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("daily summary failed: {}", exc)
            await asyncio.sleep(300)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Автономный торговый бот с веб-дашбордом. Поддерживает paper и live режимы. "
            "Включает несколько стратегий, риск-менеджмент, бэктест и аудит-лог."
        ),
        lifespan=_lifespan,
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    app.include_router(bot_router)
    app.include_router(market_router)
    app.include_router(strategy_router)
    app.include_router(agent_router)
    app.include_router(metrics_router)
    app.include_router(analytics_router)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard(request: Request, _auth: None = Depends(auth_optional)):
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": settings.app_name,
                "version": __version__,
                "mode": settings.mode,
                "exchange": settings.exchange_id,
                "symbols": settings.symbols,
                "timeframe": settings.timeframe,
            },
        )

    @app.get("/health", include_in_schema=False)
    async def health():
        return {"status": "ok", "version": __version__, "mode": settings.mode}

    return app


app = create_app()
