"""Modern Portfolio Theory: Markowitz mean-variance + Maximum Sharpe portfolio.

Решаем стандартную QP через scipy.optimize.minimize / SLSQP с ограничениями
sum(w)=1, w_i ∈ [w_min, w_max]. Это та же математика, что лежит в
Aladdin-овых оптимизаторах (минус специализированные конусные solvers).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class OptimizerResult:
    method: str
    weights: dict[str, float]
    expected_return: float  # годовой μ
    volatility: float  # годовой σ
    sharpe: float | None
    converged: bool
    message: str = ""

    def as_dict(self) -> dict:
        return {
            "method": self.method,
            "weights": self.weights,
            "expected_return": self.expected_return,
            "volatility": self.volatility,
            "sharpe": self.sharpe,
            "converged": self.converged,
            "message": self.message,
        }


def _prep(
    returns: pd.DataFrame, periods_per_year: int
) -> tuple[list[str], np.ndarray, np.ndarray]:
    symbols = list(returns.columns)
    cov = returns.cov().values * periods_per_year
    mu = returns.mean().values * periods_per_year
    return symbols, mu, cov


def _make_bounds(n: int, w_min: float, w_max: float):
    return [(w_min, w_max)] * n


def _equality_sum_to_one():
    return {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}


def _portfolio_stats(
    weights: np.ndarray, mu: np.ndarray, cov: np.ndarray, risk_free: float
) -> tuple[float, float, float | None]:
    expected = float(weights @ mu)
    variance = float(weights @ cov @ weights)
    vol = float(np.sqrt(variance))
    sharpe = ((expected - risk_free) / vol) if vol > 1e-12 else None
    return expected, vol, sharpe


def max_sharpe(
    returns: pd.DataFrame,
    *,
    periods_per_year: int = 365,
    risk_free: float = 0.0,
    w_min: float = 0.0,
    w_max: float = 1.0,
) -> OptimizerResult:
    """Найти портфель с максимальным аннуализированным Sharpe."""
    if returns.empty or returns.shape[1] == 0:
        return OptimizerResult("max_sharpe", {}, 0.0, 0.0, None, False, "empty returns")

    symbols, mu, cov = _prep(returns, periods_per_year)
    n = len(symbols)
    x0 = np.full(n, 1.0 / n)

    def neg_sharpe(w: np.ndarray) -> float:
        expected = float(w @ mu)
        variance = float(w @ cov @ w)
        if variance <= 1e-18:
            return 1e6
        return -(expected - risk_free) / np.sqrt(variance)

    res = minimize(
        neg_sharpe, x0, method="SLSQP",
        bounds=_make_bounds(n, w_min, w_max),
        constraints=[_equality_sum_to_one()],
        options={"maxiter": 300, "ftol": 1e-9},
    )
    w = np.clip(res.x, w_min, w_max)
    w = w / w.sum() if w.sum() > 0 else x0
    expected, vol, sharpe = _portfolio_stats(w, mu, cov, risk_free)
    return OptimizerResult(
        method="max_sharpe",
        weights={s: round(float(w[i]), 6) for i, s in enumerate(symbols)},
        expected_return=round(expected, 6),
        volatility=round(vol, 6),
        sharpe=round(sharpe, 4) if sharpe is not None else None,
        converged=bool(res.success),
        message=str(res.message),
    )


def min_variance(
    returns: pd.DataFrame,
    *,
    periods_per_year: int = 365,
    risk_free: float = 0.0,
    w_min: float = 0.0,
    w_max: float = 1.0,
) -> OptimizerResult:
    """Глобальный минимум дисперсии (Markowitz)."""
    if returns.empty or returns.shape[1] == 0:
        return OptimizerResult("min_variance", {}, 0.0, 0.0, None, False, "empty returns")

    symbols, mu, cov = _prep(returns, periods_per_year)
    n = len(symbols)
    x0 = np.full(n, 1.0 / n)

    def variance(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    res = minimize(
        variance, x0, method="SLSQP",
        bounds=_make_bounds(n, w_min, w_max),
        constraints=[_equality_sum_to_one()],
        options={"maxiter": 300, "ftol": 1e-9},
    )
    w = np.clip(res.x, w_min, w_max)
    w = w / w.sum() if w.sum() > 0 else x0
    expected, vol, sharpe = _portfolio_stats(w, mu, cov, risk_free)
    return OptimizerResult(
        method="min_variance",
        weights={s: round(float(w[i]), 6) for i, s in enumerate(symbols)},
        expected_return=round(expected, 6),
        volatility=round(vol, 6),
        sharpe=round(sharpe, 4) if sharpe is not None else None,
        converged=bool(res.success),
        message=str(res.message),
    )
