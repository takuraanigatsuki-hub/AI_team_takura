"""Глобальная память проекта — контекст для всех агентов."""

import json
import os
from datetime import datetime

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "project_memory.json")


def _load() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {"brief": "", "goals": [], "constraints": [], "updated_at": None}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"brief": "", "goals": [], "constraints": [], "updated_at": None}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    data["updated_at"] = datetime.now().isoformat()
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_memory() -> dict:
    return _load()


def set_memory(brief: str = None, goals: list = None, constraints: list = None) -> dict:
    data = _load()
    if brief is not None:
        data["brief"] = brief.strip()[:2000]
    if goals is not None:
        data["goals"] = [g.strip()[:200] for g in goals if g.strip()][:20]
    if constraints is not None:
        data["constraints"] = [c.strip()[:200] for c in constraints if c.strip()][:20]
    _save(data)
    return data


def context_for_prompt() -> str:
    data = _load()
    if not data.get("brief") and not data.get("goals"):
        return ""
    lines = ["Контекст проекта и пожелания пользователя:"]
    if data.get("brief"):
        lines.append(f"Brief: {data['brief']}")
    if data.get("goals"):
        lines.append("Запросы пользователя (приоритет):")
        for g in data["goals"][:6]:
            lines.append(f"  • {g}")
    if data.get("constraints"):
        lines.append("Ограничения: " + "; ".join(data["constraints"][:5]))
    return "\n".join(lines)
