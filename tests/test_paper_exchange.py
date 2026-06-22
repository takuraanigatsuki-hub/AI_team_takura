import pytest

from app.exchange.base import BaseExchange, OrderResult
from app.exchange.paper import PaperExchange


class FakeDataSource(BaseExchange):
    def __init__(self, prices):
        self.prices = prices

    async def fetch_ohlcv(self, symbol, timeframe="15m", limit=200):
        p = self.prices.get(symbol, 100.0)
        return [[i * 60_000, p, p, p, p, 1.0] for i in range(limit)]

    async def fetch_ticker(self, symbol):
        return self.prices.get(symbol, 0.0)

    async def fetch_balance(self):
        return {}

    async def create_market_order(self, symbol, side, quantity):  # noqa: D401
        return OrderResult("x", symbol, side, quantity, 0.0, 0.0, 0)


@pytest.mark.asyncio
async def test_paper_buy_and_sell_roundtrip():
    ds = FakeDataSource({"BTC/USDT": 100.0})
    paper = PaperExchange(ds, quote_currency="USDT", starting_balance=1000.0, fee_rate=0.001)

    buy = await paper.create_market_order("BTC/USDT", "buy", 1.0)
    assert buy.side == "buy"
    bal = paper.snapshot_balances()
    # 1 BTC at 100 + 0.1 fee
    assert pytest.approx(bal["USDT"], rel=1e-9) == 1000 - 100 - 0.1
    assert pytest.approx(bal["BTC"], rel=1e-9) == 1.0

    ds.prices["BTC/USDT"] = 120.0
    sell = await paper.create_market_order("BTC/USDT", "sell", 1.0)
    assert sell.side == "sell"
    bal = paper.snapshot_balances()
    # received 120, minus fee 0.12; previous cash 899.9
    assert pytest.approx(bal["USDT"], rel=1e-9) == 899.9 + 120 - 0.12
    assert pytest.approx(bal["BTC"], rel=1e-9) == 0.0


@pytest.mark.asyncio
async def test_paper_rejects_insufficient_balance():
    ds = FakeDataSource({"BTC/USDT": 100.0})
    paper = PaperExchange(ds, starting_balance=10.0)
    with pytest.raises(Exception):
        await paper.create_market_order("BTC/USDT", "buy", 1.0)
