"""Portfolio risk analytics — VaR, CVaR, correlation, beta, risk contribution.

Идея ровно как в Aladdin: считать риск ПЕРВЫМ, доходность вторым.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def compute_returns(price_series: dict[str, pd.Series]) -> pd.DataFrame:
    """Привести несколько ценовых рядов к выровненному dataframe лог-доходностей.

    На вход — словарь {symbol: Series(close, index=timestamp_ms)}.
    На выход — DataFrame с колонками-символами и одинаковым индексом, лог-доходности.
    """
    if not price_series:
        return pd.DataFrame()
    df = pd.DataFrame({sym: s for sym, s in price_series.items()})
    df = df.dropna(how="all").sort_index().ffill().bfill()
    returns = np.log(df / df.shift(1)).dropna(how="all")
    return returns.dropna(axis=1, how="all").fillna(0.0)


@dataclass
class RiskContribution:
    symbol: str
    weight: float
    marginal_contribution: float  # ∂σ_p / ∂w_i
    component_contribution: float  # w_i · ∂σ_p/∂w_i
    pct_of_total_risk: float


@dataclass
class PortfolioRisk:
    timeframe_returns: int  # число точек дневных доходностей в годе (для крипты — 365)
    weights: dict[str, float]
    expected_return: float  # годовой μ
    volatility: float  # годовой σ
    sharpe: float | None
    var_95: float  # одно-периодный VaR в долях капитала (отрицательное число)
    cvar_95: float  # Expected Shortfall
    max_loss_observed: float
    correlation: dict[str, dict[str, float]]
    betas: dict[str, float]  # бета относительно benchmark (BTC по умолчанию)
    contributions: list[RiskContribution] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "weights": self.weights,
            "expected_return": self.expected_return,
            "volatility": self.volatility,
            "sharpe": self.sharpe,
            "var_95": self.var_95,
            "cvar_95": self.cvar_95,
            "max_loss_observed": self.max_loss_observed,
            "correlation": self.correlation,
            "betas": self.betas,
            "contributions": [
                {
                    "symbol": c.symbol,
                    "weight": c.weight,
                    "marginal_contribution": c.marginal_contribution,
                    "component_contribution": c.component_contribution,
                    "pct_of_total_risk": c.pct_of_total_risk,
                }
                for c in self.contributions
            ],
            "timeframe_returns_per_year": self.timeframe_returns,
        }


def compute_portfolio_risk(
    returns: pd.DataFrame,
    weights: dict[str, float] | None = None,
    *,
    periods_per_year: int = 365,
    var_alpha: float = 0.05,
    benchmark: str | None = None,
    risk_free: float = 0.0,
) -> PortfolioRisk:
    """Главный расчётчик: даёт annualized μ, σ, Sharpe, VaR/CVaR, β и risk-contribution."""
    if returns.empty:
        return _empty_risk(weights or {})
    symbols = list(returns.columns)
    n = len(symbols)
    if weights is None:
        weights = {s: 1.0 / n for s in symbols}
    # выровняем веса под колонки returns
    w = np.array([float(weights.get(s, 0.0)) for s in symbols])
    if w.sum() > 0:
        w = w / w.sum()
    else:
        w = np.full(n, 1.0 / n)

    cov = returns.cov().values  # ковариация по периоду свечи
    mu_per_period = returns.mean().values
    portfolio_returns = (returns.values @ w)

    expected_return = float(mu_per_period @ w * periods_per_year)
    variance = float(w @ cov @ w)
    volatility = float(np.sqrt(variance) * np.sqrt(periods_per_year))
    sharpe = ((expected_return - risk_free) / volatility) if volatility > 1e-12 else None

    # Historical one-period VaR / CVaR
    sorted_ret = np.sort(portfolio_returns)
    var_idx = max(0, int(np.floor(var_alpha * len(sorted_ret))))
    var_value = float(sorted_ret[var_idx])
    tail = sorted_ret[: var_idx + 1]
    cvar_value = float(tail.mean()) if tail.size else var_value
    max_loss = float(sorted_ret[0]) if sorted_ret.size else 0.0

    # Correlation
    corr_df = returns.corr().round(4)
    correlation = {s: corr_df[s].to_dict() for s in symbols}

    # Beta to benchmark
    betas: dict[str, float] = {}
    bench = benchmark if benchmark and benchmark in returns.columns else _pick_benchmark(returns)
    if bench:
        bench_var = float(returns[bench].var())
        for s in symbols:
            if s == bench:
                betas[s] = 1.0
                continue
            cov_sb = float(returns[s].cov(returns[bench]))
            betas[s] = cov_sb / bench_var if bench_var > 1e-12 else 0.0

    # Risk contributions
    sigma_p = float(np.sqrt(variance))
    cov_w = cov @ w
    contributions: list[RiskContribution] = []
    for i, sym in enumerate(symbols):
        marg = cov_w[i] / sigma_p if sigma_p > 1e-12 else 0.0
        comp = w[i] * marg
        pct = (comp / sigma_p * 100) if sigma_p > 1e-12 else 0.0
        contributions.append(RiskContribution(
            symbol=sym,
            weight=round(float(w[i]), 6),
            marginal_contribution=round(float(marg), 8),
            component_contribution=round(float(comp), 8),
            pct_of_total_risk=round(float(pct), 4),
        ))

    return PortfolioRisk(
        timeframe_returns=periods_per_year,
        weights={s: round(float(w[i]), 6) for i, s in enumerate(symbols)},
        expected_return=round(expected_return, 6),
        volatility=round(volatility, 6),
        sharpe=(round(sharpe, 4) if sharpe is not None else None),
        var_95=round(var_value, 6),
        cvar_95=round(cvar_value, 6),
        max_loss_observed=round(max_loss, 6),
        correlation=correlation,
        betas={k: round(v, 4) for k, v in betas.items()},
        contributions=contributions,
    )


def compute_risk_contribution(returns: pd.DataFrame, weights: dict[str, float]) -> list[RiskContribution]:
    """Удобный сокращённый вызов — только risk contribution."""
    if returns.empty:
        return []
    symbols = list(returns.columns)
    w = np.array([float(weights.get(s, 0.0)) for s in symbols])
    if w.sum() <= 0:
        return []
    w = w / w.sum()
    cov = returns.cov().values
    sigma_p = float(np.sqrt(w @ cov @ w))
    if sigma_p <= 1e-12:
        return []
    cov_w = cov @ w
    out = []
    for i, sym in enumerate(symbols):
        marg = cov_w[i] / sigma_p
        comp = w[i] * marg
        out.append(RiskContribution(
            symbol=sym, weight=float(w[i]),
            marginal_contribution=float(marg),
            component_contribution=float(comp),
            pct_of_total_risk=float(comp / sigma_p * 100),
        ))
    return out


def _pick_benchmark(returns: pd.DataFrame) -> str | None:
    """Выбрать наиболее «системный» актив как benchmark — обычно BTC."""
    for guess in ("BTC/USDT", "BTC/USD", "BTC", "ETH/USDT"):
        if guess in returns.columns:
            return guess
    return returns.columns[0] if len(returns.columns) > 0 else None


def _empty_risk(weights: dict[str, float]) -> PortfolioRisk:
    return PortfolioRisk(
        timeframe_returns=0,
        weights=weights,
        expected_return=0.0,
        volatility=0.0,
        sharpe=None,
        var_95=0.0,
        cvar_95=0.0,
        max_loss_observed=0.0,
        correlation={},
        betas={},
        contributions=[],
    )
