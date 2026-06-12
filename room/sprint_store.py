"""Sprint-режим — цель, backlog, burndown."""

import json
import os
from datetime import datetime, timedelta

SPRINT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "sprint.json")


def _load() -> dict:
    if not os.path.exists(SPRINT_FILE):
        return {"active": False, "name": "", "goal": "", "started_at": None, "ends_at": None, "backlog": []}
    try:
        with open(SPRINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"active": False, "name": "", "goal": "", "started_at": None, "ends_at": None, "backlog": []}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(SPRINT_FILE), exist_ok=True)
    with open(SPRINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_sprint() -> dict:
    data = _load()
    if data.get("active") and data.get("ends_at"):
        try:
            end = datetime.fromisoformat(data["ends_at"])
            data["days_left"] = max(0, (end - datetime.now()).days)
        except Exception:
            data["days_left"] = 0
    backlog = data.get("backlog", [])
    data["stats"] = {
        "total": len(backlog),
        "done": sum(1 for b in backlog if b.get("done")),
        "todo": sum(1 for b in backlog if not b.get("done")),
    }
    return data


def start_sprint(name: str, goal: str, days: int = 7) -> dict:
    now = datetime.now()
    data = {
        "active": True,
        "name": name[:100],
        "goal": goal[:500],
        "started_at": now.isoformat(),
        "ends_at": (now + timedelta(days=max(1, days))).isoformat(),
        "backlog": [],
    }
    _save(data)
    return data


def add_backlog_item(text: str, priority: str = "medium") -> dict:
    data = _load()
    item = {
        "id": f"sp-{len(data.get('backlog', [])) + 1}",
        "text": text[:300],
        "priority": priority if priority in ("urgent", "high", "medium", "low") else "medium",
        "done": False,
        "created_at": datetime.now().isoformat(),
    }
    data.setdefault("backlog", []).append(item)
    _save(data)
    return item


def toggle_backlog(item_id: str, done: bool = None) -> dict:
    data = _load()
    for item in data.get("backlog", []):
        if item.get("id") == item_id:
            item["done"] = done if done is not None else not item.get("done")
            _save(data)
            return item
    return {}


def end_sprint() -> dict:
    data = _load()
    data["active"] = False
    _save(data)
    return data
