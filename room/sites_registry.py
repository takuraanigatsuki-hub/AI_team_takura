"""Реестр HTML-сайтов — привязка файлов к пользователям."""

import json
import os
from datetime import datetime
from typing import Optional

INDEX_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "sites_index.json")


def _ensure():
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)


def _load() -> list:
    _ensure()
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(items: list) -> None:
    _ensure()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(items[:500], f, ensure_ascii=False, indent=2)


def register(filename: str, *, user_id: str = "", title: str = "", task_id: str = "") -> dict:
    name = os.path.basename(filename)
    entry = {
        "id": name,
        "filename": name,
        "user_id": user_id or "",
        "task_id": task_id or "",
        "title": (title or name.replace(".html", "").replace("_", " "))[:120],
        "created_at": datetime.now().isoformat(),
    }
    items = [i for i in _load() if i.get("id") != name]
    items.insert(0, entry)
    _save(items)
    return entry


def list_for_user(user_id: str = "", privileged: bool = False, limit: int = 40) -> list:
    items = _load()
    if privileged:
        visible = items
    elif user_id:
        visible = [i for i in items if not i.get("user_id") or i.get("user_id") == user_id]
    else:
        visible = []
    return visible[:limit]


def _user_latest_rel(user_id: str) -> str:
    return f"users/{user_id.replace('/', '_')[:64]}/latest.html"


def latest_for_user(user_id: str = "", privileged: bool = False) -> Optional[dict]:
    items = list_for_user(user_id, privileged=privileged, limit=1)
    return items[0] if items else None


def delete_for_user(user_id: str, privileged: bool = False) -> int:
    """Удалить записи пользователя из реестра (файлы — отдельно)."""
    if not user_id and not privileged:
        return 0
    kept = []
    removed = 0
    for i in _load():
        if user_id and i.get("user_id") == user_id:
            removed += 1
            continue
        kept.append(i)
    if removed:
        _save(kept)
    return removed
