"""In-app уведомления."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Optional

NOTIF_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "notifications.json")
MAX = 500


def _load() -> list:
    if not os.path.exists(NOTIF_FILE):
        return []
    try:
        with open(NOTIF_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(items: list) -> None:
    os.makedirs(os.path.dirname(NOTIF_FILE), exist_ok=True)
    with open(NOTIF_FILE, "w", encoding="utf-8") as f:
        json.dump(items[-MAX:], f, ensure_ascii=False, indent=2)


def push(
    title: str,
    body: str = "",
    *,
    user_id: str = "",
    ntype: str = "info",
    link: str = "",
) -> dict:
    item = {
        "id": str(uuid.uuid4())[:10],
        "title": title[:120],
        "body": (body or "")[:400],
        "user_id": user_id,
        "type": ntype,
        "link": link,
        "read": False,
        "created_at": datetime.now().isoformat(),
    }
    items = _load()
    items.append(item)
    _save(items)
    return item


def list_for_user(user_id: str, limit: int = 40) -> list:
    items = _load()
    if user_id:
        filtered = [n for n in items if not n.get("user_id") or n.get("user_id") == user_id]
    else:
        filtered = [n for n in items if not n.get("user_id")]
    return list(reversed(filtered[-limit:]))


def mark_read(notif_id: str, user_id: str = "") -> bool:
    items = _load()
    for n in items:
        if n.get("id") == notif_id:
            if user_id and n.get("user_id") and n.get("user_id") != user_id:
                return False
            n["read"] = True
            _save(items)
            return True
    return False


def unread_count(user_id: str) -> int:
    return sum(1 for n in list_for_user(user_id, 100) if not n.get("read"))
