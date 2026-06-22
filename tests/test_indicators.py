import numpy as np
import pandas as pd

from app.strategies.indicators import bollinger_bands, ema, rsi, sma


def _series(n=120, seed=0):
    rng = np.random.default_rng(seed)
    walk = np.cumsum(rng.normal(0, 1, size=n)) + 100
    return pd.Series(walk)


def test_sma_basic():
    s = pd.Series([1, 2, 3, 4, 5])
    assert sma(s, 3).tolist()[-1] == 4.0


def test_ema_smooths():
    s = _series()
    e = ema(s, 12)
    assert e.dropna().shape[0] == len(s) - 11
    assert abs(e.iloc[-1] - s.iloc[-12:].mean()) < 10


def test_rsi_range():
    s = _series()
    r = rsi(s, 14)
    assert ((r >= 0) & (r <= 100)).all()


def test_bollinger_band_relationships():
    s = _series()
    lower, mid, upper = bollinger_bands(s, 20, 2.0)
    valid = ~upper.isna()
    assert (upper[valid] >= mid[valid]).all()
    assert (mid[valid] >= lower[valid]).all()
