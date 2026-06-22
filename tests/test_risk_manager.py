from app.core.config import Settings
from app.risk.manager import RiskManager


def _settings(**overrides):
    base = Settings(
        risk_per_trade=0.1,
        max_open_positions=2,
        stop_loss_pct=0.05,
        take_profit_pct=0.1,
        daily_loss_limit_pct=0.05,
        min_order_notional=10,
    )
    return base.model_copy(update=overrides)


def test_position_size_basic_buy():
    rm = RiskManager(_settings())
    d = rm.position_size_for_buy(
        equity=1000, cash_available=1000, price=100,
        open_positions=0, daily_pnl=0, daily_start_equity=1000,
        existing_qty=0,
    )
    assert d.allow is True
    # 10% of 1000 = 100; @ price 100 -> qty 1
    assert d.quantity == 1.0


def test_position_blocked_by_existing_qty():
    rm = RiskManager(_settings())
    d = rm.position_size_for_buy(
        equity=1000, cash_available=1000, price=100,
        open_positions=0, daily_pnl=0, daily_start_equity=1000,
        existing_qty=0.5,
    )
    assert d.allow is False


def test_position_blocked_by_max_open():
    rm = RiskManager(_settings(max_open_positions=2))
    d = rm.position_size_for_buy(
        equity=1000, cash_available=1000, price=100,
        open_positions=2, daily_pnl=0, daily_start_equity=1000,
        existing_qty=0,
    )
    assert d.allow is False


def test_position_blocked_by_daily_loss():
    rm = RiskManager(_settings())
    d = rm.position_size_for_buy(
        equity=900, cash_available=900, price=100,
        open_positions=0, daily_pnl=-100, daily_start_equity=1000,
        existing_qty=0,
    )
    assert d.allow is False


def test_stop_loss_and_take_profit_triggers():
    rm = RiskManager(_settings())
    assert rm.should_close_for_stop_loss(100, 94.9) is True
    assert rm.should_close_for_stop_loss(100, 95.1) is False
    assert rm.should_close_for_take_profit(100, 110.1) is True
    assert rm.should_close_for_take_profit(100, 109.9) is False
