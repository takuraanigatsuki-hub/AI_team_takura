"""Sonya Design Studio — проекты, версии, комментарии (без Figma API при создании)."""

import json
import os
import re
import uuid
from datetime import datetime
from typing import Optional

from agents.react_preview import generate_react_preview

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sonya_studio")
STORE_FILE = os.path.join(DATA_DIR, "projects.json")

PROJECT_THEMES = [
    ("landing", "Landing page для SaaS"),
    ("dashboard", "Analytics Dashboard"),
    ("mobile", "Mobile onboarding"),
    ("ecommerce", "E-commerce карточка"),
    ("design_system", "Design System UI Kit"),
    ("portfolio", "Creative Portfolio"),
]

_THEME_LABELS = dict(PROJECT_THEMES)

_GENERIC_LANDING = re.compile(
    r"^(?:сделай\s+)?(?:landing|лендинг)\s*(?:page\s+)?(?:для\s+)?(?:моего\s+)?(?:продукт|product)",
    re.I,
)


def _theme_title(theme_id: str) -> str:
    return _THEME_LABELS.get(theme_id, theme_id or "UI проект")


def _resolve_project_title(*, title: str, task: str, theme: str) -> str:
    from integrations.sonya_commands import title_from_task

    theme_label = _theme_title(theme)
    derived = title_from_task(task, "")
    clean = (title or "").strip()
    if clean and clean.lower() not in ("page для моего продукта", "ui проект", "новый проект"):
        return clean[:80]
    if derived and not _GENERIC_LANDING.search(task or ""):
        return derived[:80]
    if theme_label:
        return theme_label[:80]
    return derived or "UI проект"


def _augment_task_for_theme(task: str, theme_id: str, theme_title: str, color_hint: str) -> str:
    base = (task or "").strip()
    if not base:
        return (
            f"{theme_title}. Собственный проект Sonya Studio. "
            f"Палитра: {color_hint}. Современный UI, React компонент."
        )
    if _GENERIC_LANDING.search(base) and theme_title:
        return (
            f"{theme_title}. {base} "
            f"Уникальный дизайн, палитра: {color_hint}. Адаптивная вёрстка."
        )
    return base


async def _generate_studio_preview(task: str, *, theme: str = "", colors: Optional[list] = None) -> dict:
    hints = {}
    theme_title = _theme_title(theme)
    if theme_title:
        hints["prompt_extra"] = (
            f"Категория UI: {theme_title}. "
            "Сделай уникальный результат под задачу — не копируй generic шаблон MySite."
        )
    try:
        from integrations.llm_client import is_configured
        if is_configured():
            from integrations.llm_codegen import generate_react_from_llm
            preview = await generate_react_from_llm(task, hints)
            code = preview.get("code") or ""
            if code and "function App" in code:
                if colors:
                    primary = colors[0]
                    for old in ("#4f7df3", "#6c63ff", "#667eea"):
                        code = code.replace(old, primary)
                    preview = {**preview, "code": code}
                if not preview.get("title") or preview.get("title") == task[:60]:
                    preview["title"] = _headline_from_preview_task(task, theme)
                return preview
    except Exception:
        pass
    preview = generate_react_preview(task, theme=theme, colors=colors)
    if not preview.get("title"):
        preview["title"] = _headline_from_preview_task(task, theme)
    return preview


def _headline_from_preview_task(task: str, theme: str = "") -> str:
    from integrations.sonya_commands import title_from_task
    title = title_from_task(task, "")
    if title and not _GENERIC_LANDING.search(task or ""):
        return title
    return _theme_title(theme) or title or "UI проект"


def _now() -> str:
    return datetime.now().isoformat()


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_store() -> dict:
    _ensure_dir()
    if not os.path.exists(STORE_FILE):
        return {"projects": []}
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "projects" in data:
            return data
    except Exception:
        pass
    return {"projects": []}


def _save_store(data: dict) -> None:
    _ensure_dir()
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find_project(store: dict, project_id: str) -> Optional[dict]:
    for p in store.get("projects", []):
        if p.get("id") == project_id:
            return p
    return None


def _version_public(v: dict, *, include_code: bool = False) -> dict:
    if not v:
        return {}
    out = {
        "id": v["id"],
        "version_num": v.get("version_num", 1),
        "title": v.get("title", ""),
        "task": v.get("task", ""),
        "colors": v.get("colors", []),
        "created_at": v.get("created_at"),
        "created_by": v.get("created_by", "sonya"),
    }
    if include_code:
        out["react_code"] = v.get("react_code", "")
    return out


