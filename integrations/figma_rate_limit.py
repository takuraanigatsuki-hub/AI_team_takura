"""Глобальный throttling и cooldown для Figma REST API."""

import asyncio
import time
from typing import Optional

_lock = asyncio.Lock()
_last_request_at = 0.0
_cooldown_until = 0.0
_rate_limit_hits = 0


class FigmaRateLimitError(RuntimeError):
    def __init__(self, retry_after: float = 60.0, detail: str = ""):
        self.retry_after = max(1.0, retry_after)
        msg = detail or f"Figma rate limit exceeded. Повторите через {int(self.retry_after)} сек."
        super().__init__(msg)


def is_in_cooldown() -> bool:
    return time.time() < _cooldown_until


def cooldown_remaining() -> int:
    return max(0, int(_cooldown_until - time.time()))


def get_status() -> dict:
    return {
        "in_cooldown": is_in_cooldown(),
        "cooldown_sec_remaining": cooldown_remaining(),
        "rate_limit_hits": _rate_limit_hits,
    }


def set_cooldown(seconds: float) -> None:
    global _cooldown_until, _rate_limit_hits
    _rate_limit_hits += 1
    _cooldown_until = max(_cooldown_until, time.time() + max(5.0, seconds))


def parse_retry_after(resp) -> float:
    import config as cfg
    default = float(cfg.config.get("figma_rate_limit_cooldown_sec", 120))
    header = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    try:
        data = resp.json()
        err = data.get("err") or data.get("message") or ""
        if "rate" in str(err).lower():
            return default
    except Exception:
        pass
    return default


async def throttle() -> None:
    import config as cfg

    global _last_request_at
    min_interval = float(cfg.config.get("figma_api_min_interval_sec", 2.5))
    async with _lock:
        if is_in_cooldown():
            raise FigmaRateLimitError(cooldown_remaining())
        now = time.time()
        wait = min_interval - (now - _last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at = time.time()
