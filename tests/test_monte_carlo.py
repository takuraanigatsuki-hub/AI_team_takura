import numpy as np
import pandas as pd
import pytest

from app.analytics import monte_carlo_var


def _returns(seed=0, n=300):
    rng = np.random.default_rng(seed)
    a = rng.normal(0.0005, 0.02, n)
    b = 0.7 * a + rng.normal(0.0, 0.015, n)
    return pd.DataFrame({"BTC/USDT": a, "ETH/USDT": b})


def test_monte_carlo_var_basic():
    r = _returns()
    res = monte_carlo_var(r, {"BTC/USDT": 0.5, "ETH/USDT": 0.5},
                          n_simulations=5000, horizon=1, var_alpha=0.05)
    assert res.n_simulations == 5000
    assert res.var_value < 0  # потенциальный убыток — отрицательное число
    assert res.cvar_value <= res.var_value  # хвост не легче VaR
    assert res.worst_case <= res.var_value


def test_monte_carlo_multi_horizon_scales():
    r = _returns()
    one = monte_carlo_var(r, {"BTC/USDT": 1.0, "ETH/USDT": 0.0},
                          n_simulations=8000, horizon=1, seed=1)
    ten = monte_carlo_var(r, {"BTC/USDT": 1.0, "ETH/USDT": 0.0},
                          n_simulations=8000, horizon=10, seed=1)
    # на большем горизонте VaR глубже (по модулю)
    assert ten.var_value < one.var_value


def test_monte_carlo_empty_inputs():
    res = monte_carlo_var(pd.DataFrame(), {})
    assert res.n_simulations == 0
    assert res.var_value == 0.0


def test_monte_carlo_extreme_alpha():
    r = _returns()
    aggressive = monte_carlo_var(r, {"BTC/USDT": 1.0}, n_simulations=8000,
                                 var_alpha=0.01, seed=2)
    moderate = monte_carlo_var(r, {"BTC/USDT": 1.0}, n_simulations=8000,
                               var_alpha=0.05, seed=2)
    # на меньшем alpha VaR глубже
    assert aggressive.var_value < moderate.var_value
