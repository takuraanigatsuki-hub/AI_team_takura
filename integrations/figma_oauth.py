"""Figma OAuth 2 — подключение аккаунта пользователя."""

import base64
import json
import os
import secrets
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx

from config import config

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OAUTH_FILE = DATA_DIR / "figma_oauth.json"

FIGMA_AUTH_URL = "https://www.figma.com/oauth"
FIGMA_TOKEN_URL = "https://api.figma.com/v1/oauth/token"
FIGMA_REFRESH_URL = "https://api.figma.com/v1/oauth/refresh"
DEFAULT_SCOPES = "file_content:read,current_user:read"

_pending_states: dict[str, float] = {}


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)


def get_redirect_uri() -> str:
    uri = (os.environ.get("FIGMA_REDIRECT_URI") or config.get("figma_redirect_uri") or "").strip()
    if uri:
        return uri
    port = int(config.get("port", 8000))
    return f"http://localhost:{port}/api/figma/callback"


def get_client_credentials() -> tuple[str, str]:
    cid = (os.environ.get("FIGMA_CLIENT_ID") or config.get("figma_client_id") or "").strip()
    secret = (os.environ.get("FIGMA_CLIENT_SECRET") or config.get("figma_client_secret") or "").strip()
    return cid, secret


def oauth_app_configured() -> bool:
    cid, secret = get_client_credentials()
    return bool(cid and secret)


def load_token_store() -> dict:
    _ensure_data_dir()
    if not OAUTH_FILE.exists():
        return {}
    try:
        with open(OAUTH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_token_store(data: dict) -> None:
    _ensure_data_dir()
    with open(OAUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clear_token_store() -> None:
    if OAUTH_FILE.exists():
        OAUTH_FILE.unlink()


def _basic_auth_header() -> str:
    cid, secret = get_client_credentials()
    return "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode()


def _cleanup_states() -> None:
    now = time.time()
    expired = [k for k, exp in _pending_states.items() if exp <= now]
    for k in expired:
        _pending_states.pop(k, None)


def build_auth_url() -> str:
    cid, _ = get_client_credentials()
    if not cid:
        raise ValueError("FIGMA_CLIENT_ID не задан")

    _cleanup_states()
    state = secrets.token_urlsafe(32)
    _pending_states[state] = time.time() + 600

    store = load_token_store()
    store["_pending_state"] = {"state": state, "expires": _pending_states[state]}
    save_token_store(store)

    params = {
        "client_id": cid,
        "redirect_uri": get_redirect_uri(),
        "scope": DEFAULT_SCOPES,
        "state": state,
        "response_type": "code",
    }
    return f"{FIGMA_AUTH_URL}?{urlencode(params)}"


def verify_state(state: str) -> bool:
    _cleanup_states()
    exp = _pending_states.pop(state, None)
    if exp and exp > time.time():
        return True

    store = load_token_store()
    pending = store.pop("_pending_state", None)
    if pending:
        save_token_store(store)
    if pending and pending.get("state") == state and pending.get("expires", 0) > time.time():
        return True
    return False


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            FIGMA_TOKEN_URL,
            headers={
                "Authorization": _basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "redirect_uri": get_redirect_uri(),
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Figma OAuth {resp.status_code}: {resp.text[:400]}")
        return resp.json()


async def refresh_tokens(refresh_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            FIGMA_REFRESH_URL,
            headers={
                "Authorization": _basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"refresh_token": refresh_token},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Figma refresh {resp.status_code}: {resp.text[:400]}")
        return resp.json()


async def fetch_me(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            "https://api.figma.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            return {}
        return resp.json()


async def complete_oauth(code: str) -> dict:
    token_data = await exchange_code(code)
    access_token = token_data["access_token"]
    me = await fetch_me(access_token)
    store = {
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token"),
        "expires_at": time.time() + int(token_data.get("expires_in", 7776000)),
        "user_id": token_data.get("user_id_string") or token_data.get("user_id"),
        "user_email": me.get("email"),
        "user_handle": me.get("handle"),
        "user_name": me.get("handle") or me.get("email") or "Figma User",
        "connected_at": time.time(),
    }
    save_token_store(store)
    return store


async def ensure_valid_oauth_token() -> Optional[str]:
    store = load_token_store()
    token = store.get("access_token")
    if not token:
        return None

    expires_at = float(store.get("expires_at") or 0)
    if expires_at - time.time() > 300:
        return token

    refresh = store.get("refresh_token")
    if not refresh:
        return token

    try:
        data = await refresh_tokens(refresh)
        store["access_token"] = data["access_token"]
        store["expires_at"] = time.time() + int(data.get("expires_in", 7776000))
        save_token_store(store)
        return store["access_token"]
    except Exception:
        return None


def is_figma_connected() -> bool:
    if load_token_store().get("access_token"):
        return True
    return bool(config.get("figma_access_token"))


async def get_connection_status() -> dict:
    store = load_token_store()
    oauth_token = store.get("access_token")
    pat = config.get("figma_access_token", "")

    status = {
        "oauth_app_configured": oauth_app_configured(),
        "redirect_uri": get_redirect_uri(),
        "connected": bool(oauth_token or pat),
        "auth_method": "oauth" if oauth_token else ("pat" if pat else None),
        "user_name": store.get("user_name"),
        "user_email": store.get("user_email"),
        "user_handle": store.get("user_handle"),
        "expires_at": store.get("expires_at"),
        "has_pat_fallback": bool(pat),
    }

    if oauth_token:
        try:
            me = await fetch_me(oauth_token)
            if me:
                status["user_email"] = me.get("email") or status.get("user_email")
                status["user_handle"] = me.get("handle") or status.get("user_handle")
                status["user_name"] = me.get("handle") or me.get("email") or status.get("user_name")
        except Exception:
            pass

    return status
