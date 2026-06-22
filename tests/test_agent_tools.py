import pytest

from app.agent.tools import ToolExecutor, parse_plan
from app.core.config import Settings
from app.core.database import configure, init_db
from app.engine.trader import TradeEngine
from app.exchange.base import BaseExchange, OrderResult
from app.exchange.paper import PaperExchange


@pytest.fixture()
def isolated_db(tmp_path):
    configure(f"sqlite:///{tmp_path}/agent.db")
    init_db()


class _DS(BaseExchange):
    def __init__(self, price=100.0):
        self.price = price

    async def fetch_ohlcv(self, symbol, timeframe="15m", limit=200):
        return [[i * 60_000, self.price, self.price, self.price, self.price, 1] for i in range(50)]

    async def fetch_ticker(self, symbol):
        return self.price

    async def fetch_balance(self):
        return {}

    async def create_market_order(self, symbol, side, quantity):
        return OrderResult("x", symbol, side, quantity, self.price, 0.0, 0)


def _engine(starting=10_000.0):
    settings = Settings(
        symbols=["BTC/USDT", "ETH/USDT"],
        risk_per_trade=0.1,
        max_open_positions=2,
        stop_loss_pct=0.05,
        take_profit_pct=0.1,
        daily_loss_limit_pct=0.5,
        min_order_notional=5,
    )
    ex = PaperExchange(_DS(), quote_currency="USDT", starting_balance=starting, fee_rate=0)
    return TradeEngine(settings=settings, exchange=ex, strategies=[]), settings


def test_parse_plan_extracts_thesis_and_actions():
    raw = """```json
    {
      "thesis": "BTC consolidating; small probe.",
      "actions": [
        {"tool": "place_order", "args": {"symbol":"BTC/USDT","side":"buy","quote_amount":100,"reason":"r"}},
        {"tool": "hold", "args": {"reason":"watch ETH"}}
      ]
    }
    ```"""
    thesis, calls, err = parse_plan(raw)
    assert err == ""
    assert "BTC" in thesis
    assert [c.tool for c in calls] == ["place_order", "hold"]
    assert calls[0].args["quote_amount"] == 100


def test_parse_plan_handles_garbage():
    thesis, calls, err = parse_plan("totally not json")
    assert calls == []
    assert err


def test_parse_plan_skips_unknown_tools():
    raw = '{"thesis":"x","actions":[{"tool":"hack_db","args":{}},{"tool":"hold","args":{"reason":"r"}}]}'
    thesis, calls, err = parse_plan(raw)
    assert err == ""
    assert [c.tool for c in calls] == ["hold"]


@pytest.mark.asyncio
async def test_executor_rejects_symbol_outside_allowlist(isolated_db):
    engine, settings = _engine()
    ex = ToolExecutor(engine, settings)
    snapshot = {
        "cash": 1000, "equity": 1000, "daily_pnl": 0, "daily_start_equity": 1000,
        "prices": {"BTC/USDT": 100, "ETH/USDT": 100, "DOGE/USDT": 0.1},
        "positions_qty": {},
    }
    from app.agent.tools import ToolCall
    res = await ex.execute(
        [ToolCall("place_order", {"symbol": "DOGE/USDT", "side": "buy",
                                   "quote_amount": 100, "reason": "memes"})],
        snapshot, max_actions=5,
    )
    assert res[0].accepted is False
    assert "не в списке" in res[0].detail


@pytest.mark.asyncio
async def test_executor_buys_within_risk(isolated_db):
    engine, settings = _engine()
    ex = ToolExecutor(engine, settings)
    snapshot = {
        "cash": 1000, "equity": 1000, "daily_pnl": 0, "daily_start_equity": 1000,
        "prices": {"BTC/USDT": 100}, "positions_qty": {},
    }
    from app.agent.tools import ToolCall
    res = await ex.execute(
        [ToolCall("place_order", {"symbol": "BTC/USDT", "side": "buy",
                                   "quote_amount": 200, "reason": "test"})],
        snapshot, max_actions=5,
    )
    assert res[0].accepted is True
    # 10% of 1000 = 100 USDT max, agent asked for 200 → clamped to 100 / 100 = 1.0 BTC
    assert "BUY" in res[0].detail
    # cash снизился в snapshot тоже (executor мутирует копию snapshot prices/positions, но cash локально)


@pytest.mark.asyncio
async def test_executor_blocks_when_max_positions_reached(isolated_db):
    engine, settings = _engine()
    ex = ToolExecutor(engine, settings)
    snapshot = {
        "cash": 1000, "equity": 1000, "daily_pnl": 0, "daily_start_equity": 1000,
        "prices": {"BTC/USDT": 100, "ETH/USDT": 100},
        "positions_qty": {"BTC/USDT": 0.5, "ETH/USDT": 0.5},
    }
    from app.agent.tools import ToolCall
    res = await ex.execute(
        [ToolCall("place_order", {"symbol": "ETH/USDT", "side": "buy",
                                   "quote_amount": 100, "reason": "more"})],
        snapshot, max_actions=5,
    )
    assert res[0].accepted is False  # уже есть позиция по ETH


@pytest.mark.asyncio
async def test_executor_respects_max_actions_per_cycle(isolated_db):
    engine, settings = _engine()
    ex = ToolExecutor(engine, settings)
    snapshot = {
        "cash": 1000, "equity": 1000, "daily_pnl": 0, "daily_start_equity": 1000,
        "prices": {"BTC/USDT": 100, "ETH/USDT": 100}, "positions_qty": {},
    }
    from app.agent.tools import ToolCall
    res = await ex.execute(
        [
            ToolCall("hold", {"reason": "1"}),
            ToolCall("hold", {"reason": "2"}),
            ToolCall("hold", {"reason": "3"}),
            ToolCall("hold", {"reason": "4"}),
        ],
        snapshot, max_actions=2,
    )
    accepted = [r for r in res if r.accepted]
    rejected = [r for r in res if not r.accepted]
    assert len(accepted) == 2
    assert len(rejected) == 2
    assert all("превышен лимит" in r.detail for r in rejected)
