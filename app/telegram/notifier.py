"""Telegram-уведомления: тонкий клиент поверх Bot API (HTTPS)."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..core.config import get_settings
from ..core.logging import logger


class TelegramNotifier:
    """Минимальный отправитель сообщений в Telegram.

    Если токен не задан — все методы становятся no-op.
    """

    def __init__(
        self,
        token: str = "",
        chat_id: str = "",
        timeout: float = 10.0,
    ) -> None:
        self.token = (token or "").strip()
        self.chat_id = (chat_id or "").strip()
        self.timeout = timeout
        self._lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def _base_url(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    async def send(self, text: str, *, silent: bool = False, parse_mode: str = "HTML") -> bool:
        if not self.enabled:
            return False
        async with self._lock:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self._base_url()}/sendMessage",
                        json={
                            "chat_id": self.chat_id,
                            "text": text[:4096],
                            "parse_mode": parse_mode,
                            "disable_notification": silent,
                            "disable_web_page_preview": True,
                        },
                    )
            except httpx.HTTPError as exc:
                logger.warning("telegram send failed (network): {}", exc)
                return False
            if resp.status_code >= 400:
                logger.warning("telegram send failed {}: {}", resp.status_code, resp.text[:200])
                return False
            return True

    # ---- удобные обёртки для типичных событий ----------------------------
    async def notify_order(self, *, side: str, symbol: str, quantity: float,
                           price: float, mode: str, reason: str = "") -> bool:
        arrow = "🟢" if side == "buy" else "🔴"
        notional = quantity * price
        msg = (
            f"{arrow} <b>{side.upper()} {symbol}</b>\n"
            f"qty: <code>{quantity:.6f}</code> @ <code>{price:.4f}</code>"
            f"  ({notional:.2f})\n"
            f"режим: <i>{mode}</i>"
        )
        if reason:
            msg += f"\n<i>{_escape(reason[:300])}</i>"
        return await self.send(msg)

    async def notify_error(self, where: str, error: str) -> bool:
        return await self.send(
            f"⚠️ <b>ошибка в {_escape(where)}</b>\n<code>{_escape(error[:600])}</code>"
        )

    async def notify_agent(self, thesis: str, executed: list[dict]) -> bool:
        if not executed:
            return False
        lines = []
        for e in executed[:5]:
            mark = "✓" if e.get("accepted") else "✗"
            tool = e.get("tool", "?")
            detail = str(e.get("detail", ""))[:120]
            lines.append(f"{mark} <b>{tool}</b> — {_escape(detail)}")
        body = "\n".join(lines)
        text = (
            f"🤖 <b>агент</b>\n"
            f"<i>{_escape(thesis[:300] or '(без тезиса)')}</i>\n\n{body}"
        )
        return await self.send(text)

    async def notify_daily_summary(self, equity: float, daily_pnl: float,
                                   daily_pnl_pct: float, mode: str,
                                   open_positions: int) -> bool:
        arrow = "📈" if daily_pnl >= 0 else "📉"
        msg = (
            f"{arrow} <b>дневная сводка</b>\n"
            f"капитал: <code>{equity:.2f}</code>\n"
            f"за день: <code>{daily_pnl:+.2f}</code> ({daily_pnl_pct:+.2f}%)\n"
            f"открытых позиций: <code>{open_positions}</code>\n"
            f"режим: <i>{mode}</i>"
        )
        return await self.send(msg)


def _escape(text: str) -> str:
    """Простой HTML-escape для Telegram."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


_singleton: TelegramNotifier | None = None


def get_notifier() -> TelegramNotifier:
    global _singleton
    if _singleton is None:
        s = get_settings()
        _singleton = TelegramNotifier(token=s.telegram_bot_token, chat_id=s.telegram_chat_id)
    return _singleton


def set_notifier(notifier: TelegramNotifier | None) -> None:
    global _singleton
    _singleton = notifier
