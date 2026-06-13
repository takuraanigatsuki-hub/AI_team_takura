"""Device login и handoff-токены для десктоп-приложения."""

import json
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

DEVICES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "desktop_devices.json")
HANDOFF_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "desktop_handoff.json")

DEVICE_TTL_SEC = 600
HANDOFF_TTL_SEC = 120
POLL_INTERVAL_HINT = 2


def _load(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
    return {}


def _save(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _cleanup(store: dict, ttl_sec: int) -> dict:
    now = time.time()
    stale = [k for k, v in store.items() if now - float(v.get("created", 0)) > ttl_sec]
    for k in stale:
        store.pop(k, None)
    return store


def start_device_flow(base_url: str) -> dict:
    store = _cleanup(_load(DEVICES_FILE), DEVICE_TTL_SEC)
    device_id = secrets.token_urlsafe(24)
    user_code = "".join(secrets.choice("0123456789") for _ in range(6))
    poll_secret = secrets.token_urlsafe(32)
    now = time.time()
    store[device_id] = {
        "created": now,
        "expires": now + DEVICE_TTL_SEC,
        "user_code": user_code,
        "poll_secret": poll_secret,
        "status": "pending",
    }
    _save(DEVICES_FILE, store)
    verify_url = f"{base_url.rstrip('/')}/auth/device?id={device_id}&code={user_code}"
    return {
        "device_id": device_id,
        "user_code": user_code,
        "poll_secret": poll_secret,
        "verify_url": verify_url,
        "expires_in": DEVICE_TTL_SEC,
        "poll_interval": POLL_INTERVAL_HINT,
    }


def approve_device(device_id: str, session_token: str, user_id: str, user_code: str = "") -> bool:
    store = _cleanup(_load(DEVICES_FILE), DEVICE_TTL_SEC)
    entry = store.get(device_id)
    if not entry or entry.get("status") != "pending":
        return False
    if time.time() > float(entry.get("expires", 0)):
        entry["status"] = "expired"
        _save(DEVICES_FILE, store)
        return False
    if user_code and entry.get("user_code") != user_code:
        return False
    entry["status"] = "approved"
    entry["session_token"] = session_token
    entry["user_id"] = user_id
    entry["approved_at"] = time.time()
    _save(DEVICES_FILE, store)
    return True


def poll_device(device_id: str, poll_secret: str) -> dict:
    store = _cleanup(_load(DEVICES_FILE), DEVICE_TTL_SEC)
    entry = store.get(device_id)
    if not entry:
        return {"status": "expired"}
    stored_secret = entry.get("poll_secret") or ""
    if not poll_secret or not secrets.compare_digest(stored_secret, poll_secret):
        return {"status": "expired"}
    if time.time() > float(entry.get("expires", 0)):
        return {"status": "expired"}
    status = entry.get("status", "pending")
    if status == "approved":
        handoff = create_handoff(entry.get("session_token", ""), entry.get("user_id", ""))
        store.pop(device_id, None)
        _save(DEVICES_FILE, store)
        return {"status": "ok", "handoff_token": handoff}
    return {"status": "pending", "user_code": entry.get("user_code")}


def create_handoff(session_token: str, user_id: str) -> str:
    store = _cleanup(_load(HANDOFF_FILE), HANDOFF_TTL_SEC)
    token = secrets.token_urlsafe(32)
    store[token] = {
        "created": time.time(),
        "session_token": session_token,
        "user_id": user_id,
        "used": False,
    }
    _save(HANDOFF_FILE, store)
    return token


def consume_handoff(handoff_token: str) -> Optional[str]:
    store = _cleanup(_load(HANDOFF_FILE), HANDOFF_TTL_SEC)
    entry = store.get(handoff_token)
    if not entry or entry.get("used"):
        return None
    entry["used"] = True
    _save(HANDOFF_FILE, store)
    return entry.get("session_token")
