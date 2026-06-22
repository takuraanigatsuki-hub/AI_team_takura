"""Цикл автономного LLM-агента."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select

from ..analytics import compute_portfolio_risk, compute_returns, run_stress_tests
from ..core.config import Settings, get_settings
from ..core.database import session_scope
from ..core.logging import logger
from ..engine.trader import TradeEngine, get_engine
from ..exchange.base import ExchangeError
from ..llm.client import LLMUnavailable, get_llm_client
from ..models.db import AgentJournal, AgentMemo
from ..news.feeds import get_news_service
from ..optimizer import max_sharpe, risk_parity
from ..sentiment import aggregate_sentiment
from ..strategies.indicators import bollinger_bands, ema, rsi
from .prompts import SYSTEM_PROMPT
from .tool_schemas import trade_tools
from .tools import ToolCall, ToolExecutor, parse_plan, positions_snapshot


@dataclass
class _AgentStats:
    last_run_at: datetime | None = None
    last_error: str | None = None
    cycles: int = 0


class AutonomousAgent:
    """LLM-портфельный менеджер. Запускается по таймеру и принимает решения."""

    def __init__(
        self,
        engine: TradeEngine | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.engine = engine or get_engine()
        self.settings = settings or get_settings()
        self.news = get_news_service()
        self.stats = _AgentStats()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._lock = asyncio.Lock()
        self._executor = ToolExecutor(self.engine, self.settings)

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.llm_api_key)

    async def start(self) -> None:
        if self.running:
            return
        if not self.enabled:
            raise RuntimeError("LLM_API_KEY не задан — агенту нечем думать")
        # Базовому движку тоже нужно работать (он считает equity и стопы),
        # но стратегические сделки оставим за агентом — пауза систематических входов.
        if not self.engine.running:
            await self.engine.start()
        self.engine.pause(True)  # систематические сделки на паузе, агент рулит сам
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop(), name="agent-loop")
        logger.info(
            "AutonomousAgent started: model={} interval={}s",
            self.settings.llm_model, self.settings.agent_interval_seconds,
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=15.0)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None
        # вернём систематический ансамбль в активное состояние, но не запускаем сам движок
        self.engine.pause(False)
        logger.info("AutonomousAgent stopped")

    async def _run_loop(self) -> None:
        interval = max(60, int(self.settings.agent_interval_seconds))
        # первый тик — сразу, без задержки
        await self.tick()
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
                break  # stop fired
            except asyncio.TimeoutError:
                try:
                    await self.tick()
                except Exception as exc:  # noqa: BLE001
                    self.stats.last_error = str(exc)
                    logger.exception("agent tick failed: {}", exc)

    async def tick(self) -> dict[str, Any]:
        async with self._lock:
            self.stats.last_run_at = datetime.now(timezone.utc)
            self.stats.cycles += 1
            try:
                snapshot = await self._collect_snapshot()
                news_items = await self._collect_news()
                journal = self._collect_journal(self.settings.agent_journal_lookback)
                memos = self._collect_memos(limit=3)
                user_prompt = self._build_user_prompt(snapshot, news_items, journal, memos)

                client = get_llm_client()
                thesis, calls, raw_for_log = await self._call_llm(
                    client, user_prompt, snapshot
                )
                if calls is None:
                    return {"error": raw_for_log or "llm failure"}

                results = await self._executor.execute(
                    calls, snapshot, self.settings.agent_max_actions_per_cycle
                )
                executed = [
                    {"tool": r.tool, "args": r.args, "accepted": r.accepted,
                     "detail": r.detail, "order_id": r.order_id}
                    for r in results
                ]
                self._save_journal(
                    thesis=thesis,
                    actions=[{"tool": c.tool, "args": c.args} for c in calls],
                    executed=executed,
                    market_view=snapshot,
                    error="",
                )
                self.stats.last_error = None
                self._notify_agent_async(thesis, executed)
                return {"thesis": thesis, "executed": executed}
            except Exception as exc:  # noqa: BLE001
                self.stats.last_error = str(exc)
                logger.exception("agent.tick top-level error: {}", exc)
                return {"error": str(exc)}

    async def _call_llm(
        self,
        client,
        user_prompt: str,
        snapshot: dict[str, Any],
    ) -> tuple[str, list[ToolCall] | None, str]:
        """Зовёт LLM — сначала через native tools, при провале — fallback в JSON-mode.

        Возвращает (thesis, calls, raw_or_error). При полной неудаче calls=None.
        """
        allowed = list(self.settings.symbols)
        tools = trade_tools(allowed)

        # ----- 1) tools API (native function-calling) --------------------
        if self.settings.llm_use_tools:
            try:
                tools_resp = await asyncio.to_thread(
                    client.complete_with_tools,
                    SYSTEM_PROMPT, user_prompt, tools,
                    temperature=self.settings.agent_temperature,
                    max_tokens=self.settings.agent_max_tokens,
                    tool_choice="auto",
                )
            except LLMUnavailable as exc:
                logger.warning("tools API failed ({}), fallback to JSON-mode", exc)
                tools_resp = None
            if tools_resp is not None:
                thesis = str(tools_resp.get("content") or "").strip()
                calls = [
                    ToolCall(tool=str(t["name"]).lower(), args=dict(t["arguments"] or {}))
                    for t in tools_resp.get("tool_calls") or []
                    if str(t.get("name", "")).lower() in {"place_order", "close_position", "hold"}
                ]
                # модель может вернуть только текст без tool_calls — это эквивалент "hold"
                if not calls:
                    calls = [ToolCall(tool="hold", args={"reason": thesis[:200] or "no tool calls"})]
                return thesis, calls, "ok:tools"

        # ----- 2) fallback: JSON-mode -----------------------------------
        try:
            raw = await asyncio.to_thread(
                client.complete,
                SYSTEM_PROMPT, user_prompt,
                temperature=self.settings.agent_temperature,
                max_tokens=self.settings.agent_max_tokens,
                response_format_json=True,
            )
        except LLMUnavailable as exc:
            self.stats.last_error = str(exc)
            self._save_journal(
                thesis="", actions=[], executed=[],
                market_view=snapshot, error=f"LLM: {exc}",
            )
            return "", None, str(exc)
        thesis, calls, parse_err = parse_plan(raw)
        if parse_err:
            logger.warning("agent JSON parse failed: {} :: raw={}", parse_err, raw[:300])
            self._save_journal(
                thesis=thesis, actions=[], executed=[],
                market_view=snapshot, error=f"parse: {parse_err}",
            )
            return thesis, None, parse_err
        return thesis, calls, "ok:json"

    # --------------------------------------------------------------- snapshot
    async def _collect_snapshot(self) -> dict[str, Any]:
        balances = await self.engine.exchange.fetch_balance()
        cash, positions_value, prices = await self.engine._compute_state(balances)
        equity = cash + positions_value
        daily_start_equity = self.engine.stats.daily_start_equity or equity

        per_symbol: dict[str, dict[str, Any]] = {}
        for symbol in self.settings.symbols:
            try:
                rows = await self.engine.exchange.fetch_ohlcv(
                    symbol, timeframe=self.settings.timeframe, limit=120
                )
            except ExchangeError as exc:
                per_symbol[symbol] = {"error": str(exc)}
                continue
            if not rows:
                continue
            df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
            close = df["close"]
            try:
                ema_f = float(ema(close, 12).iloc[-1])
                ema_s = float(ema(close, 26).iloc[-1])
                rsi_v = float(rsi(close, 14).iloc[-1])
                lower, mid, upper = bollinger_bands(close, 20, 2.0)
                bb = (float(lower.iloc[-1]), float(mid.iloc[-1]), float(upper.iloc[-1]))
            except Exception:  # noqa: BLE001
                ema_f = ema_s = rsi_v = 0.0
                bb = (0.0, 0.0, 0.0)
            ch_24 = (
                float(close.iloc[-1] / close.iloc[-min(96, len(close) - 1)] - 1.0) * 100
                if len(close) > 10 else 0.0
            )
            per_symbol[symbol] = {
                "price": float(close.iloc[-1]),
                "change_pct_recent": round(ch_24, 2),
                "ema_fast": round(ema_f, 4),
                "ema_slow": round(ema_s, 4),
                "rsi_14": round(rsi_v, 2),
                "bb_lower": round(bb[0], 4),
                "bb_mid": round(bb[1], 4),
                "bb_upper": round(bb[2], 4),
            }

        positions_qty = positions_snapshot()
        positions_info = []
        for symbol, qty in positions_qty.items():
            price = prices.get(symbol)
            positions_info.append({
                "symbol": symbol, "quantity": qty,
                "current_price": price,
                "market_value": (qty * price) if price else None,
            })

        # ----- Portfolio analytics (BlackRock-style: риск ПЕРВЫМ) -----
        analytics = await self._collect_analytics(positions_qty, prices)

        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": self.settings.mode,
            "quote_currency": self.settings.quote_currency,
            "allowed_symbols": list(self.settings.symbols),
            "timeframe": self.settings.timeframe,
            "equity": round(equity, 4),
            "cash": round(cash, 4),
            "positions_value": round(positions_value, 4),
            "daily_pnl": round(equity - daily_start_equity, 4),
            "daily_start_equity": round(daily_start_equity, 4),
            "open_positions_count": sum(1 for q in positions_qty.values() if q > 0),
            "max_open_positions": self.settings.max_open_positions,
            "risk_per_trade": self.settings.risk_per_trade,
            "daily_loss_limit_pct": self.settings.daily_loss_limit_pct,
            "stop_loss_pct": self.settings.stop_loss_pct,
            "take_profit_pct": self.settings.take_profit_pct,
            "min_order_notional": self.settings.min_order_notional,
            "positions": positions_info,
            "positions_qty": positions_qty,
            "prices": prices,
            "markets": per_symbol,
            "analytics": analytics,
        }

    async def _collect_analytics(
        self,
        positions_qty: dict[str, float],
        prices: dict[str, float],
    ) -> dict[str, Any]:
        """Считает риск-метрики портфеля и две предложенные аллокации."""
        symbols = list(self.settings.symbols)
        series: dict[str, pd.Series] = {}
        for symbol in symbols:
            try:
                rows = await self.engine.exchange.fetch_ohlcv(
                    symbol, timeframe=self.settings.timeframe, limit=300
                )
            except ExchangeError:
                continue
            if not rows:
                continue
            df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
            series[symbol] = df.set_index("ts")["close"]
        returns = compute_returns(series)
        if returns.empty:
            return {"available": False, "reason": "no return data"}

        # текущие веса — по рыночной стоимости позиций
        holdings_value: dict[str, float] = {}
        for sym, qty in positions_qty.items():
            price = prices.get(sym)
            if price:
                holdings_value[sym] = qty * price
        total_val = sum(holdings_value.values())
        if total_val > 0:
            weights = {s: holdings_value.get(s, 0.0) / total_val for s in symbols}
        else:
            weights = None  # equal-weight

        from ..api.routes_analytics import _periods_per_year
        ppy = _periods_per_year(self.settings.timeframe)

        risk = compute_portfolio_risk(returns, weights, periods_per_year=ppy)
        stress = run_stress_tests(holdings_value) if holdings_value else []
        try:
            target_ms = max_sharpe(returns, periods_per_year=ppy)
            target_rp = risk_parity(returns, periods_per_year=ppy)
        except Exception as exc:  # noqa: BLE001
            logger.warning("optimizer failed: {}", exc)
            target_ms = target_rp = None

        return {
            "available": True,
            "risk": {
                "expected_return": risk.expected_return,
                "volatility": risk.volatility,
                "sharpe": risk.sharpe,
                "var_95": risk.var_95,
                "cvar_95": risk.cvar_95,
                "betas": risk.betas,
                "risk_contributions": [
                    {"symbol": c.symbol, "weight": c.weight,
                     "pct_of_total_risk": c.pct_of_total_risk}
                    for c in risk.contributions
                ],
            },
            "stress_tests": [
                {"scenario": r.scenario, "description": r.description,
                 "portfolio_change_pct": r.portfolio_change_pct}
                for r in stress[:6]
            ],
            "suggested_allocations": {
                "max_sharpe": target_ms.weights if target_ms and target_ms.converged else None,
                "risk_parity": target_rp.weights if target_rp and target_rp.converged else None,
            },
        }

    async def _collect_news(self) -> dict[str, Any]:
        try:
            items = await self.news.fetch(limit=self.settings.agent_news_per_cycle * 4)
        except Exception as exc:  # noqa: BLE001
            logger.warning("news fetch failed: {}", exc)
            return {"items": [], "sentiment": {}}
        items_payload = [
            {
                "title": i.title,
                "source": i.source,
                "published_at": i.published_at.isoformat() if i.published_at else None,
                "summary": i.summary,
            }
            for i in items
        ]
        sentiment_map = aggregate_sentiment(
            items_payload, symbols=list(self.settings.symbols), max_age_hours=72
        )
        return {
            "items": items_payload[: self.settings.agent_news_per_cycle],
            "sentiment": {
                k: v.as_dict() for k, v in sentiment_map.items()
            },
        }

    def _collect_journal(self, limit: int) -> list[dict[str, Any]]:
        with session_scope() as session:
            rows = session.execute(
                select(AgentJournal).order_by(AgentJournal.ts.desc()).limit(limit)
            ).scalars().all()
            out: list[dict[str, Any]] = []
            for row in reversed(rows):
                out.append({
                    "ts": row.ts.isoformat(),
                    "thesis": row.thesis,
                    "actions": _safe_json(row.actions),
                    "executed": _safe_json(row.executed),
                    "error": row.error,
                })
            return out

    def _build_user_prompt(
        self,
        snapshot: dict[str, Any],
        news: dict[str, Any],
        journal: list[dict[str, Any]],
        memos: list[dict[str, Any]] | None = None,
    ) -> str:
        memo_block = ""
        if memos:
            memo_block = (
                "## Memo (твои собственные уроки из предыдущих рефлексий)\n"
                f"```json\n{json.dumps(memos, ensure_ascii=False, indent=2)}\n```\n\n"
            )
        return (
            memo_block
            + "## Снимок портфеля, рынка и риска\n"
            + f"```json\n{json.dumps(snapshot, ensure_ascii=False, indent=2)}\n```\n\n"
            + "## Свежие новости + агрегированный сентимент по инструментам\n"
            + f"```json\n{json.dumps(news, ensure_ascii=False, indent=2)}\n```\n\n"
            + "## Твои предыдущие тики\n"
            + f"```json\n{json.dumps(journal, ensure_ascii=False, indent=2)}\n```\n\n"
            + "Прими решение по правилам и верни tool-вызовы (place_order / "
            + "close_position / hold). Обоснование (`reason`) каждого вызова "
            + "должно ссылаться на конкретные числа из снапшота: VaR, β, "
            + "contribution-to-risk, сентимент, индикаторы."
        )

    def _collect_memos(self, limit: int = 3) -> list[dict[str, Any]]:
        with session_scope() as session:
            rows = session.execute(
                select(AgentMemo).order_by(AgentMemo.ts.desc()).limit(limit)
            ).scalars().all()
            return [
                {"ts": row.ts.isoformat(), "summary": row.summary,
                 "rules_learned": _safe_json(row.rules_learned)}
                for row in reversed(rows)
            ]

    def _save_journal(
        self,
        thesis: str,
        actions: list[dict[str, Any]],
        executed: list[dict[str, Any]],
        market_view: dict[str, Any],
        error: str,
    ) -> None:
        with session_scope() as session:
            session.add(AgentJournal(
                thesis=thesis,
                actions=json.dumps(actions, ensure_ascii=False),
                executed=json.dumps(executed, ensure_ascii=False),
                market_view=json.dumps(
                    {k: market_view.get(k) for k in (
                        "ts", "mode", "equity", "cash", "positions_value",
                        "daily_pnl", "open_positions_count", "markets", "positions",
                    )},
                    ensure_ascii=False,
                ),
                error=error,
                mode=self.settings.mode,
            ))


    def _notify_agent_async(self, thesis: str, executed: list[dict]) -> None:
        if not self.settings.telegram_notify_agent:
            return
        try:
            from ..telegram.notifier import get_notifier

            notifier = get_notifier()
            if not notifier.enabled:
                return
            # шлём, только если что-то реально исполнили (или была отклонённая попытка)
            if not executed:
                return
            loop = asyncio.get_event_loop()
            loop.create_task(notifier.notify_agent(thesis, executed))
        except Exception as exc:  # noqa: BLE001
            logger.debug("telegram notify_agent skipped: {}", exc)


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return text


_singleton: AutonomousAgent | None = None


def get_agent() -> AutonomousAgent:
    global _singleton
    if _singleton is None:
        _singleton = AutonomousAgent()
    return _singleton


def set_agent(agent: AutonomousAgent | None) -> None:
    global _singleton
    _singleton = agent
