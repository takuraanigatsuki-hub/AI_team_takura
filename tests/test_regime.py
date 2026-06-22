import numpy as np
import pandas as pd
import pytest

from app.adaptive.regime import (
    REGIME_PREFERENCES,
    apply_regime_preferences,
    detect_regime,
)


def _trend_series(slope, n=200, vol=0.005, seed=0):
    rng = np.random.default_rng(seed)
    log_prices = np.cumsum(np.full(n, slope) + rng.normal(0, vol, n))
    return pd.Series(np.exp(log_prices) * 100, index=np.arange(n))


def test_detect_regime_trending_up():
    s = _trend_series(slope=0.005)
    r = detect_regime(s, window=80)
    assert r.label == "trending_up"
    assert r.trend_slope > 0


def test_detect_regime_trending_down():
    s = _trend_series(slope=-0.005)
    r = detect_regime(s, window=80)
    assert r.label == "trending_down"
    assert r.trend_slope < 0


def test_detect_regime_ranging():
    rng = np.random.default_rng(1)
    s = pd.Series(100 + rng.normal(0, 0.5, 300), index=range(300))
    r = detect_regime(s, window=120)
    assert r.label in ("ranging", "volatile")  # допускаем оба для шумных данных


def test_detect_regime_volatile():
    rng = np.random.default_rng(2)
    # длинный спокойный baseline → резкий всплеск волатильности в конце.
    # Нужно много спокойных свечей, чтобы long_vol baseline отражал «норму».
    quiet = rng.normal(0, 0.001, 1200)
    spike = rng.normal(0, 0.06, 80)
    log_returns = np.concatenate([quiet, spike])
    prices = 100 * np.exp(np.cumsum(log_returns))
    r = detect_regime(pd.Series(prices), window=60)
    assert r.label == "volatile"
    assert r.vol_z_score > 1.5


def test_apply_regime_preferences_amplifies_trend_strategies():
    base = {"ma_crossover": 1.0, "rsi_reversion": 1.0, "bollinger_breakout": 1.0}
    r = detect_regime(_trend_series(slope=0.005), window=80)
    adjusted = apply_regime_preferences(base, r)
    # в trending_up MA получает буст, RSI — наоборот
    assert adjusted["ma_crossover"] > base["ma_crossover"]
    assert adjusted["rsi_reversion"] < base["rsi_reversion"]


def test_preferences_dict_covers_all_regimes():
    for label in ("trending_up", "trending_down", "ranging", "volatile"):
        assert label in REGIME_PREFERENCES
