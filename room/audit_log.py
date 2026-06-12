"""Audit log — действия пользователей и события безопасности."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Optional

AUDIT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "audit_log.json")
MAX_ENTRIES = 2000


def _load() -> list:
    if not os.path.exists(AUDIT_FILE):
        return []
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(entries: list) -> None:
    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(entries[-MAX_ENTRIES:], f, ensure_ascii=False, indent=2)


def log_event(
    action: str,
    *,
    user_id: str = "",
    user_email: str = "",
    ip: str = "",
    path: str = "",
    detail: str = "",
    severity: str = "info",
    meta: Optional[dict] = None,
) -> dict:
    entry = {
        "id": str(uuid.uuid4())[:12],
        "action": action,
        "user_id": user_id,
        "user_email": user_email,
        "ip": ip,
        "path": path,
        "detail": (detail or "")[:500],
        "severity": severity,
        "meta": meta or {},
        "timestamp": datetime.now().isoformat(),
    }
    entries = _load()
    entries.append(entry)
    _save(entries)
    return entry


def get_recent(limit: int = 100, severity: str = "") -> list:
    entries = _load()
    if severity:
        entries = [e for e in entries if e.get("severity") == severity]
    return list(reversed(entries[-limit:]))


def stats() -> dict:
    entries = _load()
    last_24h = []
    now = datetime.now()
    for e in entries[-500:]:
        try:
            ts = datetime.fromisoformat(e.get("timestamp", ""))
            if (now - ts).total_seconds() < 86400:
                last_24h.append(e)
        except Exception:
            pass
    by_severity = {}
    for e in last_24h:
        s = e.get("severity", "info")
        by_severity[s] = by_severity.get(s, 0) + 1
    return {
        "total": len(entries),
        "last_24h": len(last_24h),
        "by_severity": by_severity,
    }
