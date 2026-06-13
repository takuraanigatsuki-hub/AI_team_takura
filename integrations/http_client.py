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
    return url or None


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

    # auto — явный прокси из .env, иначе прямое подключение (без сломанного system proxy)
    kw["trust_env"] = False
    if proxy:
        kw["proxy"] = proxy
    return kw


def async_client(timeout: float = 60.0, **extra) -> httpx.AsyncClient:
    return httpx.AsyncClient(**client_kwargs(timeout, **extra))


def describe_outbound() -> str:
    mode = proxy_mode()
    proxy = explicit_proxy()
    if mode == "proxy" or (mode == "auto" and proxy):
        return f"proxy ({proxy})"
    if mode == "system":
        return "system env (HTTP_PROXY)"
    return "direct"
