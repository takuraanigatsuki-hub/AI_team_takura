"""Создание PR / commit из артефакта."""

import os


async def create_pr_from_artifact(artifact: dict, room_manager=None) -> dict:
    from integrations.local_git_sync import sync_changes_async, has_local_changes, PROJECT_ROOT

    agent_id = artifact.get("agent_id", "cursor")
    art_type = artifact.get("type", "code")
    title = artifact.get("title", "Artifact update")[:80]
    files = artifact.get("files") or {}

    written = []
    if files:
        out_dir = os.path.join(PROJECT_ROOT, "output", "artifacts", artifact.get("id", "latest"))
        os.makedirs(out_dir, exist_ok=True)
        for fname, content in files.items():
            safe = fname.replace("..", "").replace("/", "_")
            path = os.path.join(out_dir, safe)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content if isinstance(content, str) else str(content))
            written.append(path)

    if artifact.get("preview_html"):
        html_path = os.path.join(PROJECT_ROOT, "output", "artifacts", artifact.get("id", "latest"), "preview.html")
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(artifact["preview_html"])
        written.append(html_path)

    msg = f"feat({agent_id}): {title} [{art_type}]"
    result = {"ok": True, "message": msg, "files_written": len(written)}

    if has_local_changes():
        sync_result = await sync_changes_async(msg)
        result["git"] = sync_result
        if room_manager and sync_result.get("commit_url"):
            await room_manager.broadcast_work({
                "type": "pr_ready",
                "message": f"📦 Артефакт → GitHub: {sync_result.get('commit_url')}",
                "commit_url": sync_result.get("commit_url"),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            })
    else:
        result["git"] = {"action": "skip", "message": "Файлы сохранены в output/artifacts/"}

    return result
