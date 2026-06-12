"""Feature flags — включение функций по tier и глобально."""

from __future__ import annotations

import json
import os
from typing import Optional

FLAGS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "feature_flags.json")

DEFAULT_FLAGS = {
    "investor_portal": True,
    "security_agent": True,
    "cursor_auto_patch": True,
    "team_workspaces": True,
    "task_templates": True,
    "skill_matrix": True,
    "stripe_billing": False,
    "require_auth_mutations": True,
    "guest_readonly_ws": True,
    "honeypot_enabled": True,
}


def _load() -> dict:
    if not os.path.exists(FLAGS_FILE):
        return dict(DEFAULT_FLAGS)
    try:
        with open(FLAGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_FLAGS)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_FLAGS)


def _save(flags: dict) -> None:
    os.makedirs(os.path.dirname(FLAGS_FILE), exist_ok=True)
    with open(FLAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(flags, f, ensure_ascii=False, indent=2)


def get_flags() -> dict:
    return _load()


def is_enabled(name: str) -> bool:
    return bool(_load().get(name, DEFAULT_FLAGS.get(name, False)))


def set_flag(name: str, value: bool, admin_user: Optional[dict] = None) -> dict:
    flags = _load()
    flags[name] = bool(value)
    _save(flags)
    return flags
