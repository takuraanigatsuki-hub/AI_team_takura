"""Timeline / Replay — журнал событий комнаты."""

import json
import os
from datetime import datetime
from typing import Optional

TIMELINE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "timeline.jsonl")
MAX_LINES = 2000


def _ensure():
    os.makedirs(os.path.dirname(TIMELINE_FILE), exist_ok=True)


def append_event(event: dict) -> None:
    _ensure()
    event.setdefault("recorded_at", datetime.now().isoformat())
    with open(TIMELINE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    _trim()


def _trim():
    if not os.path.exists(TIMELINE_FILE):
        return
    try:
        with open(TIMELINE_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > MAX_LINES:
            with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines[-MAX_LINES:])
    except Exception:
        pass


def get_events(limit: int = 100, since: Optional[str] = None) -> list:
    if not os.path.exists(TIMELINE_FILE):
        return []
    events = []
    try:
        with open(TIMELINE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if since and (ev.get("recorded_at") or "") < since:
                        continue
                    events.append(ev)
                except Exception:
                    continue
    except Exception:
        return []
    return events[-limit:]


def replay_summary(hours: float = 1.0) -> dict:
    from datetime import timedelta
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    events = get_events(limit=500, since=since)
    by_type = {}
    for e in events:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {"hours": hours, "total": len(events), "by_type": by_type, "events": events[-80:]}
