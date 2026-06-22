from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from ..models.db import DecisionLog, EquityPoint, Order, Position
from ..models.schemas import (
    BotStatus,
    DecisionOut,
    EquityPointOut,
    OrderOut,
    PositionOut,
)
from .deps import AuthDep, EngineDep, SessionDep


router = APIRouter(prefix="/api/bot", tags=["bot"], dependencies=[])


@router.get("/status", response_model=BotStatus)
async def status(engine: EngineDep, _auth: AuthDep) -> BotStatus:
    return engine.status()


@router.post("/start", response_model=BotStatus)
async def start(engine: EngineDep, _auth: AuthDep) -> BotStatus:
    await engine.start()
    return engine.status()


@router.post("/stop", response_model=BotStatus)
async def stop(engine: EngineDep, _auth: AuthDep) -> BotStatus:
    await engine.stop()
    return engine.status()


@router.post("/pause", response_model=BotStatus)
async def pause(engine: EngineDep, _auth: AuthDep) -> BotStatus:
    engine.pause(True)
    return engine.status()


@router.post("/resume", response_model=BotStatus)
async def resume(engine: EngineDep, _auth: AuthDep) -> BotStatus:
    engine.pause(False)
    return engine.status()


@router.post("/kill", response_model=BotStatus)
async def kill(engine: EngineDep, _auth: AuthDep) -> BotStatus:
    engine.kill()
    return engine.status()


@router.post("/unkill", response_model=BotStatus)
async def unkill(engine: EngineDep, _auth: AuthDep) -> BotStatus:
    engine.reset_kill()
    return engine.status()


@router.post("/tick", response_model=BotStatus)
async def manual_tick(engine: EngineDep, _auth: AuthDep) -> BotStatus:
    """Принудительный одиночный шаг — полезно для дебага."""
    await engine.tick()
    return engine.status()


@router.get("/positions", response_model=list[PositionOut])
async def positions(session: SessionDep, engine: EngineDep, _auth: AuthDep):
    rows = session.execute(
        select(Position).where(Position.quantity > 0).order_by(Position.symbol)
    ).scalars().all()
    out: list[PositionOut] = []
    for row in rows:
        try:
            price = await engine.exchange.fetch_ticker(row.symbol)
        except Exception:
            price = None
        item = PositionOut.model_validate(row)
        item.current_price = price
        if price is not None:
            item.market_value = price * row.quantity
            item.unrealized_pnl = (price - row.avg_entry_price) * row.quantity
            if row.avg_entry_price > 0:
                item.unrealized_pnl_pct = (
                    (price - row.avg_entry_price) / row.avg_entry_price * 100
                )
        out.append(item)
    return out


@router.get("/orders", response_model=list[OrderOut])
def orders(session: SessionDep, _auth: AuthDep, limit: int = 100):
    limit = max(1, min(limit, 500))
    rows = session.execute(
        select(Order).order_by(Order.created_at.desc()).limit(limit)
    ).scalars().all()
    return [OrderOut.model_validate(r) for r in rows]


@router.get("/decisions", response_model=list[DecisionOut])
def decisions(session: SessionDep, _auth: AuthDep, limit: int = 100):
    limit = max(1, min(limit, 500))
    rows = session.execute(
        select(DecisionLog).order_by(DecisionLog.ts.desc()).limit(limit)
    ).scalars().all()
    return [DecisionOut.model_validate(r) for r in rows]


@router.get("/equity", response_model=list[EquityPointOut])
def equity(session: SessionDep, _auth: AuthDep, limit: int = 500):
    limit = max(1, min(limit, 5000))
    rows = session.execute(
        select(EquityPoint).order_by(EquityPoint.ts.desc()).limit(limit)
    ).scalars().all()
    return [EquityPointOut.model_validate(r) for r in reversed(rows)]
