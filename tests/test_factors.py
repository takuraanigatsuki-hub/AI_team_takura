import numpy as np
import pandas as pd
import pytest

from app.analytics import (
    compute_factor_exposures,
    compute_portfolio_factors,
    compute_returns,
)


def _market_with_correlated_asset(seed=0, n=400, beta=1.5):
    rng = np.random.default_rng(seed)
    btc = rng.normal(0.0005, 0.02, n)
    eth = 0.6 * btc + rng.normal(0.0003, 0.015, n)
    alt = beta * btc + rng.normal(0.0, 0.01, n)
    idx = np.arange(n)
    return pd.DataFrame({
        "BTC/USDT": btc, "ETH/USDT": eth, "ALT/USDT": alt,
    }, index=idx)


def test_factor_exposures_recovers_btc_beta():
    returns = _market_with_correlated_asset(beta=1.5)
    factors = compute_factor_exposures(returns)
    by_sym = {f.symbol: f for f in factors}
    # для BTC сам себе — beta = 1
    assert by_sym["BTC/USDT"].btc_beta == 1.0
    # для ALT, который мы сконструировали как 1.5 * BTC + шум — β близко к 1.5
    assert by_sym["ALT/USDT"].btc_beta == pytest.approx(1.5, abs=0.15)
    assert by_sym["ALT/USDT"].r_squared > 0.7


def test_factor_exposures_handles_empty():
    assert compute_factor_exposures(pd.DataFrame()) == []


def test_portfolio_factors_weight_aggregation():
    returns = _market_with_correlated_asset()
    weights = {"BTC/USDT": 0.5, "ETH/USDT": 0.3, "ALT/USDT": 0.2}
    pf = compute_portfolio_factors(returns, weights)
    assert sum(pf.weights.values()) == pytest.approx(1.0, abs=1e-6)
    assert 0 <= pf.diversification_score <= 1
    # портфельный β к BTC — взвешенная средняя экспозиций
    expected_beta = 0.5 * 1.0 + 0.3 * (compute_factor_exposures(returns)[1].btc_beta or 0) \
                  + 0.2 * (compute_factor_exposures(returns)[2].btc_beta or 0)
    assert pf.portfolio_btc_beta == pytest.approx(expected_beta, abs=0.05)


def test_diversification_score_one_for_equal_split():
    returns = _market_with_correlated_asset()
    weights = {"BTC/USDT": 1/3, "ETH/USDT": 1/3, "ALT/USDT": 1/3}
    pf = compute_portfolio_factors(returns, weights)
    assert pf.diversification_score == pytest.approx(1.0, abs=1e-6)


def test_diversification_score_zero_for_one_asset():
    returns = _market_with_correlated_asset()
    weights = {"BTC/USDT": 1.0, "ETH/USDT": 0.0, "ALT/USDT": 0.0}
    pf = compute_portfolio_factors(returns, weights)
    assert pf.diversification_score == pytest.approx(0.0, abs=0.05)
