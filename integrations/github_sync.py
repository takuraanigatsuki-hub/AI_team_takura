"""Синхронизация задач с GitHub через Cursor Cloud Agents."""

import os
from datetime import datetime
from typing import Any, Optional

from integrations.cursor_client import get_client, cursor_runs

# Активные cloud-агенты: agent_id -> метаданные для polling
active_cloud_agents: dict[str, dict] = {}


def _repo_from_item(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return (
            item.get("repository")
            or item.get("url")
            or item.get("html_url")
            or item.get("clone_url")
            or ""
        )
    return ""


async def resolve_repo_url() -> str:
    """URL репозитория: config → env → первый из Cursor API."""
    from config import config

    url = (
        config.get("cursor_repo_url")
        or os.environ.get("CURSOR_REPO_URL")
        or ""
    ).strip()
    if url:
        return url

    if not config.get("cursor_github_sync"):
        return ""

    client = get_client()
    repos = await client.list_repositories()
    for item in repos:
        candidate = _repo_from_item(item)
        if candidate and "github.com" in candidate:
            return candidate
    if repos:
        return _repo_from_item(repos[0])
    return ""


def _extract_pr_url(status: dict) -> str:
    for key in ("prUrl", "pr_url", "pullRequestUrl", "pull_request_url"):
        if status.get(key):
            return status[key]
    target = status.get("target") or {}
    for key in ("prUrl", "pr_url", "url"):
        if target.get(key):
            return target[key]
    return ""


def _extract_branch_url(status: dict) -> str:
    target = status.get("target") or {}
    return target.get("branchUrl") or target.get("branch_url") or target.get("url") or ""


def _build_sync_prompt(task_text: str, source: str = "user") -> str:
    return (
        "You are working in the connected GitHub repository.\n"
        f"Task source: {source}\n\n"
        f"Implement the following changes in the codebase, commit them, "
        f"and push to the repository:\n\n{task_text}\n\n"
        "Requirements:\n"
        "- Match existing project conventions\n"
        "- Do not commit secrets (.env, API keys)\n"
        "- Write clear commit messages\n"
    )


async def sync_task_to_github(
    task_text: str,
    room_manager=None,
    source: str = "AI Team Room",
) -> Optional[dict]:
    """
    Запускает Cursor Cloud Agent для синхронизации задачи с GitHub.
    Вызывается автоматически при cursor_github_sync=true.
    """
    from config import config

    if not config.get("cursor_github_sync"):
        return None
    if not config.get("cursor_enabled"):
        return None

    repo_url = await resolve_repo_url()
    if not repo_url:
        if room_manager:
            await room_manager.broadcast_work({
                "type": "system",
                "message": (
                    "⚠️ GitHub Sync: укажите репозиторий в Настройках → Cursor SDK "
                    "или подключите GitHub в Cursor Dashboard."
                ),
                "timestamp": datetime.now().isoformat(),
            })
        return None

    client = get_client()
    ref = config.get("cursor_repo_ref", "main")
    auto_pr = config.get("cursor_auto_create_pr", True)
    prompt = _build_sync_prompt(task_text, source)

    async def on_progress(msg: str):
        if room_manager:
            await room_manager.broadcast_work({
                "type": "cursor_progress",
                "agent_name": "Лео",
                "agent_emoji": "⚡",
                "message": msg,
                "timestamp": datetime.now().isoformat(),
            })

    run = await client.run_task(
        prompt=prompt,
        repo_url=repo_url,
        ref=ref,
        auto_create_pr=auto_pr,
        on_progress=on_progress,
        force_cloud=True,
    )

    agent_id = run.get("agent_id")
    if agent_id:
        active_cloud_agents[agent_id] = {
            "run_id": run.get("id"),
            "prompt": task_text[:500],
            "repo_url": repo_url,
            "started_at": run.get("started_at"),
        }

    if room_manager:
        pr_hint = " (PR будет создан автоматически)" if auto_pr else ""
        await room_manager.broadcast_work({
            "type": "github_sync_started",
            "run_id": run.get("id"),
            "agent_id": agent_id,
            "repo_url": repo_url,
            "agent_name": "Лео",
            "agent_emoji": "⚡",
            "message": (
                f"🔄 **GitHub Sync** → `{repo_url}`{pr_hint}\n"
                f"Cloud Agent: `{agent_id or 'запуск…'}`\n"
                f"Задача: {task_text[:300]}"
            ),
            "timestamp": datetime.now().isoformat(),
        })
        await room_manager.pipeline.on_github("started")

    return run


async def cloud_agent_poller(room_manager, interval: int = 20):
    """Фоновый опрос статуса cloud-агентов → PR-ссылки в чат."""
    import asyncio

    client = get_client()
    while True:
        await asyncio.sleep(interval)
        if not active_cloud_agents:
            continue
        for agent_id, info in list(active_cloud_agents.items()):
            try:
                status = await client.get_agent(agent_id)
                st = (status.get("status") or "").upper()
                pr_url = _extract_pr_url(status)
                branch_url = _extract_branch_url(status)

                if st in ("FINISHED", "COMPLETED", "DONE", "SUCCESS") or pr_url:
                    msg_parts = [f"✅ Cloud Agent `{agent_id}` завершён."]
                    if pr_url:
                        msg_parts.append(f"🔗 Pull Request: {pr_url}")
                    if branch_url:
                        msg_parts.append(f"🌿 Branch: {branch_url}")
                    msg_parts.append(
                        "Изменения на GitHub. Откройте Cursor Dashboard для деталей."
                    )
                    await room_manager.broadcast_work({
                        "type": "github_sync_done",
                        "agent_id": agent_id,
                        "run_id": info.get("run_id"),
                        "status": st or "done",
                        "pr_url": pr_url,
                        "branch_url": branch_url,
                        "agent_name": "Лео",
                        "agent_emoji": "⚡",
                        "message": "\n".join(msg_parts),
                        "timestamp": datetime.now().isoformat(),
                    })
                    await room_manager.pipeline.on_github("done")
                    active_cloud_agents.pop(agent_id, None)

                    run_id = info.get("run_id")
                    if run_id and run_id in cursor_runs:
                        cursor_runs[run_id]["status"] = "completed"
                        cursor_runs[run_id]["pr_url"] = pr_url
                        cursor_runs[run_id]["agent_status"] = status

                elif st in ("FAILED", "ERROR", "CANCELLED"):
                    await room_manager.broadcast_work({
                        "type": "error",
                        "message": f"❌ Cloud Agent `{agent_id}`: {st}",
                        "timestamp": datetime.now().isoformat(),
                    })
                    active_cloud_agents.pop(agent_id, None)

            except Exception:
                continue
