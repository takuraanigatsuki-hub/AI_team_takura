"""Telegram-уведомления Sonya Design Studio."""


def _enabled() -> bool:
    import config as cfg
    if cfg.config.get("telegram_notify_studio") is False:
        return False
    return bool(cfg.config.get("telegram_notify_tasks", False))


def _app_link(project_id: str = "") -> str:
    import config as cfg
    import os
    port = int(cfg.config.get("port", 8000))
    base_url = os.environ.get("APP_PUBLIC_URL") or f"http://localhost:{port}"
    base = f"{base_url}/app?view=sonya-studio"
    if project_id:
        return f"{base}&project={project_id}"
    return base


async def notify_studio(
    event: str,
    *,
    project_title: str = "",
    project_id: str = "",
    author: str = "",
    text: str = "",
    version_num: int = 0,
    open_comments: int = 0,
) -> None:
    if not _enabled():
        return
    try:
        from integrations.telegram_bot import notify_task
    except Exception:
        return

    link = _app_link(project_id)

    if event == "comment":
        msg = "\n".join([
            "💬 **Sonya Studio · новый комментарий**",
            f"Проект: {project_title}",
            f"От: {author}",
            f"«{text[:200]}»",
            f"Открытых: {open_comments}",
            f"→ {link}",
        ])
    elif event == "version":
        msg = "\n".join([
            "🔧 **Sonya Studio · новая версия**",
            f"«{project_title}» → v{version_num}",
            f"→ {link}",
        ])
    elif event == "published":
        msg = "\n".join([
            "📦 **Sonya Studio · опубликовано**",
            f"«{project_title}» v{version_num}",
            "Handoff готов (tokens + React)",
            f"→ {link}",
        ])
    elif event == "project":
        msg = "\n".join([
            "✨ **Sonya Studio · новый проект**",
            f"«{project_title}»",
            f"→ {link}",
        ])
    else:
        msg = f"🎨 Studio: {project_title}\n{link}"

    await notify_task(msg)
