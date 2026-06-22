"""CLI: загрузить N лет OHLCV с биржи через ccxt и прогнать стратегии.

Пример:
    python -m scripts.historical_backtest \\
        --exchange binance \\
        --symbols BTC/USDT,ETH/USDT,SOL/USDT \\
        --timeframe 1h \\
        --years 3 \\
        --balance 10000

Результат:
    data/backtest_<symbol>_<timeframe>.json   — детальный отчёт
    data/backtest_summary.json                — сводка по всем парам/стратегиям
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.engine.backtest import BacktestResult, run_backtest  # noqa: E402
from app.strategies import build_strategies  # noqa: E402
from app.strategies.bollinger_breakout import BollingerBreakoutStrategy  # noqa: E402
from app.strategies.ma_crossover import MACrossoverStrategy  # noqa: E402
from app.strategies.rsi_reversion import RSIReversionStrategy  # noqa: E402


DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


TIMEFRAME_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000,
    "6h": 21_600_000, "12h": 43_200_000, "1d": 86_400_000,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exchange", default="binance", help="id биржи в ccxt")
    p.add_argument("--symbols", default="BTC/USDT,ETH/USDT,SOL/USDT")
    p.add_argument("--timeframe", default="1h", choices=list(TIMEFRAME_MS))
    p.add_argument("--years", type=float, default=3.0,
                   help="сколько лет истории грузить (макс. ~6 на 1h Binance)")
    p.add_argument("--balance", type=float, default=10_000.0)
    p.add_argument("--risk", type=float, default=0.05,
                   help="доля капитала на сделку (0.05 = 5%)")
    p.add_argument("--sl", type=float, default=0.03)
    p.add_argument("--tp", type=float, default=0.06)
    p.add_argument("--consensus", type=int, default=2)
    return p.parse_args()


async def fetch_ohlcv_history(
    exchange_id: str, symbol: str, timeframe: str, years: float
) -> pd.DataFrame:
    """Качаем по 1000 свечей за запрос, итеративно идём в прошлое."""
    import ccxt  # type: ignore

    klass = getattr(ccxt, exchange_id)
    client = klass({"enableRateLimit": True})

    end_ts = int(time.time() * 1000)
    start_ts = end_ts - int(years * 365.25 * 24 * 60 * 60 * 1000)
    tf_ms = TIMEFRAME_MS[timeframe]
    limit = 1000

    rows: list[list[float]] = []
    since = start_ts
    last_ts: int | None = None

    print(f"[{symbol}] загрузка {years:.1f} года(лет) {timeframe} свечей с {exchange_id}…")
    while since < end_ts:
        try:
            chunk = await asyncio.to_thread(
                client.fetch_ohlcv, symbol, timeframe, since, limit
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  ! ошибка: {exc}; пауза 5 сек, retry")
            await asyncio.sleep(5)
            continue
        if not chunk:
            break
        rows.extend(chunk)
        last_ts = int(chunk[-1][0])
        if last_ts <= (since - 1):
            break
        since = last_ts + tf_ms
        # учтём rate limit
        await asyncio.sleep((client.rateLimit or 1000) / 1000)
        if len(chunk) < limit and last_ts >= end_ts - tf_ms:
            break

    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset="ts").sort_values("ts").reset_index(drop=True)
    df.set_index("ts", inplace=True)
    print(f"[{symbol}] получено {len(df)} свечей, "
          f"с {datetime.fromtimestamp(int(df.index[0])/1000, tz=timezone.utc).date()} "
          f"по {datetime.fromtimestamp(int(df.index[-1])/1000, tz=timezone.utc).date()}")
    return df


def _settings_from_args(args: argparse.Namespace) -> Settings:
    return Settings(
        symbols=args.symbols.split(","),
        timeframe=args.timeframe,
        risk_per_trade=args.risk,
        max_open_positions=1,  # бэктест по одному символу за раз
        stop_loss_pct=args.sl,
        take_profit_pct=args.tp,
        daily_loss_limit_pct=0.5,  # для бэктеста не блокируем по дневной просадке
        signal_consensus=args.consensus,
        min_order_notional=1,
    )


def _summarize_trades(result: BacktestResult) -> dict[str, Any]:
    return {
        "starting_balance": result.starting_balance,
        "final_equity": round(result.final_equity, 2),
        "pnl": round(result.pnl, 2),
        "pnl_pct": round(result.pnl_pct, 2),
        "num_trades": result.num_trades,
    }


async def run_for_symbol(symbol: str, args: argparse.Namespace) -> dict[str, Any]:
    df = await fetch_ohlcv_history(args.exchange, symbol, args.timeframe, args.years)
    if df.empty:
        return {"symbol": symbol, "error": "нет данных"}

    settings = _settings_from_args(args)

    strategy_sets: dict[str, list] = {
        "ma_crossover_only": [MACrossoverStrategy()],
        "rsi_reversion_only": [RSIReversionStrategy()],
        "bollinger_breakout_only": [BollingerBreakoutStrategy()],
        "ensemble_consensus_2": build_strategies(
            ["ma_crossover", "rsi_reversion", "bollinger_breakout"]
        ),
    }
    per_strategy: dict[str, dict[str, Any]] = {}
    for name, strategies in strategy_sets.items():
        # для одиночных стратегий снизим consensus до 1
        s = settings.model_copy(update={"signal_consensus": 1 if len(strategies) == 1 else args.consensus})
        result = run_backtest(
            df, strategies, s, symbol=symbol, starting_balance=args.balance
        )
        per_strategy[name] = _summarize_trades(result)
        out = {
            "symbol": symbol,
            "strategies": name,
            **per_strategy[name],
            "trades": [
                {"side": t.side, "ts": int(t.timestamp), "price": round(t.price, 4),
                 "qty": round(t.quantity, 6), "reason": t.reason[:120]}
                for t in result.trades
            ],
            "equity_curve_tail": [
                {"ts": int(ts), "equity": round(eq, 2)}
                for ts, eq in result.equity_curve[-200:]
            ],
        }
        safe_symbol = symbol.replace("/", "-")
        path = DATA_DIR / f"backtest_{safe_symbol}_{args.timeframe}_{name}.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
        print(f"  [{name}] pnl={out['pnl']:+.2f} ({out['pnl_pct']:+.2f}%)  "
              f"trades={out['num_trades']}  → {path.name}")

    # buy & hold для сравнения
    first_close = float(df["close"].iloc[0])
    last_close = float(df["close"].iloc[-1])
    qty = args.balance / first_close
    bh_final = qty * last_close
    bh_pnl_pct = (bh_final / args.balance - 1) * 100
    per_strategy["buy_and_hold"] = {
        "starting_balance": args.balance,
        "final_equity": round(bh_final, 2),
        "pnl": round(bh_final - args.balance, 2),
        "pnl_pct": round(bh_pnl_pct, 2),
        "num_trades": 1,
    }
    print(f"  [buy_and_hold] pnl={per_strategy['buy_and_hold']['pnl']:+.2f} "
          f"({per_strategy['buy_and_hold']['pnl_pct']:+.2f}%)")

    return {"symbol": symbol, "strategies": per_strategy, "candles": len(df)}


async def main() -> int:
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    summary: list[dict] = []
    for symbol in symbols:
        try:
            res = await run_for_symbol(symbol, args)
        except Exception as exc:  # noqa: BLE001
            res = {"symbol": symbol, "error": str(exc)}
            print(f"  ! провал {symbol}: {exc}")
        summary.append(res)

    out_path = DATA_DIR / "backtest_summary.json"
    out_path.write_text(json.dumps({
        "args": vars(args),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": summary,
    }, ensure_ascii=False, indent=2))
    print(f"\nСводка сохранена в {out_path}")
    print("\n=== Сводка по парам ===")
    for r in summary:
        if "error" in r:
            print(f"  {r['symbol']}: {r['error']}")
            continue
        print(f"\n  {r['symbol']} ({r['candles']} свечей)")
        for name, m in r["strategies"].items():
            print(f"    {name:<28} pnl={m['pnl']:+9.2f}  ({m['pnl_pct']:+6.2f}%)  trades={m['num_trades']}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
