from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from ..agent.loop import AutonomousAgent, get_agent
from ..agent.reflection import run_reflection
from ..core.config import get_settings
from ..core.database import get_session
from ..models.db import AgentJournal, AgentMemo
from ..models.schemas import AgentJournalOut, AgentMemoOut, AgentStatus, NewsItemOut
from ..news.feeds import get_news_service
from .deps import AuthDep, SessionDep


router = APIRouter(prefix="/api/agent", tags=["agent"])


def _agent() -> AutonomousAgent:
    return get_agent()


def _status(agent: AutonomousAgent) -> AgentStatus:
    settings = get_settings()
    return AgentStatus(
        enabled=agent.enabled,
        running=agent.running,
        interval_seconds=settings.agent_interval_seconds,
        model=settings.llm_model,
        provider=settings.llm_provider,
        last_run_at=agent.stats.last_run_at,
        last_error=agent.stats.last_error,
        cycles=agent.stats.cycles,
        has_api_key=bool(settings.llm_api_key),
    )


@router.get("/status", response_model=AgentStatus)
def status(_auth: AuthDep) -> AgentStatus:
    return _status(_agent())


@router.post("/start", response_model=AgentStatus)
async def start(_auth: AuthDep) -> AgentStatus:
    agent = _agent()
    try:
        await agent.start()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _status(agent)


@router.post("/stop", response_model=AgentStatus)
async def stop(_auth: AuthDep) -> AgentStatus:
    agent = _agent()
    await agent.stop()
    return _status(agent)


@router.post("/tick", response_model=dict)
async def manual_tick(_auth: AuthDep):
    agent = _agent()
    if not agent.enabled:
        raise HTTPException(status_code=400, detail="LLM_API_KEY не задан")
    result = await agent.tick()
    return result


@router.get("/journal", response_model=list[AgentJournalOut])
def journal(session: SessionDep, _auth: AuthDep, limit: int = Query(30, ge=1, le=200)):
    rows = session.execute(
        select(AgentJournal).order_by(AgentJournal.ts.desc()).limit(limit)
    ).scalars().all()
    return [AgentJournalOut.model_validate(r) for r in rows]


@router.get("/news", response_model=list[NewsItemOut])
async def news(_auth: AuthDep, limit: int = Query(20, ge=1, le=100),
               q: str | None = Query(None)):
    svc = get_news_service()
    items = await (svc.search(q, limit=limit) if q else svc.fetch(limit=limit))
    return [NewsItemOut(**i.as_dict()) for i in items]


@router.get("/memos", response_model=list[AgentMemoOut])
def memos(session: SessionDep, _auth: AuthDep, limit: int = Query(20, ge=1, le=100)):
    rows = session.execute(
        select(AgentMemo).order_by(AgentMemo.ts.desc()).limit(limit)
    ).scalars().all()
    return [AgentMemoOut.model_validate(r) for r in rows]


@router.post("/reflect", response_model=dict)
async def reflect(_auth: AuthDep):
    """Запустить рефлексию вручную (не дожидаясь таймера)."""
    settings = get_settings()
    if not settings.llm_api_key:
        raise HTTPException(status_code=400, detail="LLM_API_KEY не задан")
    res = await run_reflection(settings)
    return {
        "summary": res.summary,
        "rules": res.rules,
        "journal_count": res.journal_count,
        "orders_count": res.orders_count,
        "realized_pnl": res.realized_pnl,
        "error": res.error,
    }
