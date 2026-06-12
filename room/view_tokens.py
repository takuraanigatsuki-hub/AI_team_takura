"""View-only токены для клиентского режима."""

import json
import os
import secrets
from datetime import datetime, timedelta

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "view_tokens.json")


def _load() -> list:
    if not os.path.exists(TOKENS_FILE):
        return []
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(tokens: list) -> None:
    os.makedirs(os.path.dirname(TOKENS_FILE), exist_ok=True)
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens[-20:], f, ensure_ascii=False, indent=2)


def create_token(hours: int = 72, label: str = "client") -> dict:
    token = secrets.token_urlsafe(24)
    entry = {
        "token": token,
        "label": label,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=hours)).isoformat(),
    }
    tokens = _load()
    tokens.append(entry)
    _save(tokens)
    return entry


def validate_token(token: str) -> bool:
    if not token:
        return False
    now = datetime.now()
    for t in _load():
        if t.get("token") == token:
            try:
                return now < datetime.fromisoformat(t["expires_at"])
            except Exception:
                return True
    return False
