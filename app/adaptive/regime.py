"""Регим-детектор: trending_up / trending_down / ranging / volatile.

Простой и интерпретируемый эвристический классификатор. Для каждого окна:
- считаем направленность тренда через линейную регрессию log-цен;
- считаем волатильность как std дневных доходностей;
- сравниваем с рассчитанными порогами на длинной истории.

Регим влияет на вес стратегий в агрегаторе:
- trending → выше веса трендовых стратегий (ma_crossover, bollinger_breakout BUY)
- ranging  → выше веса mean-reversion (rsi_reversion)
- volatile → агрегатор требует большего consensus, размер позиций режется
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


RegimeT = Literal["trending_up", "trending_down", "ranging", "volatile"]


@dataclass
class MarketRegime:
    label: RegimeT
    trend_slope: float          # наклон log-цены (β регрессии)
    realized_volatility: float  # стандартное отклонение доходностей
    vol_z_score: float          # z-score текущей vol относительно истории
    confidence: float           # 0..1

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "trend_slope": round(self.trend_slope, 8),
            "realized_volatility": round(self.realized_volatility, 6),
            "vol_z_score": round(self.vol_z_score, 4),
            "confidence": round(self.confidence, 4),
        }


def detect_regime(
    prices: pd.Series | pd.DataFrame,
    *,
    window: int = 60,
) -> MarketRegime:
    """Определить регим по последним N точкам.

    Принимает либо одну ценовую серию, либо DataFrame (берётся первая колонка
    или столбец 'close'). Окно `window` — последние N точек для анализа.
    """
    if isinstance(prices, pd.DataFrame):
        if "close" in prices.columns:
            series = prices["close"]
        else:
            series = prices.iloc[:, 0]
    else:
        series = prices

    if series is None or len(series) < window + 10:
        return MarketRegime("ranging", 0.0, 0.0, 0.0, 0.1)

    arr = np.asarray(series.tail(window).astype(float).values)
    log_p = np.log(arr)
    x = np.arange(len(log_p), dtype=float)

    # тренд: наклон линейной регрессии log-цены
    slope, _intercept = np.polyfit(x, log_p, 1)
    # средняя величина движения за свечу для нормировки
    returns = np.diff(log_p)
    realized_vol = float(np.std(returns, ddof=1)) if returns.size > 1 else 0.0

    # vol-z: где сейчас vol относительно ИСТОРИЧЕСКОГО baseline,
    # ИСКЛЮЧАЯ текущее окно (иначе всплеск растворяется в собственном baseline)
    full_returns = np.diff(np.log(series.astype(float).values))
    if full_returns.size > window + 5:
        baseline_window = full_returns[: -window] if full_returns.size > window else full_returns
        baseline_window = baseline_window[-min(len(baseline_window), 5 * window):]
        long_vol = float(np.std(baseline_window, ddof=1)) if baseline_window.size > 5 else realized_vol
    else:
        long_vol = realized_vol
    vol_z = (realized_vol - long_vol) / long_vol if long_vol > 1e-12 else 0.0

    # Решаем регим
    trend_strength = abs(slope) / max(realized_vol, 1e-9)

    if vol_z > 1.5:
        label: RegimeT = "volatile"
        conf = float(min(1.0, vol_z / 3))
    elif trend_strength > 0.5:
        label = "trending_up" if slope > 0 else "trending_down"
        conf = float(min(1.0, trend_strength / 1.5))
    else:
        label = "ranging"
        conf = float(min(1.0, 1.0 - trend_strength))

    return MarketRegime(
        label=label, trend_slope=float(slope),
        realized_volatility=realized_vol, vol_z_score=float(vol_z),
        confidence=conf,
    )


REGIME_PREFERENCES: dict[RegimeT, dict[str, float]] = {
    # коэффициенты для базовых стратегий — умножаются на адаптивные веса
    "trending_up":   {"ma_crossover": 1.3, "bollinger_breakout": 1.2, "rsi_reversion": 0.7},
    "trending_down": {"ma_crossover": 1.2, "bollinger_breakout": 1.0, "rsi_reversion": 0.8},
    "ranging":       {"ma_crossover": 0.7, "bollinger_breakout": 0.8, "rsi_reversion": 1.4},
    "volatile":      {"ma_crossover": 0.6, "bollinger_breakout": 0.6, "rsi_reversion": 0.6},
}


def apply_regime_preferences(
    base_weights: dict[str, float],
    regime: MarketRegime,
    base_lookup: dict[str, str] | None = None,
) -> dict[str, float]:
    """Применить regime preferences к словарю весов стратегий.

    base_lookup: {strategy_name → base_name}; нужно для DynamicStrategy с
    нестандартным name. Если не задан — name считается = base.
    """
    prefs = REGIME_PREFERENCES.get(regime.label, {})
    if not prefs:
        return base_weights
    out: dict[str, float] = {}
    for name, w in base_weights.items():
        base = (base_lookup or {}).get(name, name)
        multiplier = prefs.get(base, 1.0)
        # учитываем confidence регима — плавный переход
        scaled = w * (1 + (multiplier - 1) * regime.confidence)
        out[name] = max(0.01, scaled)
    return out
