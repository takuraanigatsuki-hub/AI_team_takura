from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from ..adaptive.bandit import (
    load_bandit_states,
    sample_weights,
    update_bandit_from_history,
)
from ..adaptive.genetic import run_genetic_cycle
from ..adaptive.proposer import run_proposer_cycle
from ..adaptive.regime import detect_regime
from ..adaptive.retirement import run_retirement_cycle
from ..adaptive.tuner import run_tuning_cycle
from ..adaptive.weights import (
    compute_adaptive_weights,
    compute_performance_snapshots,
)
from ..core.database import session_scope
from ..exchange.base import ExchangeError
from ..models.db import OnlineLexicon, StrategyConfig, StrategyPerformance
from ..sentiment.online import load_online_weights, run_online_learning_cycle
from .deps import AuthDep, EngineDep, SessionDep


router = APIRouter(prefix="/api/adaptive", tags=["adaptive"])


@router.get("/weights")
def weights(session: SessionDep, engine: EngineDep, _auth: AuthDep):
    s = engine.settings
    snapshots = compute_performance_snapshots(session, lookback=s.adaptive_lookback_decisions)
    w = compute_adaptive_weights(
        snapshots, w_min=s.adaptive_min_weight, w_max=s.adaptive_max_weight,
    )
    return {
        "weights": w,
        "snapshots": [s.as_dict() for s in snapshots],
        "lookback": s.adaptive_lookback_decisions,
        "current_engine_weights": engine.stats.adaptive_weights,
    }


@router.post("/weights/refresh")
def weights_refresh(engine: EngineDep, _auth: AuthDep):
    w = engine.refresh_adaptive_weights()
    return {"weights": w}


@router.get("/regime")
async def regime(engine: EngineDep, _auth: AuthDep,
                 symbol: str = Query(None),
                 timeframe: str = Query("1h"),
                 candles: int = Query(200, ge=80, le=1000)):
    sym = symbol or (engine.settings.symbols[0] if engine.settings.symbols else "BTC/USDT")
    try:
        rows = await engine.exchange.fetch_ohlcv(sym, timeframe=timeframe, limit=candles)
    except ExchangeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not rows:
        raise HTTPException(status_code=400, detail="no candles")
    import pandas as pd
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    res = detect_regime(df["close"], window=min(120, len(df) - 5))
    return {"symbol": sym, **res.as_dict()}


@router.get("/strategies")
def strategies(session: SessionDep, _auth: AuthDep,
               only_enabled: bool = Query(False)):
    q = select(StrategyConfig).order_by(StrategyConfig.backtest_score.desc())
    if only_enabled:
        q = q.where(StrategyConfig.enabled == 1)
    rows = session.execute(q).scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "base": r.base,
            "params": _safe(r.params), "enabled": bool(r.enabled),
            "created_by": r.created_by, "backtest_score": r.backtest_score,
            "note": r.note, "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        } for r in rows
    ]


@router.post("/strategies/{config_id}/toggle")
def toggle_strategy(config_id: int, _auth: AuthDep, engine: EngineDep):
    with session_scope() as session:
        row = session.get(StrategyConfig, config_id)
        if row is None:
            raise HTTPException(status_code=404, detail="not found")
        row.enabled = 0 if row.enabled else 1
        new_state = bool(row.enabled)
    engine.reload_strategies_from_db()
    return {"id": config_id, "enabled": new_state}


@router.post("/strategies/reload")
def reload_strategies(engine: EngineDep, _auth: AuthDep):
    n = engine.reload_strategies_from_db()
    return {"loaded": n, "names": [s.name for s in engine.strategies]}


@router.post("/tuner/run")
async def run_tuner(_auth: AuthDep, engine: EngineDep,
                    symbol: str = Query(None),
                    samples: int = Query(20, ge=5, le=100)):
    sym = symbol or (engine.settings.symbols[0] if engine.settings.symbols else "BTC/USDT")
    best = await run_tuning_cycle(
        engine.settings, symbol=sym, samples_per_strategy=samples
    )
    engine.reload_strategies_from_db()
    return [{"base": c.base, "params": c.params,
             "score": c.score, "folds": c.folds} for c in best]


