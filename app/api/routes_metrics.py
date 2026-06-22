from __future__ import annotations

from fastapi import APIRouter

from ..metrics.performance import (
    compute_portfolio_metrics,
    compute_strategy_attribution,
)
from .deps import AuthDep, SessionDep


router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/portfolio")
def portfolio(session: SessionDep, _auth: AuthDep):
    return compute_portfolio_metrics(session).as_dict()


@router.get("/strategies")
def strategies(session: SessionDep, _auth: AuthDep):
    return [item.as_dict() for item in compute_strategy_attribution(session)]
