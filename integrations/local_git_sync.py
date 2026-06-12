"""Локальный auto-commit + push в GitHub при изменениях проекта."""

import asyncio
import os
import subprocess
from datetime import datetime
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GIT_CANDIDATES = [
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files (x86)\Git\bin\git.exe",
    "git",
]

_last_sync_at: Optional[str] = None
_last_error: Optional[str] = None


def _find_git() -> str:
    for path in GIT_CANDIDATES:
        if path == "git" or os.path.isfile(path):
            return path
    return "git"


def _run_git(args: list, cwd: str = PROJECT_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_find_git()] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def get_status() -> dict:
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    remote = _run_git(["remote", "get-url", "origin"])
    porcelain = _run_git(["status", "--porcelain"])
    changed = [ln for ln in porcelain.stdout.splitlines() if ln.strip()]
    return {
        "branch": branch.stdout.strip() if branch.returncode == 0 else "unknown",
        "remote": remote.stdout.strip() if remote.returncode == 0 else "",
        "changed_files": len(changed),
        "files": changed[:30],
        "last_sync_at": _last_sync_at,
        "last_error": _last_error,
    }


def has_local_changes() -> bool:
    r = _run_git(["status", "--porcelain"])
    return bool(r.stdout.strip())


def sync_changes(message: Optional[str] = None) -> dict:
    """git add → commit → push. Без .env (в .gitignore)."""
    global _last_sync_at, _last_error

    if not has_local_changes():
        return {"ok": True, "action": "skip", "message": "Нет локальных изменений"}

    add = _run_git(["add", "-A"])
    if add.returncode != 0:
        _last_error = add.stderr.strip()
        return {"ok": False, "action": "add", "error": _last_error}

    commit_msg = message or (
        f"auto: project sync {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    commit = _run_git(["commit", "-m", commit_msg])
    if commit.returncode != 0:
        err = commit.stderr.strip()
        if "nothing to commit" in err.lower():
            return {"ok": True, "action": "skip", "message": "Nothing to commit"}
        _last_error = err
        return {"ok": False, "action": "commit", "error": _last_error}

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    branch_name = branch.stdout.strip() or "main"
    push = _run_git(["push", "origin", branch_name])
    if push.returncode != 0:
        _last_error = push.stderr.strip()
        return {
            "ok": False,
            "action": "push",
            "error": _last_error,
            "committed": True,
            "message": commit_msg,
        }

    _last_sync_at = datetime.now().isoformat()
    _last_error = None
    sha = _run_git(["rev-parse", "--short", "HEAD"])
    return {
        "ok": True,
        "action": "pushed",
        "message": commit_msg,
        "commit": sha.stdout.strip(),
        "branch": branch_name,
        "synced_at": _last_sync_at,
    }


async def sync_changes_async(message: Optional[str] = None) -> dict:
    return await asyncio.to_thread(sync_changes, message)


async def auto_sync_loop(room_manager=None, interval: int = 60):
    """Фоновый цикл: при изменениях — commit + push."""
    import config as cfg_module

    while True:
        await asyncio.sleep(max(30, interval))
        if not cfg_module.config.get("git_auto_sync", True):
            continue
        try:
            if not has_local_changes():
                continue
            result = await sync_changes_async()
            if result.get("ok") and result.get("action") == "pushed" and room_manager:
                await room_manager.broadcast_work({
                    "type": "git_sync_done",
                    "message": (
                        f"📤 **GitHub:** изменения отправлены\n"
                        f"• `{result.get('commit')}` · {result.get('branch')}\n"
                        f"• {result.get('message')}"
                    ),
                    "timestamp": datetime.now().isoformat(),
                })
        except Exception as e:
            _last_error = str(e)


async def sync_after_task(task_text: str, room_manager=None) -> Optional[dict]:
    """Синхронизация после задачи пользователя."""
    import config as cfg_module

    if not cfg_module.config.get("git_auto_sync", True):
        return None
    if not has_local_changes():
        return None

    preview = task_text[:80].replace("\n", " ")
    msg = f"auto: {preview}" if preview else None
    result = await sync_changes_async(msg)
    if room_manager and result.get("action") == "pushed":
        await room_manager.broadcast_work({
            "type": "git_sync_done",
            "message": (
                f"📤 Локальные изменения → GitHub (`{result.get('commit')}`)"
            ),
            "timestamp": datetime.now().isoformat(),
        })
        await room_manager.pipeline.on_github("done")
    return result
