"""Sprint-режим — цель, backlog, burndown (per-user)."""

import json
import os
import uuid
from datetime import datetime, timedelta

SPRINT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sprints")


def _path(user_id: str = "") -> str:
    os.makedirs(SPRINT_DIR, exist_ok=True)
    key = (user_id or "guest").replace("/", "_")[:64]
    return os.path.join(SPRINT_DIR, f"{key}.json")


def _empty() -> dict:
    return {"active": False, "name": "", "goal": "", "started_at": None, "ends_at": None, "backlog": []}


def _load(user_id: str = "") -> dict:
    path = _path(user_id)
    if not os.path.exists(path):
        return _empty()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _empty()


def _save(data: dict, user_id: str = "") -> None:
    with open(_path(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_sprint(user_id: str = "") -> dict:
    data = _load(user_id)
    if data.get("active") and data.get("ends_at"):
        try:
            end = datetime.fromisoformat(data["ends_at"])
            data["days_left"] = max(0, (end - datetime.now()).days)
        except Exception:
            data["days_left"] = 0
    backlog = data.get("backlog", [])
    done = sum(1 for b in backlog if b.get("done"))
    total = len(backlog)
    data["stats"] = {"total": total, "done": done, "todo": total - done}
    data["progress_pct"] = round(100 * done / total) if total else 0
    return data


def start_sprint(name: str, goal: str, days: int = 7, user_id: str = "") -> dict:
    now = datetime.now()
    data = {
        "active": True,
        "name": name[:100],
        "goal": goal[:500],
        "started_at": now.isoformat(),
        "ends_at": (now + timedelta(days=max(1, days))).isoformat(),
        "backlog": [],
        "user_id": user_id,
    }
    _save(data, user_id)
    return data


def add_backlog_item(text: str, priority: str = "medium", user_id: str = "") -> dict:
    data = _load(user_id)
    item = {
        "id": str(uuid.uuid4())[:8],
        "text": text[:300],
        "priority": priority if priority in ("urgent", "high", "medium", "low") else "medium",
        "done": False,
        "created_at": datetime.now().isoformat(),
    }
    data.setdefault("backlog", []).append(item)
    _save(data, user_id)
    return item


def toggle_backlog(item_id: str, done: bool = None, user_id: str = "") -> dict:
    data = _load(user_id)
    for item in data.get("backlog", []):
        if item.get("id") == item_id:
            item["done"] = done if done is not None else not item.get("done")
            _save(data, user_id)
            return item
    return {}


def end_sprint(user_id: str = "") -> dict:
    data = _load(user_id)
    data["active"] = False
    _save(data, user_id)
    return data
