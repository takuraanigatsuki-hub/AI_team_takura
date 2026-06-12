"""Сохранение layout dashboard per user."""

from __future__ import annotations

import json
import os

LAYOUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "dashboard_layouts.json")

DEFAULT_WIDGETS = [
    "hero", "kpis", "integrations", "activity", "agents", "security", "actions",
]


def _load() -> dict:
    if not os.path.exists(LAYOUT_FILE):
        return {}
    try:
        with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(LAYOUT_FILE), exist_ok=True)
    with open(LAYOUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_layout(user_id: str = "") -> dict:
    key = user_id or "default"
    data = _load()
    entry = data.get(key, {})
    return {
        "widgets": entry.get("widgets", list(DEFAULT_WIDGETS)),
        "hidden": entry.get("hidden", []),
    }


def save_layout(user_id: str, widgets: list, hidden: list = None) -> dict:
    key = user_id or "default"
    data = _load()
    data[key] = {
        "widgets": widgets[:20],
        "hidden": hidden or [],
    }
    _save(data)
    return data[key]