def _project_origin(p: dict) -> str:
    origin = p.get("origin") or ""
    if origin in ("sonya_auto", "user"):
        return origin
    versions = p.get("versions") or []
    first_by = (versions[0].get("created_by") if versions else "") or ""
    if first_by == "sonya" or (p.get("description") or "").startswith("Проект Sonya Studio"):
        return "sonya_auto"
    return "user"


def _public_project(p: dict, *, include_versions: bool = True, include_react_code: bool = False) -> dict:
    versions = p.get("versions", [])
    current = next((v for v in versions if v.get("id") == p.get("current_version_id")), None)
    if not current and versions:
        current = versions[-1]
    out = {
        "id": p["id"],
        "title": p.get("title", "Проект"),
        "description": p.get("description", ""),
        "status": p.get("status", "draft"),
        "theme": p.get("theme", ""),
        "frame_id": p.get("frame_id", "main"),
        "colors": p.get("colors", []),
        "created_at": p.get("created_at"),
        "updated_at": p.get("updated_at"),
        "published_at": p.get("published_at"),
        "figma_handoff": p.get("figma_handoff"),
        "version_count": len(versions),
        "open_comments": sum(1 for c in p.get("comments", []) if c.get("status") == "open"),
        "origin": _project_origin(p),
        "current_version": _version_public(current, include_code=include_react_code) if current else None,
    }
    if include_versions:
        out["versions"] = [_version_public(v, include_code=False) for v in versions]
        out["comments"] = p.get("comments", [])
    return out


def list_projects(scope: str = "all") -> list:
    store = _load_store()
    items = sorted(store.get("projects", []), key=lambda x: x.get("updated_at", ""), reverse=True)
    if scope == "studio":
        items = [p for p in items if _project_origin(p) == "user"]
    elif scope in ("learning", "sonya_auto"):
        items = [p for p in items if _project_origin(p) == "sonya_auto"]
    return [_public_project(p, include_versions=False) for p in items]


def cleanup_projects(scope: str = "studio", *, keep_published: bool = True) -> dict:
    """scope=studio — черновики пользователя; scope=learning — авто-проекты Сони."""
    store = _load_store()
    removed: list[str] = []
    kept: list[dict] = []
    for p in store.get("projects", []):
        origin = _project_origin(p)
        status = p.get("status", "draft")
        drop = False
        if scope == "studio" and origin == "user" and status == "draft":
            drop = True
        elif scope == "learning" and origin == "sonya_auto":
            if not keep_published or status != "published":
                drop = True
        elif scope == "all-auto" and origin == "sonya_auto":
            drop = True
        if drop:
            removed.append(p.get("id", ""))
        else:
            kept.append(p)
    store["projects"] = kept
    _save_store(store)
    return {"removed": len(removed), "removed_ids": removed, "remaining": len(kept)}


def get_project(project_id: str) -> Optional[dict]:
    store = _load_store()
    p = _find_project(store, project_id)
    return _public_project(p, include_react_code=True) if p else None


def create_project(
    *,
    title: str,
    description: str = "",
    task: str = "",
    theme: str = "",
    react_code: str = "",
    preview_title: str = "",
    colors: Optional[list] = None,
    created_by: str = "sonya",
    origin: str = "",
) -> dict:
    store = _load_store()
    if not task and not react_code:
        import random
        theme_id, theme_title = random.choice(PROJECT_THEMES)
        theme = theme or theme_id
        title = _resolve_project_title(title=title, task="", theme=theme) or theme_title
        task = f"{theme_title}. Современный UI, адаптивная вёрстка, палитра команды."
        colors = colors or ["#6c63ff", "#5ecf8a", "#1a1d2e", "#f0f0f5", "#c792ea"]
        preview = generate_react_preview(task, theme=theme, colors=colors)
        react_code = preview.get("code", "")
        preview_title = preview.get("title", title)
    elif not react_code:
        title = _resolve_project_title(title=title, task=task, theme=theme) or title or "UI проект"
        colors = colors or ["#6c63ff", "#5ecf8a", "#1a1d2e", "#f0f0f5"]
        preview = generate_react_preview(task, theme=theme, colors=colors)
        react_code = preview.get("code", "")
        preview_title = preview_title or preview.get("title", title)
    else:
        title = _resolve_project_title(title=title, task=task, theme=theme) or title or "UI проект"

    pid = _uid("proj-")
    vid = _uid("ver-")
    ts = _now()
    version = {
        "id": vid,
        "version_num": 1,
        "title": preview_title or title,
        "task": task,
        "react_code": react_code,
        "colors": colors or [],
        "created_at": ts,
        "created_by": created_by,
    }
    project = {
        "id": pid,
        "title": title,
        "description": description,
        "status": "draft",
        "theme": theme,
        "frame_id": "main",
        "colors": colors or [],
        "created_at": ts,
        "updated_at": ts,
        "published_at": None,
        "figma_handoff": None,
        "current_version_id": vid,
        "versions": [version],
        "comments": [],
        "origin": origin or ("sonya_auto" if created_by == "sonya" else "user"),
    }
    store.setdefault("projects", []).insert(0, project)
    _save_store(store)
    return _public_project(project, include_react_code=True)


