import numpy as np
import pandas as pd
import pytest

from app.analytics import compute_returns
from app.optimizer import max_sharpe, min_variance, risk_parity


def _three_asset_returns(seed=1, n=400):
    rng = np.random.default_rng(seed)
    a = 100 * np.exp(np.cumsum(rng.normal(0.0008, 0.02, n)))   # «BTC» — выше доходность
    b = 50 * np.exp(np.cumsum(rng.normal(0.0004, 0.025, n)))   # «ETH»
    c = 30 * np.exp(np.cumsum(rng.normal(0.0002, 0.05, n)))    # «волатильный мем»
    idx = np.arange(n) * 3600_000
    series = {
        "BTC/USDT": pd.Series(a, index=idx),
        "ETH/USDT": pd.Series(b, index=idx),
        "DOGE/USDT": pd.Series(c, index=idx),
    }
    return compute_returns(series)


def _weights_sum_to_one(weights):
    assert abs(sum(weights.values()) - 1.0) < 1e-3


def test_max_sharpe_converges_and_normalizes():
    r = _three_asset_returns()
    res = max_sharpe(r, periods_per_year=8760)
    assert res.converged
    _weights_sum_to_one(res.weights)
    assert all(w >= -1e-6 for w in res.weights.values())
    assert res.sharpe is not None


def test_min_variance_lowest_vol():
    r = _three_asset_returns()
    mv = min_variance(r, periods_per_year=8760)
    ms = max_sharpe(r, periods_per_year=8760)
    # min-variance не должен быть волатильнее max-sharpe
    assert mv.volatility <= ms.volatility + 1e-6
    _weights_sum_to_one(mv.weights)


def test_risk_parity_equalizes_contributions():
    r = _three_asset_returns()
    rp = risk_parity(r, periods_per_year=8760)
    _weights_sum_to_one(rp.weights)
    # вычислим вклад каждого актива и проверим, что они близко к равным
    import numpy as np

    cov = r.cov().values
    symbols = list(r.columns)
    w = np.array([rp.weights[s] for s in symbols])
    sigma_p = float(np.sqrt(w @ cov @ w))
    rc = w * (cov @ w) / sigma_p
    rc_norm = rc / sigma_p  # доли, сумма = 1
    # для 3 активов: цель 1/3 каждому; допускаем ±15% (это локальный минимум)
    for c in rc_norm:
        assert abs(c - 1.0 / 3) < 0.15


def test_optimizer_handles_empty():
    empty = pd.DataFrame()
    for fn in (max_sharpe, min_variance, risk_parity):
        res = fn(empty)
        assert res.converged is False
        assert res.weights == {}