@router.post("/proposer/run")
async def run_proposer(_auth: AuthDep, engine: EngineDep,
                       symbol: str = Query(None)):
    sym = symbol or (engine.settings.symbols[0] if engine.settings.symbols else "BTC/USDT")
    results = await run_proposer_cycle(engine.settings, symbol=sym)
    engine.reload_strategies_from_db()
    return [
        {
            "base": p.base, "params": p.params, "rationale": p.rationale,
            "backtest_score": p.backtest_score, "accepted": p.accepted,
            "reject_reason": p.reject_reason,
        } for p in results
    ]


@router.get("/bandit")
def bandit_state(session: SessionDep, engine: EngineDep, _auth: AuthDep):
    names = [s.name for s in engine.strategies]
    states = load_bandit_states(session, names=names)
    sampled = sample_weights(states)
    return {
        "enabled": engine.settings.bandit_enabled,
        "blend": engine.settings.bandit_blend,
        "states": [st.as_dict() for st in states.values()],
        "sampled_weights": sampled,
    }


@router.post("/bandit/update")
def bandit_update(_auth: AuthDep, lookback: int = Query(500, ge=10, le=5000)):
    with session_scope() as session:
        updated = update_bandit_from_history(session, lookback=lookback)
    return {"updated": len(updated),
            "states": [u.as_dict() for u in updated.values()]}


@router.post("/genetic/run")
async def genetic_run(_auth: AuthDep, engine: EngineDep,
                      symbol: str = Query(None)):
    sym = symbol or (engine.settings.symbols[0] if engine.settings.symbols else "BTC/USDT")
    survivors = await run_genetic_cycle(engine.settings, symbol=sym)
    engine.reload_strategies_from_db()
    return [
        {"base": c.base, "params": c.params, "score": c.score,
         "generation": c.generation, "parents": list(c.parents) if c.parents else None}
        for c in survivors
    ]


@router.post("/retirement/run")
def retirement_run(_auth: AuthDep, engine: EngineDep):
    res = run_retirement_cycle(engine.settings)
    engine.reload_strategies_from_db()
    return {
        "retired": res.retired, "kept": res.kept,
        "skipped_protected": res.skipped_protected,
    }


@router.post("/sentiment/learn")
async def sentiment_learn(_auth: AuthDep, engine: EngineDep):
    res = await run_online_learning_cycle(engine.settings)
    return res


@router.get("/sentiment/lexicon")
def sentiment_lexicon(session: SessionDep, _auth: AuthDep,
                      min_samples: int = Query(2, ge=1),
                      limit: int = Query(50, ge=1, le=500)):
    rows = session.execute(
        select(OnlineLexicon).where(OnlineLexicon.samples >= min_samples)
        .order_by(OnlineLexicon.samples.desc()).limit(limit)
    ).scalars().all()
    return [
        {"word": r.word, "weight": round(r.weight, 4),
         "samples": r.samples,
         "last_seen_at": r.last_seen_at.isoformat()}
        for r in rows
    ]


@router.get("/performance_history")
def performance_history(session: SessionDep, _auth: AuthDep,
                        limit: int = Query(200, ge=1, le=2000)):
    rows = session.execute(
        select(StrategyPerformance).order_by(StrategyPerformance.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        {
            "strategy_name": r.strategy_name,
            "window_start": r.window_start.isoformat(),
            "window_end": r.window_end.isoformat(),
            "votes": r.votes, "decisive_votes": r.decisive_votes,
            "accuracy": r.accuracy, "attributable_pnl": r.attributable_pnl,
            "avg_confidence": r.avg_confidence, "weight": r.weight,
        } for r in rows
    ]


def _safe(s: str):
    try:
        return json.loads(s) if s else {}
    except json.JSONDecodeError:
        return {}