def add_version(
    project_id: str,
    *,
    task: str,
    react_code: str = "",
    preview_title: str = "",
    colors: Optional[list] = None,
    created_by: str = "sonya",
) -> Optional[dict]:
    store = _load_store()
    p = _find_project(store, project_id)
    if not p:
        return None

    if not react_code:
        preview = generate_react_preview(task, theme=p.get("theme", ""), colors=p.get("colors"))
        react_code = preview.get("code", "")
        preview_title = preview_title or preview.get("title", p.get("title", "UI"))
        colors = colors or p.get("colors", [])

    vid = _uid("ver-")
    num = len(p.get("versions", [])) + 1
    ts = _now()
    version = {
        "id": vid,
        "version_num": num,
        "title": preview_title,
        "task": task,
        "react_code": react_code,
        "colors": colors or p.get("colors", []),
        "created_at": ts,
        "created_by": created_by,
    }
    p.setdefault("versions", []).append(version)
    p["current_version_id"] = vid
    p["updated_at"] = ts
    p["colors"] = colors or p.get("colors", [])
    if p.get("status") == "published":
        p["status"] = "review"
    _save_store(store)
    return _public_project(p, include_react_code=True)


def add_comment(
    project_id: str,
    *,
    text: str,
    author: str = "Пользователь",
    x: float = 0.5,
    y: float = 0.5,
    frame_id: str = "main",
) -> Optional[dict]:
    store = _load_store()
    p = _find_project(store, project_id)
    if not p:
        return None
    text = (text or "").strip()
    if not text:
        raise ValueError("Текст комментария обязателен")

    comment = {
        "id": _uid("cmt-"),
        "text": text[:500],
        "author": author[:80],
        "x": max(0.0, min(1.0, float(x))),
        "y": max(0.0, min(1.0, float(y))),
        "frame_id": frame_id or "main",
        "status": "open",
        "created_at": _now(),
        "resolved_in_version": None,
    }
    p.setdefault("comments", []).append(comment)
    p["updated_at"] = _now()
    if p.get("status") == "published":
        p["status"] = "review"
    _save_store(store)
    return comment


def resolve_comments(project_id: str, version_id: str, comment_ids: Optional[list] = None) -> None:
    store = _load_store()
    p = _find_project(store, project_id)
    if not p:
        return
    ids = set(comment_ids or [])
    for c in p.get("comments", []):
        if c.get("status") != "open":
            continue
        if not ids or c.get("id") in ids:
            c["status"] = "resolved"
            c["resolved_in_version"] = version_id
    p["updated_at"] = _now()
    _save_store(store)


def build_revision_task(project: dict) -> str:
    open_comments = [c for c in project.get("comments", []) if c.get("status") == "open"]
    current = project.get("current_version") or {}
    base_task = current.get("task") or project.get("title", "UI проект")
    if not open_comments:
        return base_task

    lines = [f"Обнови UI проекта «{project.get('title')}». Исходная задача: {base_task}", "", "Правки от пользователя:"]
    for i, c in enumerate(open_comments, 1):
        pos = f" (точка {int(c.get('x', 0.5)*100)}%, {int(c.get('y', 0.5)*100)}%)"
        lines.append(f"{i}. {c.get('text')}{pos}")
    lines.append("")
    lines.append("Сохрани общий стиль, исправь только указанное.")
    return "\n".join(lines)


