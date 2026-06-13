"""Командные workspace — изолированные комнаты."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Optional

WS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "workspaces.json")


def _load() -> list:
    if not os.path.exists(WS_FILE):
        return []
    try:
        with open(WS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(workspaces: list) -> None:
    os.makedirs(os.path.dirname(WS_FILE), exist_ok=True)
    with open(WS_FILE, "w", encoding="utf-8") as f:
        json.dump(workspaces[-50:], f, ensure_ascii=False, indent=2)


def list_for_user(user_id: str) -> list:
    return [
        w for w in _load()
        if user_id in (w.get("member_ids") or []) or w.get("owner_id") == user_id
    ]


def create(name: str, owner_id: str, description: str = "") -> dict:
    ws = {
        "id": str(uuid.uuid4())[:10],
        "name": (name or "Workspace")[:80],
        "description": (description or "")[:300],
        "owner_id": owner_id,
        "member_ids": [owner_id],
        "created_at": datetime.now().isoformat(),
    }
    workspaces = _load()
    workspaces.insert(0, ws)
    _save(workspaces)
    try:
        from integrations.rag.workspace_store import ensure_workspace_store
        ensure_workspace_store(ws["id"], seed_from_global=True)
    except Exception:
        pass
    return ws


def add_member(workspace_id: str, user_id: str) -> Optional[dict]:
    workspaces = _load()
    for w in workspaces:
        if w.get("id") == workspace_id:
            members = w.setdefault("member_ids", [])
            if user_id not in members:
                members.append(user_id)
            _save(workspaces)
            return w
    return None


def set_active(user_id: str, workspace_id: str) -> None:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "active_workspaces.json")
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data[user_id] = workspace_id
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_active(user_id: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "active_workspaces.json")
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get(user_id, "")
    except Exception:
        return ""
