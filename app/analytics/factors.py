"""Multi-factor decomposition: разложение доходности каждого актива на
систематические факторы. Кросс-секционные факторы:

- BTC β     — экспозиция на рыночный портфель крипты
- ETH β     — экспозиция на смарт-контрактный лидер (после очистки от BTC)
- MOM       — момент: средний return за последние ~30% окна
- VOL       — волатильность за окно (rolling std)
- SIZE      — приоритетная capitalization, прокси через средний объём * цену
              (нужны volume и цена — берём из OHLCV; если volume отсутствует, фактор пропускается)

Это упрощённый аналог Barra-моделей, которые BlackRock использует в Aladdin.
В реальной системе факторов > 50, плюс альтернативные данные (on-chain,
satellite, transactions). Здесь — образовательная база.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class FactorExposure:
    symbol: str
    btc_beta: float | None
    eth_beta: float | None
    momentum: float
    volatility: float
    size_proxy: float | None
    alpha: float  # перехват из регрессии (idiosyncratic return)
    r_squared: float

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "btc_beta": self.btc_beta,
            "eth_beta": self.eth_beta,
            "momentum": self.momentum,
            "volatility": self.volatility,
            "size_proxy": self.size_proxy,
            "alpha": self.alpha,
            "r_squared": self.r_squared,
        }


@dataclass
class PortfolioFactorExposure:
    weights: dict[str, float]
    portfolio_btc_beta: float
    portfolio_eth_beta: float
    portfolio_momentum: float
    portfolio_volatility: float
    diversification_score: float  # 1 = идеально, 0 = одна позиция
    per_asset: list[FactorExposure] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "weights": self.weights,
            "portfolio_btc_beta": self.portfolio_btc_beta,
            "portfolio_eth_beta": self.portfolio_eth_beta,
            "portfolio_momentum": self.portfolio_momentum,
            "portfolio_volatility": self.portfolio_volatility,
            "diversification_score": self.diversification_score,
            "per_asset": [a.as_dict() for a in self.per_asset],
        }


def _ols_two_factor(y: np.ndarray, x1: np.ndarray, x2: np.ndarray | None) -> tuple[float, float | None, float, float]:
    """Простая OLS-регрессия y = α + β1·x1 (+ β2·x2) + ε.

    Возвращает (β1, β2|None, α, R²). Использует numpy.linalg.lstsq.
    """
    cols = [x1]
    if x2 is not None:
        cols.append(x2)
    cols.append(np.ones_like(y))
    X = np.column_stack(cols)
    try:
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return 0.0, 0.0 if x2 is not None else None, 0.0, 0.0

    if x2 is not None:
        beta1, beta2, alpha = float(coef[0]), float(coef[1]), float(coef[2])
    else:
        beta1, alpha = float(coef[0]), float(coef[1])
        beta2 = None

    y_hat = X @ coef
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-18 else 0.0
    return beta1, beta2, alpha, max(0.0, min(1.0, r2))


def compute_factor_exposures(
    returns: pd.DataFrame,
    volumes: dict[str, pd.Series] | None = None,
    *,
    benchmark_btc: str = "BTC/USDT",
    benchmark_eth: str = "ETH/USDT",
    momentum_window: int = 30,
) -> list[FactorExposure]:
    """Посчитать факторные экспозиции для каждой колонки `returns`."""
    if returns.empty:
        return []
    has_btc = benchmark_btc in returns.columns
    has_eth = benchmark_eth in returns.columns
    out: list[FactorExposure] = []
    for sym in returns.columns:
        y = returns[sym].values.astype(float)
        if y.size < 10:
            continue

        if has_btc and sym != benchmark_btc:
            x_btc = returns[benchmark_btc].values.astype(float)
        else:
            x_btc = None

        if has_eth and sym not in (benchmark_btc, benchmark_eth) and x_btc is not None:
            x_eth = returns[benchmark_eth].values.astype(float)
        else:
            x_eth = None

        if x_btc is None:
            btc_beta = 1.0 if sym == benchmark_btc else None
            eth_beta = 1.0 if sym == benchmark_eth else None
            alpha = float(y.mean())
            r2 = 0.0
        else:
            btc_beta, eth_beta, alpha, r2 = _ols_two_factor(y, x_btc, x_eth)

        # MOM и VOL — простые признаки
        last = max(5, int(len(y) * 0.3))
        momentum = float(np.exp(np.sum(y[-last:])) - 1.0)
        volatility = float(np.std(y, ddof=1)) if y.size > 1 else 0.0

        size_proxy: float | None = None
        if volumes and sym in volumes:
            vol_series = volumes[sym]
            if not vol_series.empty:
                size_proxy = float(vol_series.tail(50).mean())

        out.append(FactorExposure(
            symbol=sym,
            btc_beta=round(btc_beta, 4) if btc_beta is not None else None,
            eth_beta=round(eth_beta, 4) if eth_beta is not None else None,
            momentum=round(momentum, 6),
            volatility=round(volatility, 6),
            size_proxy=round(size_proxy, 4) if size_proxy is not None else None,
            alpha=round(alpha, 8),
            r_squared=round(r2, 4),
        ))
    return out


def compute_portfolio_factors(
    returns: pd.DataFrame,
    weights: dict[str, float],
    volumes: dict[str, pd.Series] | None = None,
) -> PortfolioFactorExposure:
    """Свернуть факторы к уровню портфеля по весам."""
    per_asset = compute_factor_exposures(returns, volumes=volumes)
    if not per_asset:
        return PortfolioFactorExposure(
            weights={}, portfolio_btc_beta=0.0, portfolio_eth_beta=0.0,
            portfolio_momentum=0.0, portfolio_volatility=0.0,
            diversification_score=0.0, per_asset=[],
        )

    w = {a.symbol: float(weights.get(a.symbol, 0.0)) for a in per_asset}
    total = sum(w.values())
    if total > 0:
        w = {k: v / total for k, v in w.items()}
    else:
        n = len(per_asset)
        w = {a.symbol: 1.0 / n for a in per_asset}

    def _wmean(attr: str) -> float:
        s = 0.0
        for a in per_asset:
            v = getattr(a, attr)
            if v is None:
                continue
            s += w[a.symbol] * float(v)
        return round(s, 6)

    # Herfindahl-Hirschman index → 1 - HHI ∈ [0, 1-1/N]; нормируем к [0,1]
    hhi = sum(v * v for v in w.values())
    n = len(w)
    max_diversity = 1.0 - 1.0 / n if n > 1 else 0.0
    diversification = ((1.0 - hhi) / max_diversity) if max_diversity > 0 else 0.0

    return PortfolioFactorExposure(
        weights={k: round(v, 6) for k, v in w.items()},
        portfolio_btc_beta=_wmean("btc_beta"),
        portfolio_eth_beta=_wmean("eth_beta"),
        portfolio_momentum=_wmean("momentum"),
        portfolio_volatility=_wmean("volatility"),
        diversification_score=round(diversification, 4),
        per_asset=per_asset,
    )
