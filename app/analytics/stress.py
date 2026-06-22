"""Stress-тесты портфеля. Несколько встроенных исторических сценариев + кастомные шоки."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StressScenario:
    name: str
    description: str
    shocks: dict[str, float]  # symbol → процентное изменение цены (-0.30 = -30%)


@dataclass
class StressTestResult:
    scenario: str
    description: str
    shocks_applied: dict[str, float]
    portfolio_change_pct: float
    portfolio_change_abs: float
    per_asset_change: dict[str, float]


def default_scenarios() -> list[StressScenario]:
    """Сценарии, основанные на реальных эпизодах. Шоки — за один день/несколько дней."""
    return [
        StressScenario(
            name="covid_march_2020",
            description="13 марта 2020 — крипто-падение из-за пандемии (BTC -50% за 2 дня)",
            shocks={"BTC/USDT": -0.50, "ETH/USDT": -0.55, "SOL/USDT": -0.55,
                    "BNB/USDT": -0.45, "XRP/USDT": -0.45, "DOGE/USDT": -0.50},
        ),
        StressScenario(
            name="luna_collapse_may_2022",
            description="Май 2022 — крах Terra/Luna и UST (общий бэар по альтам)",
            shocks={"BTC/USDT": -0.30, "ETH/USDT": -0.40, "SOL/USDT": -0.55,
                    "BNB/USDT": -0.35, "XRP/USDT": -0.35, "DOGE/USDT": -0.45},
        ),
        StressScenario(
            name="ftx_nov_2022",
            description="Ноябрь 2022 — банкротство FTX, заморозка вывода, паника",
            shocks={"BTC/USDT": -0.25, "ETH/USDT": -0.30, "SOL/USDT": -0.60,
                    "BNB/USDT": -0.20, "XRP/USDT": -0.20, "DOGE/USDT": -0.25},
        ),
        StressScenario(
            name="btc_flash_crash_30",
            description="Гипотетический флеш-крэш BTC -30% за час, корреляция альтов 1.3×",
            shocks={"BTC/USDT": -0.30, "ETH/USDT": -0.39, "SOL/USDT": -0.45,
                    "BNB/USDT": -0.35, "XRP/USDT": -0.35, "DOGE/USDT": -0.45},
        ),
        StressScenario(
            name="exchange_hack",
            description="Гипотетический взлом крупной биржи — отток ликвидности, -20% по топ-10",
            shocks={"BTC/USDT": -0.20, "ETH/USDT": -0.22, "SOL/USDT": -0.28,
                    "BNB/USDT": -0.30, "XRP/USDT": -0.22, "DOGE/USDT": -0.25},
        ),
        StressScenario(
            name="regulation_ban_us",
            description="Гипотетический запрет крипты в США — резкий уход капитала",
            shocks={"BTC/USDT": -0.35, "ETH/USDT": -0.40, "SOL/USDT": -0.50,
                    "BNB/USDT": -0.30, "XRP/USDT": -0.40, "DOGE/USDT": -0.45},
        ),
    ]


def run_stress_tests(
    holdings_value: dict[str, float],
    scenarios: list[StressScenario] | None = None,
    fallback_shock: float = -0.30,
) -> list[StressTestResult]:
    """Применить сценарии к портфелю. holdings_value: {symbol: текущая стоимость в фиате}."""
    if not holdings_value:
        return []
    scenarios = scenarios or default_scenarios()
    portfolio_value = float(sum(holdings_value.values()))
    if portfolio_value <= 0:
        return []

    out: list[StressTestResult] = []
    for sc in scenarios:
        per_asset: dict[str, float] = {}
        total_delta = 0.0
        for symbol, value in holdings_value.items():
            shock = sc.shocks.get(symbol, fallback_shock)
            delta = value * shock
            per_asset[symbol] = delta
            total_delta += delta
        out.append(StressTestResult(
            scenario=sc.name,
            description=sc.description,
            shocks_applied=dict(sc.shocks),
            portfolio_change_pct=round(total_delta / portfolio_value * 100, 4),
            portfolio_change_abs=round(total_delta, 4),
            per_asset_change={k: round(v, 4) for k, v in per_asset.items()},
        ))
    return out
