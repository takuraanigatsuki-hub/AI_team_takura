"""Синхронизация knowledge/*.json и learning data на GitHub."""

import asyncio
import os
from datetime import datetime
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(PROJECT_ROOT, "knowledge")
LEARNING_STORE = os.path.join(PROJECT_ROOT, "data", "learning_projects.json")

_last_knowledge_mtime: Optional[float] = None
_pending = False


def _snapshot_mtime() -> float:
    latest = 0.0
    if os.path.isdir(KNOWLEDGE_DIR):
        for name in os.listdir(KNOWLEDGE_DIR):
            if not name.endswith(".json"):
                continue
            try:
                latest = max(latest, os.path.getmtime(os.path.join(KNOWLEDGE_DIR, name)))
            except OSError:
                pass
    if os.path.isfile(LEARNING_STORE):
        try:
            latest = max(latest, os.path.getmtime(LEARNING_STORE))
        except OSError:
            pass
    return latest


def mark_knowledge_dirty():
    global _pending
    _pending = True


def knowledge_changed() -> bool:
    global _last_knowledge_mtime, _pending
    if _pending:
        return True
    current = _snapshot_mtime()
    if _last_knowledge_mtime is None:
        _last_knowledge_mtime = current
        return False
    return current > _last_knowledge_mtime


async def sync_knowledge_to_github(room_manager=None) -> Optional[dict]:
    """Commit + push только если изменились knowledge/ или learning_projects."""
    import config as cfg_module
    from integrations.local_git_sync import sync_changes_async, has_local_changes

    global _last_knowledge_mtime, _pending

    if not cfg_module.config.get("git_auto_sync", True):
        return None
    if not knowledge_changed() and not has_local_changes():
        return None

    result = await sync_changes_async(
        f"auto: agent knowledge sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    _last_knowledge_mtime = _snapshot_mtime()
    _pending = False

    if room_manager and result.get("ok") and result.get("action") == "pushed":
        await room_manager.broadcast_work({
            "type": "knowledge_sync_done",
            "message": f"📚 Знания агентов → GitHub (`{result.get('commit')}`)",
            "commit_url": result.get("commit_url"),
            "timestamp": datetime.now().isoformat(),
        })
    return result


async def knowledge_sync_loop(room_manager=None, interval: int = 90):
    """Фон: выгрузка изученных знаний на сервер (git push)."""
    while True:
        await asyncio.sleep(max(45, interval))
        try:
            await sync_knowledge_to_github(room_manager)
        except Exception:
            pass
