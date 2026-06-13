"""Единый httpx-клиент: VPN/proxy или прямое подключение к внешним API."""

from __future__ import annotations

import os
from typing import Optional

import httpx


def proxy_mode() -> str:
    import config as cfg
    raw = (
        os.environ.get("OUTBOUND_PROXY_MODE")
        or cfg.config.get("outbound_proxy_mode")
        or "auto"
    )
    return raw.strip().lower()


def explicit_proxy() -> Optional[str]:
    import config as cfg
    url = (
        os.environ.get("OUTBOUND_PROXY")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("HTTP_PROXY")
        or cfg.config.get("outbound_proxy")
        or ""
    ).strip()
    if url:
        return url
    # VFlex / Clash — mixed-port 7890 по умолчанию
    if os.environ.get("VFLEX_SUBSCRIPTION_URL") or cfg.config.get("vflex_subscription_url"):
        return "http://127.0.0.1:7890"
    return None


def _local_proxy_alive(proxy: str) -> bool:
    from urllib.parse import urlparse
    import socket
    p = urlparse(proxy)
    host = p.hostname or "127.0.0.1"
    port = p.port or 7890
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def client_kwargs(timeout: float = 60.0, **extra) -> dict:
    """Параметры для httpx.AsyncClient с учётом VPN/proxy."""
    mode = proxy_mode()
    proxy = explicit_proxy()
    kw: dict = {"timeout": timeout, **extra}

    if mode == "direct":
        kw["trust_env"] = False
        return kw

    if mode == "system":
        kw["trust_env"] = True
        return kw

    if mode == "proxy":
        kw["trust_env"] = False
        if proxy:
            kw["proxy"] = proxy
        return kw

    # auto — прокси только если VPN-клиент (7890) запущен, иначе напрямую
    kw["trust_env"] = False
    if proxy and _local_proxy_alive(proxy):
        kw["proxy"] = proxy
    return kw


def async_client(timeout: float = 60.0, **extra) -> httpx.AsyncClient:
    return httpx.AsyncClient(**client_kwargs(timeout, **extra))


def describe_outbound() -> str:
    mode = proxy_mode()
    proxy = explicit_proxy()
    if mode == "proxy" or (mode == "auto" and proxy and _local_proxy_alive(proxy)):
        return f"proxy ({proxy})"
    if mode == "auto" and proxy:
        return f"direct (VPN proxy {proxy} offline)"
    if mode == "system":
        return "system env (HTTP_PROXY)"
    return "direct"
