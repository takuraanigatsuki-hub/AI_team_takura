"""Risk Parity portfolio — каждый актив вносит одинаковый риск.

Стратегия Bridgewater All-Weather и многих risk-parity фондов.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .mpt import OptimizerResult, _portfolio_stats, _prep


def risk_parity(
    returns: pd.DataFrame,
    *,
    periods_per_year: int = 365,
    risk_free: float = 0.0,
    target_contributions: list[float] | None = None,
) -> OptimizerResult:
    """Найти веса, такие что risk_contribution_i = target_i для всех i.

    По умолчанию target = равномерное (1/N) — это и есть «risk parity».
    """
    if returns.empty or returns.shape[1] == 0:
        return OptimizerResult("risk_parity", {}, 0.0, 0.0, None, False, "empty returns")

    symbols, mu, cov = _prep(returns, periods_per_year)
    n = len(symbols)

    if target_contributions is None:
        target = np.full(n, 1.0 / n)
    else:
        target = np.array(target_contributions, dtype=float)
        if target.sum() <= 0:
            target = np.full(n, 1.0 / n)
        else:
            target = target / target.sum()

    def objective(w: np.ndarray) -> float:
        w = np.maximum(w, 1e-9)
        w = w / w.sum()
        sigma_p = float(np.sqrt(w @ cov @ w))
        if sigma_p <= 1e-12:
            return 1e6
        rc = w * (cov @ w) / sigma_p
        rc_norm = rc / sigma_p  # доли вклада, сумма = 1
        return float(np.sum((rc_norm - target) ** 2))

    x0 = np.full(n, 1.0 / n)
    res = minimize(
        objective, x0, method="SLSQP",
        bounds=[(1e-6, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}],
        options={"maxiter": 500, "ftol": 1e-10},
    )
    w = np.clip(res.x, 1e-6, 1.0)
    w = w / w.sum()
    expected, vol, sharpe = _portfolio_stats(w, mu, cov, risk_free)
    return OptimizerResult(
        method="risk_parity",
        weights={s: round(float(w[i]), 6) for i, s in enumerate(symbols)},
        expected_return=round(expected, 6),
        volatility=round(vol, 6),
        sharpe=round(sharpe, 4) if sharpe is not None else None,
        converged=bool(res.success),
        message=str(res.message),
    )
