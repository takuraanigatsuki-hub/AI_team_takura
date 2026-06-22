from __future__ import annotations

from dataclasses import dataclass

from ..core.config import Settings


@dataclass
class RiskDecision:
    allow: bool
    quantity: float = 0.0
    reason: str = ""


class RiskManager:
    """Решает, разрешить ли сделку и какого размера, по правилам из настроек."""

    def __init__(self, settings: Settings) -> None:
        self.s = settings

    def position_size_for_buy(
        self,
        *,
        equity: float,
        cash_available: float,
        price: float,
        open_positions: int,
        daily_pnl: float,
        daily_start_equity: float,
        existing_qty: float,
    ) -> RiskDecision:
        if price <= 0:
            return RiskDecision(False, 0.0, "цена <= 0")
        if existing_qty > 0:
            return RiskDecision(False, 0.0, "уже есть позиция")
        if open_positions >= self.s.max_open_positions:
            return RiskDecision(False, 0.0,
                                f"достигнут лимит открытых позиций ({self.s.max_open_positions})")
        if daily_start_equity > 0:
            loss_pct = -daily_pnl / daily_start_equity
            if loss_pct >= self.s.daily_loss_limit_pct:
                return RiskDecision(False, 0.0,
                                    f"дневной лимит убытков {self.s.daily_loss_limit_pct:.1%} достигнут")
        notional = equity * self.s.risk_per_trade
        notional = min(notional, cash_available)
        if notional < self.s.min_order_notional:
            return RiskDecision(False, 0.0,
                                f"размер ордера {notional:.2f} < min {self.s.min_order_notional:.2f}")
        qty = notional / price
        if qty <= 0:
            return RiskDecision(False, 0.0, "qty<=0 после расчёта")
        return RiskDecision(True, qty, f"buy notional={notional:.2f}")

    def should_close_for_stop_loss(self, avg_entry: float, price: float) -> bool:
        if avg_entry <= 0 or price <= 0 or self.s.stop_loss_pct <= 0:
            return False
        return (avg_entry - price) / avg_entry >= self.s.stop_loss_pct

    def should_close_for_take_profit(self, avg_entry: float, price: float) -> bool:
        if avg_entry <= 0 or price <= 0 or self.s.take_profit_pct <= 0:
            return False
        return (price - avg_entry) / avg_entry >= self.s.take_profit_pct

    def daily_loss_blocked(self, daily_pnl: float, daily_start_equity: float) -> bool:
        if daily_start_equity <= 0:
            return False
        return -daily_pnl / daily_start_equity >= self.s.daily_loss_limit_pct
