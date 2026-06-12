"""Опциональная auth (ROOM_API_KEY) + rate limit для API."""

import os
import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def _api_key() -> str:
    import config as cfg
    return (os.environ.get("ROOM_API_KEY") or cfg.config.get("room_api_key") or "").strip()


class AuthRateMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 40, window_sec: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_sec = window_sec
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _check_rate(self, client: str) -> bool:
        now = time.time()
        window_start = now - self.window_sec
        hits = [t for t in self._hits[client] if t > window_start]
        self._hits[client] = hits
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        if path.startswith("/api/task") and request.method == "POST":
            key = _api_key()
            if key:
                header = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                if header != key:
                    return JSONResponse({"detail": "Invalid API key"}, status_code=401)
            client = request.client.host if request.client else "unknown"
            if not self._check_rate(client):
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        return await call_next(request)
