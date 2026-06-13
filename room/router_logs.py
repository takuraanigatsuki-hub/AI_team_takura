"""Логи маршрутизации задач — датасет для fine-tune router (Фаза C)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "router_logs")
LOG_FILE = os.path.join(LOG_DIR, "routes.jsonl")


def log_route(
    task_text: str,
    pm_assignments: dict,
    routed: dict,
    note: str,
    *,
    user_id: str = "",
    workspace_id: str = "",
    kind: str = "",
) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "task": (task_text or "")[:2000],
        "kind": kind,
        "pm_assignments": list((pm_assignments or {}).keys()),
        "routed": list((routed or {}).keys()),
        "router_note": note,
        "user_id": user_id,
        "workspace_id": workspace_id,
        "label": {
            "input_agents": pm_assignments,
            "output_agents": routed,
        },
    }
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_logs(limit: int = 100) -> list[dict]:
    if not os.path.exists(LOG_FILE):
        return []
    lines = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def export_finetune_jsonl(out_path: str = None, limit: int = 5000) -> str:
    """Экспорт в формат chat fine-tune (system/user/assistant)."""
    out_path = out_path or os.path.join(LOG_DIR, "finetune_export.jsonl")
    rows = list_logs(limit=limit)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            user = f"Задача: {r.get('task', '')}\nPM назначил: {r.get('pm_assignments', [])}"
            assistant = json.dumps(
                {"agents": r.get("routed", []), "reason": r.get("router_note", "")},
                ensure_ascii=False,
            )
            record = {
                "messages": [
                    {"role": "system", "content": "Ты router AI-команды. Ответь JSON: {\"agents\": [...], \"reason\": \"...\"}"},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                ]
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out_path
