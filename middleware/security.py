"""Security middleware: headers, rate limit, threat detection, auth на мутациях."""

from __future__ import annotations

import os
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from room.audit_log import log_event
from room.feature_flags import is_enabled
from room.security_monitor import get_monitor

SESSION_COOKIE = "ai_team_session"

PUBLIC_WRITE = frozenset({
    "/api/auth/register",
    "/api/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/telegram/webhook",
    "/api/billing/stripe/webhook",
})

PUBLIC_GET = frozenset({
    "/api/auth/me",
    "/api/subscription/plans",
    "/api/agents",
    "/api/chat/commands",
    "/api/learning/masha-lab",
    "/api/investor/dashboard",
    "/api/task-templates",
    "/api/feature-flags",
    "/openapi.json",
    "/docs",
    "/redoc",
})

INVESTOR_ALLOWED_PREFIX = (
    "/api/investor/",
    "/api/auth/",
    "/api/agents",
    "/api/tasks",
    "/api/projects",
)

ADMIN_PREFIX = "/api/admin/"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_user(request: Request):
    try:
        from room.user_auth import get_user_from_token
        token = request.cookies.get(SESSION_COOKIE, "")
        return get_user_from_token(token) if token else None
    except Exception:
        return None


def _api_key_ok(request: Request) -> bool:
    import config as cfg
    key = (os.environ.get("ROOM_API_KEY") or cfg.config.get("room_api_key") or "").strip()
    if not key:
        return False
    header = (
        request.headers.get("X-API-Key")
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    return header == key


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method
        ip = _client_ip(request)
        monitor = get_monitor()

        if monitor.is_blocked(ip):
            return JSONResponse({"detail": "Access denied"}, status_code=403)

        if is_enabled("honeypot_enabled") and monitor.is_honeypot(path):
            monitor.record_threat(
                ip=ip, path=path, threat_type="honeypot",
                detail="Honeypot access", severity="critical",
            )
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        if path.startswith("/api/"):
            if not monitor.check_rate(ip, max_req=150, window=60):
                monitor.record_threat(
                    ip=ip, path=path, threat_type="rate_limit",
                    detail="API rate limit", severity="medium",
                )
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)

            query = str(request.url.query or "")
            monitor.scan_payload(f"{path}?{query}", ip=ip, path=path)

            if method in ("POST", "PATCH", "PUT", "DELETE") and is_enabled("require_auth_mutations"):
                if path.startswith("/api/v1/"):
                    pass  # JWT auth handled by api.deps in route dependencies
                elif path not in PUBLIC_WRITE and not _api_key_ok(request):
                    user = _get_user(request)
                    if not user:
                        log_event("auth_denied", ip=ip, path=path, severity="warn")
                        return JSONResponse({"detail": "Authentication required"}, status_code=401)
                    role = user.get("role", "member")
                    if role == "investor":
                        allowed = any(path.startswith(p) for p in INVESTOR_ALLOWED_PREFIX)
                        if not allowed or path.startswith(ADMIN_PREFIX):
                            return JSONResponse({"detail": "Investor read-only"}, status_code=403)

            if method == "GET" and path.startswith("/api/admin/"):
                user = _get_user(request)
                if not user:
                    return JSONResponse({"detail": "Authentication required"}, status_code=401)
                from room.user_auth import has_privilege
                if not has_privilege(user, "admin") and user.get("role") not in ("owner", "admin", "tech_admin"):
                    return JSONResponse({"detail": "Forbidden"}, status_code=403)

        response = await call_next(request)

        if path.startswith("/api/") or path.startswith("/static/"):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
            if path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-store"

        if response.status_code == 404 and path.startswith("/api/"):
            ev = monitor.record_404(ip, path)
            if ev and is_enabled("security_agent"):
                request.state.security_event = ev

        return response
