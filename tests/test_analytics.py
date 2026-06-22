import numpy as np
import pandas as pd
import pytest

from app.analytics import (
    compute_portfolio_risk,
    compute_returns,
    compute_risk_contribution,
    default_scenarios,
    run_stress_tests,
)


def _two_asset_prices(seed=42, n=300):
    rng = np.random.default_rng(seed)
    a = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, n)))
    b = 50 * np.exp(np.cumsum(rng.normal(0.0003, 0.03, n)))
    idx = np.arange(n) * 3600_000
    return {
        "BTC/USDT": pd.Series(a, index=idx),
        "ETH/USDT": pd.Series(b, index=idx),
    }


def test_compute_returns_shape():
    series = _two_asset_prices()
    returns = compute_returns(series)
    assert list(returns.columns) == ["BTC/USDT", "ETH/USDT"]
    assert returns.shape[0] == 299  # log diff drops first row
    assert returns.isna().sum().sum() == 0


def test_portfolio_risk_basic():
    series = _two_asset_prices()
    returns = compute_returns(series)
    pr = compute_portfolio_risk(
        returns, weights={"BTC/USDT": 0.6, "ETH/USDT": 0.4},
        periods_per_year=8760, var_alpha=0.05,
    )
    assert pr.weights["BTC/USDT"] == pytest.approx(0.6)
    assert pr.volatility > 0
    assert pr.var_95 < 0  # это убыток → отрицательное число
    assert pr.cvar_95 <= pr.var_95  # хвост не легче самого VaR
    assert "BTC/USDT" in pr.betas
    # сумма pct_of_total_risk должна быть ≈ 100
    total_pct = sum(c.pct_of_total_risk for c in pr.contributions)
    assert abs(total_pct - 100.0) < 1.0


def test_risk_contribution_sums_to_100():
    series = _two_asset_prices()
    returns = compute_returns(series)
    contributions = compute_risk_contribution(
        returns, {"BTC/USDT": 0.5, "ETH/USDT": 0.5}
    )
    total_pct = sum(c.pct_of_total_risk for c in contributions)
    assert abs(total_pct - 100.0) < 1e-3


def test_stress_test_applies_shocks():
    holdings = {"BTC/USDT": 1000.0, "ETH/USDT": 500.0}
    results = run_stress_tests(holdings)
    # должны быть результаты по всем встроенным сценариям
    assert len(results) == len(default_scenarios())
    crash = next(r for r in results if r.scenario == "btc_flash_crash_30")
    # BTC -30%, ETH -39% → -300 + -195 = -495 из 1500 → -33%
    assert crash.portfolio_change_abs == pytest.approx(-495, rel=0.05)
    assert crash.portfolio_change_pct == pytest.approx(-33.0, abs=2.0)


def test_stress_test_empty_returns_empty():
    assert run_stress_tests({}) == []
