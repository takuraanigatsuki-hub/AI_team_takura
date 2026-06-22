"""Telegram-бот команд: long-polling getUpdates → команды → ответ.

Зависит только от httpx. Запускается фоновой задачей, останавливается через stop().
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

import httpx

from ..core.config import Settings, get_settings
from ..core.logging import logger
from ..metrics.performance import compute_portfolio_metrics
from ..core.database import session_scope


CommandHandler = Callable[[list[str]], Awaitable[str]]


HELP_TEXT = (
    "🤖 <b>Команды Trade-бота</b>\n"
    "/status — статус движка и портфеля\n"
    "/pnl — P&amp;L за сегодня и общие метрики\n"
    "/positions — открытые позиции\n"
    "/orders [N] — последние N ордеров (по умолчанию 10)\n"
    "/journal [N] — последние записи дневника LLM-агента\n"
    "/pause /resume — пауза/продолжение движка\n"
    "/kill /unkill — аварийная блокировка / снятие\n"
    "/agent_start /agent_stop /agent_tick — управление LLM-агентом\n"
    "/help — это сообщение"
)


class TelegramBot:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.token = self.settings.telegram_bot_token.strip()
        self.chat_id = self.settings.telegram_chat_id.strip()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._offset: int = 0
        self._handlers: dict[str, CommandHandler] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def register(self, command: str, handler: CommandHandler) -> None:
        self._handlers[command.lower()] = handler

    async def start(self) -> None:
        if not self.enabled or self.running:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="telegram-bot")
        logger.info("Telegram bot started (long-poll)")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                updates = await self._get_updates(timeout=25)
            except Exception as exc:  # noqa: BLE001
                logger.warning("telegram poll error: {}", exc)
                await asyncio.sleep(3)
                continue
            for u in updates or []:
                await self._handle_update(u)

    async def _get_updates(self, timeout: int) -> list[dict]:
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params: dict = {"timeout": timeout, "allowed_updates": ["message"]}
        if self._offset:
            params["offset"] = self._offset
        async with httpx.AsyncClient(timeout=timeout + 5) as client:
            try:
                resp = await client.get(url, params=params)
            except httpx.HTTPError as exc:
                raise RuntimeError(f"http: {exc}") from exc
        if resp.status_code >= 400:
            raise RuntimeError(f"{resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        if not body.get("ok"):
            raise RuntimeError(f"telegram: {body}")
        results = body.get("result", []) or []
        if results:
            self._offset = max(int(u["update_id"]) for u in results) + 1
        return results

    async def _handle_update(self, update: dict) -> None:
        msg = update.get("message") or {}
        chat = msg.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        text = str(msg.get("text") or "").strip()
        if not text:
            return
        if self.chat_id and chat_id != self.chat_id:
            await self._send(chat_id, "🚫 unauthorized chat")
            return
        parts = text.split()
        cmd = parts[0].lstrip("/").lower().split("@", 1)[0]
        args = parts[1:]
        handler = self._handlers.get(cmd)
        if not handler:
            await self._send(chat_id, HELP_TEXT)
            return
        try:
            reply = await handler(args)
        except Exception as exc:  # noqa: BLE001
            logger.exception("telegram handler {} failed: {}", cmd, exc)
            reply = f"⚠️ ошибка: {exc}"
        if reply:
            await self._send(chat_id, reply)

    async def _send(self, chat_id: str, text: str) -> None:
        if not chat_id:
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.post(
                    url,
                    json={
                        "chat_id": chat_id, "text": text[:4096],
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
            except httpx.HTTPError as exc:
                logger.warning("telegram reply failed: {}", exc)


def build_default_handlers(bot: TelegramBot) -> None:
    """Регистрирует стандартный набор команд."""
    from ..agent.loop import get_agent
    from ..engine.trader import get_engine

    async def help_cmd(_args):
        return HELP_TEXT

    async def status_cmd(_args):
        engine = get_engine()
        agent = get_agent()
        s = engine.status()
        text = (
            f"🟢 <b>статус</b>\n"
            f"движок: {'RUN' if s.running else 'STOP'}"
            f"{' · PAUSE' if s.paused else ''}"
            f"{' · KILL' if s.kill_switch else ''}\n"
            f"режим: {s.mode}\n"
            f"капитал: <code>{s.equity:.2f}</code>\n"
            f"кэш: <code>{s.cash:.2f}</code> · в позициях: <code>{s.positions_value:.2f}</code>\n"
            f"за день: <code>{s.daily_pnl:+.2f}</code> ({s.daily_pnl_pct:+.2f}%)\n"
            f"агент: {'on' if agent.running else 'off'}"
            f" · циклов: {agent.stats.cycles}"
        )
        if s.last_error:
            text += f"\nпоследняя ошибка: <code>{s.last_error[:200]}</code>"
        return text

    async def pnl_cmd(_args):
        with session_scope() as session:
            m = compute_portfolio_metrics(session)
        if m.points == 0:
            return "статистики пока нет (дождитесь первого тика)"
        lines = [
            f"📊 <b>P&amp;L и метрики</b>",
            f"капитал: <code>{m.current_equity:.2f}</code> (старт <code>{m.starting_equity:.2f}</code>)",
            f"всего: <code>{m.total_return:+.2f}</code> ({m.total_return_pct:+.2f}%)",
            f"max DD: <code>{m.max_drawdown_pct:.2f}%</code>",
        ]
        if m.sharpe_ratio is not None:
            lines.append(f"Sharpe: <code>{m.sharpe_ratio:.2f}</code>")
        if m.win_rate is not None:
            lines.append(f"win-rate: <code>{m.win_rate*100:.1f}%</code> по {m.num_orders} ордерам")
        if m.daily_pnl:
            last = m.daily_pnl[-1]
            lines.append(f"сегодня: <code>{last.pnl:+.2f}</code> ({last.pnl_pct:+.2f}%)")
        return "\n".join(lines)

    async def positions_cmd(_args):
        from sqlalchemy import select
        from ..models.db import Position
        with session_scope() as session:
            rows = session.execute(
                select(Position).where(Position.quantity > 0)
            ).scalars().all()
            data = [(r.symbol, float(r.quantity), float(r.avg_entry_price)) for r in rows]
        if not data:
            return "позиций нет"
        lines = ["💼 <b>открытые позиции</b>"]
        for symbol, qty, avg in data:
            lines.append(f"{symbol}: <code>{qty:.6f}</code> @ <code>{avg:.4f}</code>")
        return "\n".join(lines)

    async def orders_cmd(args):
        from sqlalchemy import select
        from ..models.db import Order
        n = 10
        if args:
            try:
                n = max(1, min(int(args[0]), 30))
            except ValueError:
                pass
        with session_scope() as session:
            rows = session.execute(
                select(Order).order_by(Order.created_at.desc()).limit(n)
            ).scalars().all()
            data = [
                (r.created_at.strftime("%m-%d %H:%M"), r.side, r.symbol, r.quantity, r.price)
                for r in rows
            ]
        if not data:
            return "ордеров нет"
        lines = [f"📜 <b>последние {len(data)} ордеров</b>"]
        for ts, side, sym, qty, price in data:
            mark = "🟢" if side == "buy" else "🔴"
            lines.append(f"{mark} <code>{ts}</code> {side} {sym} {qty:.6f} @ {price:.4f}")
        return "\n".join(lines)

    async def journal_cmd(args):
        from sqlalchemy import select
        from ..models.db import AgentJournal
        n = 5
        if args:
            try:
                n = max(1, min(int(args[0]), 10))
            except ValueError:
                pass
        with session_scope() as session:
            rows = session.execute(
                select(AgentJournal).order_by(AgentJournal.ts.desc()).limit(n)
            ).scalars().all()
            data = [(r.ts.strftime("%m-%d %H:%M"), r.thesis, r.executed) for r in rows]
        if not data:
            return "дневник пуст"
        lines = [f"🧠 <b>дневник агента (последние {len(data)})</b>"]
        for ts, thesis, executed_raw in data:
            try:
                executed = json.loads(executed_raw or "[]")
            except json.JSONDecodeError:
                executed = []
            acts = ", ".join(
                f"{'✓' if e.get('accepted') else '✗'}{e.get('tool','?')}"
                for e in executed
            ) or "—"
            lines.append(f"<code>{ts}</code> · {acts}\n<i>{(thesis or '')[:200]}</i>")
        return "\n\n".join(lines)

    async def pause_cmd(_args):
        get_engine().pause(True)
        return "⏸ движок на паузе"

    async def resume_cmd(_args):
        get_engine().pause(False)
        return "▶️ движок снят с паузы"

    async def kill_cmd(_args):
        get_engine().kill()
        return "🛑 KILL switch активирован — новые сделки заблокированы"

    async def unkill_cmd(_args):
        get_engine().reset_kill()
        return "✅ KILL switch снят"

    async def agent_start_cmd(_args):
        try:
            await get_agent().start()
        except RuntimeError as exc:
            return f"⚠️ {exc}"
        return "🤖 агент запущен"

    async def agent_stop_cmd(_args):
        await get_agent().stop()
        return "🤖 агент остановлен"

    async def agent_tick_cmd(_args):
        if not get_agent().enabled:
            return "⚠️ LLM_API_KEY не задан"
        result = await get_agent().tick()
        if "error" in result:
            return f"⚠️ {result['error']}"
        return f"🤖 тик выполнен: {result.get('thesis', '')[:200]}"

    bot.register("help", help_cmd)
    bot.register("start", help_cmd)
    bot.register("status", status_cmd)
    bot.register("pnl", pnl_cmd)
    bot.register("positions", positions_cmd)
    bot.register("orders", orders_cmd)
    bot.register("journal", journal_cmd)
    bot.register("pause", pause_cmd)
    bot.register("resume", resume_cmd)
    bot.register("kill", kill_cmd)
    bot.register("unkill", unkill_cmd)
    bot.register("agent_start", agent_start_cmd)
    bot.register("agent_stop", agent_stop_cmd)
    bot.register("agent_tick", agent_tick_cmd)


_singleton: TelegramBot | None = None


def get_telegram_bot() -> TelegramBot:
    global _singleton
    if _singleton is None:
        _singleton = TelegramBot()
        build_default_handlers(_singleton)
    return _singleton