async def apply_open_comments(agent, project_id: str) -> Optional[dict]:
    """Соня создаёт новую версию по открытым комментариям."""
    store = _load_store()
    p = _find_project(store, project_id)
    if not p:
        return None

    full = _public_project(p)
    open_comments = [c for c in full.get("comments", []) if c.get("status") == "open"]
    if not open_comments:
        raise ValueError("Нет открытых комментариев")

    task = build_revision_task(full)
    if agent.room_manager:
        await agent._broadcast(f"🎨 Studio: правлю «{p.get('title')}» по {len(open_comments)} комментариям…", "learning")

    preview = await _generate_studio_preview(task, theme=p.get("theme", ""), colors=full.get("colors"))
    updated = add_version(
        project_id,
        task=task,
        react_code=preview.get("code", ""),
        preview_title=preview.get("title", p.get("title")),
        colors=full.get("colors"),
        created_by="sonya",
    )
    if not updated:
        return None

    version_id = updated.get("current_version", {}).get("id")
    resolve_comments(project_id, version_id, [c["id"] for c in open_comments])

    preview_payload = {
        "title": updated["current_version"]["title"],
        "code": updated["current_version"]["react_code"],
        "task": task,
        "timestamp": _now(),
        "studio_project_id": project_id,
    }
    agent.last_preview = preview_payload

    if agent.room_manager:
        await agent.room_manager.broadcast_work({
            "type": "sonya_studio_update",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            "project_id": project_id,
            "project_title": updated.get("title"),
            "version_num": updated["current_version"].get("version_num"),
            "message": f"✅ Studio · «{updated.get('title')}» v{updated['current_version'].get('version_num')} — правки применены",
            "preview": preview_payload,
            "timestamp": _now(),
        })
        await agent.room_manager.broadcast_work({
            "type": "react_preview",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            **preview_payload,
        })

    return get_project(project_id)


def publish_project(project_id: str, *, figma_url: str = "") -> Optional[dict]:
    store = _load_store()
    p = _find_project(store, project_id)
    if not p:
        return None

    current = next((v for v in p.get("versions", []) if v.get("id") == p.get("current_version_id")), None)
    if not current:
        return None

    ts = _now()
    handoff = {
        "published_at": ts,
        "preview_title": current.get("title"),
        "task": current.get("task"),
        "colors": current.get("colors", []),
        "css_tokens": _colors_to_css(current.get("colors", [])),
        "react_code": current.get("react_code", ""),
        "version_num": current.get("version_num", 1),
        "figma_url": figma_url.strip() or None,
        "instructions": (
            "Handoff из Sonya Design Studio. React-код и tokens готовы. "
            "Для Figma: создайте файл или вставьте скриншот превью; tokens — в :root."
        ),
    }
    p["status"] = "published"
    p["published_at"] = ts
    p["figma_handoff"] = handoff
    p["updated_at"] = ts
    _save_store(store)
    return _public_project(p, include_react_code=True)


def _colors_to_css(colors: list) -> str:
    names = ["--accent", "--surface", "--text", "--border", "--green", "--purple", "--muted", "--yellow"]
    lines = [":root {"]
    for i, c in enumerate(colors[:8]):
        if i < len(names):
            lines.append(f"  {names[i]}: {c};")
    lines.append("}")
    return "\n".join(lines)


async def create_studio_project(agent, *, title: str = "", theme: str = "", task: str = "") -> dict:
    """Соня создаёт проект в Studio (без Figma API)."""
    import random
    from integrations.figma_learning import load_patterns, _pick_colors

    patterns = load_patterns()
    theme_id, theme_title = random.choice(PROJECT_THEMES)
    theme = theme or theme_id
    colors = _pick_colors(patterns)
    color_hint = ", ".join(colors[:5])
    task = _augment_task_for_theme(task, theme, theme_title, color_hint)
    title = _resolve_project_title(title=title, task=task, theme=theme) or theme_title
    preview = await _generate_studio_preview(task, theme=theme, colors=colors)
    project = create_project(
        title=title,
        description=f"Проект Sonya Studio · {theme_title}",
        task=task,
        theme=theme,
        react_code=preview.get("code", ""),
        preview_title=preview.get("title", title),
        colors=colors,
        created_by="sonya",
        origin="sonya_auto",
    )

    preview_payload = {
        "title": project["current_version"]["title"],
        "code": project["current_version"]["react_code"],
        "task": task,
        "timestamp": _now(),
        "studio_project_id": project["id"],
    }
    agent.last_preview = preview_payload

    if agent.room_manager:
        await agent.room_manager.broadcast_work({
            "type": "sonya_studio_project",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            "project": project,
            "message": (
                f"✨ **Sonya Studio** · новый проект «{title}»\n"
                f"Палитра: {color_hint}\n"
                f"Откройте вкладку **Studio** для комментариев и публикации"
            ),
            "preview": preview_payload,
            "timestamp": _now(),
        })
        await agent.room_manager.broadcast_work({
            "type": "react_preview",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            **preview_payload,
        })

    return project


async def run_studio_create_session(agent) -> Optional[dict]:
    """Создаёт проект в Studio. Возвращает project или None при ошибке."""
    try:
        return await create_studio_project(agent)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Studio create failed: %s", e)
        return None
