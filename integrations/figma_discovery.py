"""Автономное обнаружение Figma-макетов для Сони — без ссылок от пользователя."""

import json
import os
import random
import re
from datetime import datetime
from typing import Any, Optional

from integrations.figma_client import is_figma_api_url, parse_figma_url

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DISCOVERY_FILE = os.path.join(DATA_DIR, "sonya_figma_discovery.json")

FIGMA_LINK_RE = re.compile(
    r"https?://(?:www\.)?figma\.com/(?:design|file|community/file)/[a-zA-Z0-9]+[^\s\"'<>]*",
    re.IGNORECASE,
)

# Дополнительный каталог — расширяется через config.figma_discovery_catalog
BUILTIN_DISCOVERY_CATALOG: list[dict] = []

WEB_DISCOVERY_TOPICS = [
    "figma community landing page template file",
    "figma community dashboard ui kit",
    "figma community mobile app design",
    "figma community design system components",
    "figma community ecommerce ui",
    "figma community portfolio website",
]


def _ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _default_state() -> dict:
    return {
        "studied_keys": [],
        "failed_keys": [],
        "queue": [],
        "log": [],
        "web_cache": [],
        "last_scan_at": None,
        "last_study_at": None,
    }


def load_discovery() -> dict:
    _ensure_dirs()
    if not os.path.exists(DISCOVERY_FILE):
        return _default_state()
    try:
        with open(DISCOVERY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        base = _default_state()
        base.update(data)
        return base
    except Exception:
        return _default_state()


def save_discovery(data: dict) -> None:
    _ensure_dirs()
    with open(DISCOVERY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _is_auto_discover_enabled() -> bool:
    import config as cfg_module

    return bool(cfg_module.config.get("figma_auto_discover", True))


def _team_scan_enabled() -> bool:
    import config as cfg_module

    return bool(cfg_module.config.get("figma_discover_team_files", True))


def get_catalog() -> list[dict]:
    import config as cfg_module

    extra = cfg_module.config.get("figma_discovery_catalog") or []
    seen_keys: set[str] = set()
    merged: list[dict] = []
    for item in list(extra) + BUILTIN_DISCOVERY_CATALOG:
        if not isinstance(item, dict):
            continue
        key = item.get("file_key") or ""
        url = item.get("url") or ""
        if not key and url:
            parsed = parse_figma_url(url)
            key = (parsed or {}).get("file_key") or ""
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        entry = dict(item)
        entry["file_key"] = key
        if not entry.get("url"):
            slug = (entry.get("name") or "Community").lower().replace(" ", "-")[:48]
            entry["url"] = f"https://www.figma.com/design/{key}/{slug}"
        merged.append(entry)
    return merged


def _studied_set(state: dict) -> set[str]:
    return set(state.get("studied_keys") or [])


def _failed_set(state: dict) -> set[str]:
    return set(state.get("failed_keys") or [])


def _is_known_key(state: dict, file_key: str) -> bool:
    return file_key in _studied_set(state) or file_key in _failed_set(state)


def file_key_to_url(file_key: str, name: str = "Community") -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")[:48] or "community"
    return f"https://www.figma.com/design/{file_key}/{slug}"


def extract_figma_urls(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for m in FIGMA_LINK_RE.findall(text):
        url = m.rstrip(".,)")
        if is_figma_api_url(url) and url not in found:
            found.append(url)
    return found


def mark_studied(file_key: str, *, name: str = "", url: str = "", source: str = "auto") -> None:
    if not file_key:
        return
    state = load_discovery()
    studied = state.setdefault("studied_keys", [])
    if file_key not in studied:
        studied.append(file_key)
    state["studied_keys"] = studied[-200:]

    state["queue"] = [q for q in state.get("queue", []) if q.get("file_key") != file_key]

    log_entry = {
        "file_key": file_key,
        "name": name or file_key,
        "url": url,
        "source": source,
        "status": "studied",
        "timestamp": datetime.now().isoformat(),
    }
    state["log"] = ([log_entry] + state.get("log", []))[:40]
    state["last_study_at"] = log_entry["timestamp"]
    save_discovery(state)


def mark_failed(file_key: str, reason: str = "", *, url: str = "", source: str = "auto") -> None:
    if not file_key:
        return
    state = load_discovery()
    failed = state.setdefault("failed_keys", [])
    if file_key not in failed:
        failed.append(file_key)
    state["failed_keys"] = failed[-100:]
    state["queue"] = [q for q in state.get("queue", []) if q.get("file_key") != file_key]

    log_entry = {
        "file_key": file_key,
        "url": url,
        "source": source,
        "status": "failed",
        "reason": (reason or "")[:120],
        "timestamp": datetime.now().isoformat(),
    }
    state["log"] = ([log_entry] + state.get("log", []))[:40]
    save_discovery(state)


def _enqueue(state: dict, targets: list[dict]) -> int:
    queue = state.get("queue") or []
    existing = {q.get("file_key") for q in queue}
    added = 0
    for t in targets:
        key = t.get("file_key")
        if not key or key in existing or _is_known_key(state, key):
            continue
        queue.append(t)
        existing.add(key)
        added += 1
    state["queue"] = queue[:60]
    return added


async def scan_team_files(client) -> list[dict]:
    """Файлы из команд пользователя (OAuth/PAT с доступом к teams)."""
    if not client or not client.configured:
        return []
    targets: list[dict] = []
    try:
        me = await client.get_me()
    except Exception:
        return []

    teams = me.get("teams") or []
    for team in teams[:3]:
        team_id = team.get("id")
        team_name = team.get("name") or "Team"
        if not team_id:
            continue
        try:
            projects_resp = await client.get_team_projects(str(team_id))
        except Exception:
            continue
        for project in (projects_resp.get("projects") or [])[:8]:
            project_id = project.get("id")
            project_name = project.get("name") or "Project"
            if not project_id:
                continue
            try:
                files_resp = await client.get_project_files(str(project_id))
            except Exception:
                continue
            for f in (files_resp.get("files") or [])[:12]:
                key = f.get("key")
                name = f.get("name") or "File"
                if not key:
                    continue
                targets.append({
                    "file_key": key,
                    "name": name,
                    "url": file_key_to_url(key, name),
                    "source": "team",
                    "category": "team",
                    "team": team_name,
                    "project": project_name,
                })
    return targets


async def discover_urls_from_web(agent) -> list[str]:
    """Поиск community-ссылок через веб-обучение агента."""
    topic = random.choice(WEB_DISCOVERY_TOPICS)
    material = await agent._fetch_learning_material(topic)
    if not material:
        return []

    blob = " ".join(
        str(material.get(k) or "")
        for k in ("title", "summary", "url", "content", "snippet")
    )
    urls = extract_figma_urls(blob)
    if material.get("url"):
        urls = extract_figma_urls(str(material["url"])) + urls

    state = load_discovery()
    cache = state.get("web_cache") or []
    new_urls = [u for u in urls if u not in cache and is_figma_api_url(u)]
    if new_urls:
        state["web_cache"] = (new_urls + cache)[:30]
        save_discovery(state)
    return new_urls[:5]


async def run_discovery_scan(agent=None, *, include_web: bool = True) -> dict:
    """Обновить очередь: team → каталог → веб."""
    if not _is_auto_discover_enabled():
        return {"ok": False, "reason": "disabled", "added": 0}

    from integrations.figma_client import get_client_async

    state = load_discovery()
    added = 0
    sources: dict[str, int] = {}

    client = await get_client_async()
    if _team_scan_enabled() and client.configured:
        team_targets = await scan_team_files(client)
        n = _enqueue(state, team_targets)
        if n:
            sources["team"] = n
            added += n

    catalog_targets = []
    for item in get_catalog():
        key = item["file_key"]
        if _is_known_key(state, key):
            continue
        catalog_targets.append({
            "file_key": key,
            "name": item.get("name", "Community"),
            "url": item.get("url") or file_key_to_url(key, item.get("name", "")),
            "source": "catalog",
            "category": item.get("category", "community"),
        })
    n = _enqueue(state, catalog_targets)
    if n:
        sources["catalog"] = n
        added += n

    if include_web and agent is not None:
        web_urls = await discover_urls_from_web(agent)
        web_targets = []
        for url in web_urls:
            parsed = parse_figma_url(url)
            if not parsed:
                continue
            key = parsed["file_key"]
            if _is_known_key(state, key):
                continue
            web_targets.append({
                "file_key": key,
                "url": url,
                "name": "Web discovery",
                "source": "web",
                "category": "web",
            })
        n = _enqueue(state, web_targets)
        if n:
            sources["web"] = n
            added += n

    state["last_scan_at"] = datetime.now().isoformat()
    save_discovery(state)
    return {
        "ok": True,
        "added": added,
        "sources": sources,
        "queue_size": len(state.get("queue") or []),
        "studied_count": len(state.get("studied_keys") or []),
    }


def pick_next_target(state: Optional[dict] = None) -> Optional[dict]:
    """Следующий макет из очереди (team > catalog > web по порядку добавления)."""
    state = state or load_discovery()
    queue = state.get("queue") or []
    if not queue:
        return None
    # Приоритет: team, catalog, web
    priority = {"team": 0, "catalog": 1, "web": 2, "auto": 3}
    queue = sorted(queue, key=lambda q: priority.get(q.get("source", "auto"), 9))
    return queue[0]


async def try_autonomous_study(agent, *, max_attempts: int = 2) -> bool:
    """Соня сама выбирает и изучает макет из очереди обнаружения."""
    if not _is_auto_discover_enabled():
        return False

    from integrations.figma_learning import study_reference_file
    from integrations.figma_rate_limit import is_in_cooldown

    if is_in_cooldown():
        return False

    state = load_discovery()
    if not state.get("queue"):
        await run_discovery_scan(agent, include_web=True)

    for _ in range(max_attempts):
        state = load_discovery()
        target = pick_next_target(state)
        if not target:
            await run_discovery_scan(agent, include_web=True)
            target = pick_next_target(load_discovery())
        if not target:
            return False

        url = target.get("url") or file_key_to_url(target["file_key"], target.get("name", ""))
        source = target.get("source", "auto")
        result = await study_reference_file(
            agent,
            url,
            source="figma_auto",
            discovery_meta={"discovery_source": source, "file_key": target.get("file_key")},
        )
        key = target.get("file_key") or (parse_figma_url(url) or {}).get("file_key")

        if result and not result.get("error"):
            return True

        if key:
            err = (result or {}).get("error", "unknown")
            mark_failed(key, str(err), url=url, source=source)
        if result and result.get("rate_limit"):
            return False

    return False


def get_discovery_status() -> dict:
    import config as cfg_module

    state = load_discovery()
    catalog = get_catalog()
    next_target = pick_next_target(state)
    return {
        "auto_discover_enabled": _is_auto_discover_enabled(),
        "discover_team_files": _team_scan_enabled(),
        "queue_size": len(state.get("queue") or []),
        "studied_keys_count": len(state.get("studied_keys") or []),
        "failed_keys_count": len(state.get("failed_keys") or []),
        "catalog_size": len(catalog),
        "last_scan_at": state.get("last_scan_at"),
        "last_study_at": state.get("last_study_at"),
        "next_target": {
            "name": next_target.get("name"),
            "url": next_target.get("url"),
            "source": next_target.get("source"),
            "category": next_target.get("category"),
        }
        if next_target
        else None,
        "queue_preview": (state.get("queue") or [])[:8],
        "recent_log": (state.get("log") or [])[:10],
        "reference_urls_count": len(cfg_module.config.get("figma_reference_urls") or []),
    }
