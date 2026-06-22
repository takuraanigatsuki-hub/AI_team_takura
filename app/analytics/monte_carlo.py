"""Monte Carlo VaR — симуляции из multivariate normal под фактическую
ковариацию доходностей. Считаем VaR и CVaR более устойчиво в хвостах,
чем historical percentile."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MonteCarloResult:
    n_simulations: int
    horizon: int
    var_alpha: float
    var_value: float        # одно-периодный VaR в долях капитала
    cvar_value: float
    expected_return: float  # средняя симулированная доходность
    worst_case: float
    best_case: float

    def as_dict(self) -> dict:
        return self.__dict__


def monte_carlo_var(
    returns: pd.DataFrame,
    weights: dict[str, float],
    *,
    n_simulations: int = 10_000,
    horizon: int = 1,
    var_alpha: float = 0.05,
    seed: int | None = 42,
) -> MonteCarloResult:
    """Симулировать N путей портфельной доходности и оценить VaR/CVaR.

    Метод: оцениваем μ и Σ по предоставленным доходностям, генерируем
    n_simulations выборок из multivariate normal, суммируем по горизонту,
    взвешиваем весами портфеля → распределение портфельной доходности.
    """
    if returns.empty or not weights:
        return MonteCarloResult(0, horizon, var_alpha, 0.0, 0.0, 0.0, 0.0, 0.0)

    symbols = list(returns.columns)
    w = np.array([float(weights.get(s, 0.0)) for s in symbols])
    if w.sum() > 0:
        w = w / w.sum()
    else:
        w = np.full(len(symbols), 1.0 / len(symbols))

    mu = returns.mean().values
    cov = returns.cov().values

    rng = np.random.default_rng(seed)
    try:
        # многошаговая симуляция: сумма horizon независимых выборок
        sims = rng.multivariate_normal(mu, cov, size=(n_simulations, horizon))
    except np.linalg.LinAlgError:
        # ковариация вырождена — добавим небольшое регуляризационное смещение
        cov = cov + np.eye(len(symbols)) * 1e-10
        sims = rng.multivariate_normal(mu, cov, size=(n_simulations, horizon))

    # суммируем доходности по горизонту → доходность за весь период
    period_returns = sims.sum(axis=1) @ w
    sorted_ret = np.sort(period_returns)
    idx = max(0, int(np.floor(var_alpha * len(sorted_ret))))
    var_value = float(sorted_ret[idx])
    tail = sorted_ret[: idx + 1]
    cvar_value = float(tail.mean()) if tail.size else var_value

    return MonteCarloResult(
        n_simulations=n_simulations,
        horizon=horizon,
        var_alpha=var_alpha,
        var_value=round(var_value, 6),
        cvar_value=round(cvar_value, 6),
        expected_return=round(float(period_returns.mean()), 6),
        worst_case=round(float(period_returns.min()), 6),
        best_case=round(float(period_returns.max()), 6),
    )
