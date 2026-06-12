"""Соня — автономное обучение в Figma: изучение референсов и свои проекты."""

import json
import os
import random
from datetime import datetime
from typing import Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PATTERNS_FILE = os.path.join(DATA_DIR, "sonya_figma_patterns.json")
PORTFOLIO_DIR = os.path.join(DATA_DIR, "sonya_figma_portfolio")
PORTFOLIO_INDEX = os.path.join(PORTFOLIO_DIR, "index.json")

PROJECT_THEMES = [
    ("landing", "Landing page для SaaS-стартапа", "лендинг SaaS hero pricing CTA"),
    ("dashboard", "Analytics dashboard с карточками KPI", "дашборд analytics KPI графики"),
    ("mobile", "Mobile app onboarding экраны", "mobile onboarding swipe UI"),
    ("ecommerce", "E-commerce карточка товара", "карточка товара ecommerce shop"),
    ("design_system", "Design system: кнопки и формы", "design system кнопки формы tokens"),
    ("portfolio", "Portfolio creative agency", "portfolio agency creative gallery"),
]

FIGMA_WEB_TOPICS = [
    "Figma auto layout best practices",
    "Figma design tokens variables",
    "Figma component variants",
    "UI design trends 2025",
    "Figma community templates",
    "design system color palette",
]

# Встроенные паттерны — когда API недоступен / rate limit / site-ссылки
BUILTIN_PATTERNS = [
    {
        "file_name": "SaaS Dashboard UI",
        "colors": ["#6c63ff", "#5ecf8a", "#1a1d2e", "#f0f0f5", "#ffd866", "#c792ea"],
        "fonts": ["Inter 600", "Inter 400"],
        "frames": ["Sidebar", "KPI Cards", "Chart Area", "Top Nav"],
        "source": "builtin",
    },
    {
        "file_name": "Landing Hero Section",
        "colors": ["#4f7df3", "#ffffff", "#0c0d10", "#5ecf8a", "#e2e4ea"],
        "fonts": ["Inter 700", "Inter 400"],
        "frames": ["Hero", "Features", "Pricing", "Footer CTA"],
        "source": "builtin",
    },
    {
        "file_name": "Mobile App Shell",
        "colors": ["#7aa2ff", "#141519", "#f07178", "#5ecf8a", "#2a2b35"],
        "fonts": ["SF Pro 600", "SF Pro 400"],
        "frames": ["Onboarding", "Home Tab", "Profile", "Settings"],
        "source": "builtin",
    },
]


def _ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PORTFOLIO_DIR, exist_ok=True)


def load_patterns() -> dict:
    _ensure_dirs()
    if not os.path.exists(PATTERNS_FILE):
        return {"studied": [], "colors": [], "fonts": [], "frames": [], "sources": []}
    try:
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"studied": [], "colors": [], "fonts": [], "frames": [], "sources": []}


def save_patterns(data: dict) -> None:
    _ensure_dirs()
    with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_portfolio() -> list:
    _ensure_dirs()
    if not os.path.exists(PORTFOLIO_INDEX):
        return []
    try:
        with open(PORTFOLIO_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_portfolio_entry(entry: dict) -> None:
    _ensure_dirs()
    items = load_portfolio()
    items.insert(0, entry)
    items = items[:50]
    with open(PORTFOLIO_INDEX, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def get_reference_urls() -> list[str]:
    import config as cfg_module
    from integrations.figma_client import is_figma_api_url

    urls = list(cfg_module.config.get("figma_reference_urls") or [])
    default = cfg_module.config.get("figma_default_url", "")
    if default and default not in urls:
        urls.insert(0, default)
    return [u for u in urls if u and "figma.com" in u and is_figma_api_url(u)]


def ensure_seed_patterns() -> None:
    """Стартовые паттерны — чтобы Соня могла создавать проекты без Figma API."""
    patterns = load_patterns()
    if patterns.get("colors") or patterns.get("studied"):
        return
    for bp in BUILTIN_PATTERNS:
        _merge_builtin_pattern(bp)


def _merge_patterns(figma_result: dict, source_url: str) -> dict:
    patterns = load_patterns()
    summary = figma_result.get("summary") or {}

    studied = {
        "file_name": summary.get("file_name", "Figma"),
        "url": source_url,
        "colors": summary.get("colors", [])[:12],
        "fonts": summary.get("fonts", [])[:6],
        "frames": [f.get("name") for f in (summary.get("frames") or [])[:8]],
        "timestamp": datetime.now().isoformat(),
    }
    patterns["studied"] = ([studied] + patterns.get("studied", []))[:30]

    for c in summary.get("colors") or []:
        if c not in patterns.get("colors", []):
            patterns["colors"].append(c)
    patterns["colors"] = patterns["colors"][:40]

    for f in summary.get("fonts") or []:
        if f not in patterns.get("fonts", []):
            patterns["fonts"].append(f)
    patterns["fonts"] = patterns["fonts"][:20]

    for fr in summary.get("frames") or []:
        name = fr.get("name")
        if name and name not in patterns.get("frames", []):
            patterns["frames"].append(name)
    patterns["frames"] = patterns["frames"][:30]

    if source_url not in patterns.get("sources", []):
        patterns.setdefault("sources", []).append(source_url)
    patterns["sources"] = patterns["sources"][:20]

    save_patterns(patterns)
    return patterns


def _merge_builtin_pattern(bp: dict) -> dict:
    patterns = load_patterns()
    studied = {
        "file_name": bp.get("file_name", "Reference"),
        "url": "",
        "colors": bp.get("colors", [])[:12],
        "fonts": bp.get("fonts", [])[:6],
        "frames": bp.get("frames", [])[:8],
        "timestamp": datetime.now().isoformat(),
        "source": bp.get("source", "builtin"),
    }
    patterns["studied"] = ([studied] + patterns.get("studied", []))[:30]
    for c in bp.get("colors") or []:
        if c not in patterns.get("colors", []):
            patterns.setdefault("colors", []).append(c)
    patterns["colors"] = patterns.get("colors", [])[:40]
    for f in bp.get("fonts") or []:
        if f not in patterns.get("fonts", []):
            patterns.setdefault("fonts", []).append(f)
    patterns["fonts"] = patterns.get("fonts", [])[:20]
    save_patterns(patterns)
    return patterns


async def study_builtin_pattern(agent, pattern: Optional[dict] = None) -> bool:
    """Изучение без Figma API — встроенный UI-паттерн."""
    bp = pattern or random.choice(BUILTIN_PATTERNS)
    patterns = _merge_builtin_pattern(bp)
    frame_names = ", ".join(bp.get("frames", [])[:4])

    knowledge = {
        "topic": f"UI pattern: {bp.get('file_name', 'Reference')}",
        "title": bp.get("file_name", "UI Reference"),
        "summary": (
            f"Изучила референс «{bp.get('file_name')}»: "
            f"{len(bp.get('colors', []))} цветов, фреймы: {frame_names or '—'}."
        ),
        "url": "",
        "source": "figma_builtin",
        "keywords": ["figma", "design", "ui", "pattern"] + (bp.get("colors") or [])[:2],
        "timestamp": datetime.now().isoformat(),
    }
    agent.learned_topics.append(knowledge)
    if len(agent.learned_topics) > 200:
        agent.learned_topics = agent.learned_topics[-200:]
    agent._persist_knowledge()

    if agent.room_manager:
        await agent.room_manager.broadcast_learning({
            "type": "figma_study",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            "message": (
                f"🎨 **UI Reference** · «{bp.get('file_name')}»\n"
                f"Цвета: {', '.join(bp.get('colors', [])[:5])}\n"
                f"Фреймы: {frame_names or '—'}\n"
                f"_(локальный референс — Figma API недоступен)_"
            ),
            "file_name": bp.get("file_name"),
            "colors": bp.get("colors", [])[:8],
            "url": "",
            "patterns_total": len(patterns.get("studied", [])),
            "timestamp": datetime.now().isoformat(),
        })
    return True


def _pick_colors(patterns: dict, count: int = 5) -> list[str]:
    pool = patterns.get("colors") or []
    if len(pool) >= count:
        return random.sample(pool, count)
    defaults = ["#6c63ff", "#5ecf8a", "#1a1d2e", "#f0f0f5", "#c792ea", "#ffd866"]
    merged = list(dict.fromkeys(pool + defaults))
    return merged[:count]


async def remember_figma_from_import(agent, figma_result: dict, source_url: str) -> dict:
    """Запомнить макет после импорта — паттерны + knowledge без повторного API."""
    patterns = _merge_patterns(figma_result, source_url)
    summary = figma_result.get("summary") or {}
    frames = summary.get("frames") or []
    frame_names = ", ".join(f.get("name", "") for f in frames[:4] if f.get("name"))

    knowledge = {
        "topic": f"Figma: {summary.get('file_name', 'макет')}",
        "title": summary.get("file_name", "Figma import"),
        "summary": (
            f"Импорт и запоминание: {len(summary.get('colors', []))} цветов, "
            f"фреймы: {frame_names or '—'}."
        ),
        "url": source_url,
        "source": "figma",
        "keywords": ["figma", "design", "ui", "import"] + (summary.get("colors") or [])[:3],
        "timestamp": datetime.now().isoformat(),
        "figma_data": {
            "colors": summary.get("colors", [])[:8],
            "css_tokens": figma_result.get("css_tokens", ""),
        },
    }
    agent.learned_topics.append(knowledge)
    if len(agent.learned_topics) > 200:
        agent.learned_topics = agent.learned_topics[-200:]
    agent._persist_knowledge()

    if agent.room_manager:
        await agent.room_manager.broadcast_learning({
            "type": "figma_study",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            "message": (
                f"🎨 **Запомнила макет** · «{summary.get('file_name')}»\n"
                f"Цвета: {', '.join(summary.get('colors', [])[:5]) or '—'}\n"
                f"Фреймы: {frame_names or '—'}"
            ),
            "file_name": summary.get("file_name"),
            "colors": summary.get("colors", [])[:8],
            "preview_url": figma_result.get("preview_url"),
            "url": source_url,
            "patterns_total": len(patterns.get("studied", [])),
            "timestamp": datetime.now().isoformat(),
        })
    return knowledge


async def study_reference_file(agent, url: str) -> Optional[dict]:
    from integrations.figma_client import get_client_async, parse_figma_url, is_figma_api_url
    from integrations.figma_rate_limit import FigmaRateLimitError, is_in_cooldown

    if is_in_cooldown():
        return {"error": "rate_limit", "url": url}

    parsed = parse_figma_url(url)
    if not parsed:
        return None
    if not is_figma_api_url(url):
        return {"error": "unsupported_url", "url": url}

    client = await get_client_async()
    if not client.configured:
        return None

    try:
        result = await client.import_design(url, lightweight=True)
    except FigmaRateLimitError as e:
        return {"error": str(e), "rate_limit": True, "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}

    patterns = _merge_patterns(result, url)
    summary = result.get("summary") or {}
    frames = summary.get("frames") or []
    frame_names = ", ".join(f.get("name", "") for f in frames[:4] if f.get("name"))

    knowledge = {
        "topic": f"Figma: {summary.get('file_name', 'макет')}",
        "title": summary.get("file_name", "Figma reference"),
        "summary": (
            f"Изучила макет: {len(summary.get('colors', []))} цветов, "
            f"{len(frames)} фреймов. Фреймы: {frame_names or '—'}. "
            f"Шрифты: {', '.join((summary.get('fonts') or [])[:3]) or 'system'}."
        ),
        "url": url,
        "source": "figma",
        "keywords": ["figma", "design", "ui", "tokens"] + (summary.get("colors") or [])[:3],
        "timestamp": datetime.now().isoformat(),
        "figma_data": {
            "colors": summary.get("colors", [])[:8],
            "css_tokens": result.get("css_tokens", ""),
        },
    }

    agent.learned_topics.append(knowledge)
    if len(agent.learned_topics) > 200:
        agent.learned_topics = agent.learned_topics[-200:]
    agent._persist_knowledge()

    if agent.room_manager:
        await agent.room_manager.broadcast_learning({
            "type": "figma_study",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            "message": (
                f"🎨 **Figma Community** · изучила «{summary.get('file_name')}»\n"
                f"Цвета: {', '.join(summary.get('colors', [])[:5]) or '—'}\n"
                f"Фреймы: {frame_names or '—'}\n"
                f"🔗 {url}"
            ),
            "file_name": summary.get("file_name"),
            "colors": summary.get("colors", [])[:8],
            "preview_url": result.get("preview_url"),
            "url": url,
            "patterns_total": len(patterns.get("studied", [])),
            "timestamp": datetime.now().isoformat(),
        })

    return {"patterns": patterns, "result": result, "knowledge": knowledge}


async def create_original_project(agent) -> Optional[dict]:
    from agents.react_preview import generate_react_preview

    patterns = load_patterns()
    theme_id, theme_title, task_hint = random.choice(PROJECT_THEMES)
    colors = _pick_colors(patterns)
    inspiration = random.choice(patterns.get("studied", [{}])) if patterns.get("studied") else {}
    insp_name = inspiration.get("file_name", "собственный стиль")

    color_hint = ", ".join(colors[:5])
    task_text = (
        f"{task_hint}. Собственный проект Сони «{theme_title}». "
        f"Палитра из Figma-обучения: {color_hint}. "
        f"Вдохновение: {insp_name}."
    )

    preview = generate_react_preview(task_text)
    preview["task"] = task_text
    preview["timestamp"] = datetime.now().isoformat()
    preview["figma_inspired"] = True
    preview["colors"] = colors

    agent.last_preview = preview

    entry = {
        "id": f"sonya-{int(datetime.now().timestamp())}",
        "title": theme_title,
        "theme": theme_id,
        "colors": colors,
        "inspiration": insp_name,
        "preview_title": preview.get("title"),
        "task": task_text,
        "timestamp": preview["timestamp"],
    }
    save_portfolio_entry(entry)

    knowledge = {
        "topic": f"Свой проект: {theme_title}",
        "title": theme_title,
        "summary": f"Создала UI «{theme_title}» на основе {len(patterns.get('studied', []))} изученных макетов. Палитра: {color_hint}.",
        "url": "",
        "source": "figma_portfolio",
        "keywords": ["figma", "portfolio", theme_id] + colors[:2],
        "timestamp": datetime.now().isoformat(),
    }
    agent.learned_topics.append(knowledge)
    agent._persist_knowledge()

    if agent.room_manager:
        await agent.room_manager.broadcast_work({
            "type": "figma_portfolio",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            "message": (
                f"✨ **Новый дизайн-проект** · «{theme_title}»\n"
                f"Палитра: {color_hint}\n"
                f"Вдохновение: {insp_name}\n"
                f"Откройте React Preview 🎨"
            ),
            "title": theme_title,
            "colors": colors,
            "theme": theme_id,
            "timestamp": preview["timestamp"],
        })
        await agent.room_manager.broadcast_work({
            "type": "react_preview",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            "title": preview["title"],
            "code": preview["code"],
            "task": task_text,
            "timestamp": preview["timestamp"],
            "is_site": preview.get("is_site", False),
            "figma_inspired": True,
        })

    return entry


async def run_figma_study_session(agent) -> bool:
    from integrations.figma_rate_limit import is_in_cooldown

    ensure_seed_patterns()

    if is_in_cooldown():
        return await study_builtin_pattern(agent)

    urls = get_reference_urls()
    if urls:
        random.shuffle(urls)
        for url in urls[:2]:
            result = await study_reference_file(agent, url)
            if result and not result.get("error"):
                return True
            if result and result.get("rate_limit"):
                return await study_builtin_pattern(agent)

    # Нет API-ссылок или все запросы неудачны — локальный референс или веб
    if random.random() < 0.65:
        return await study_builtin_pattern(agent)
    return await _study_figma_web(agent)


async def _study_figma_web(agent) -> bool:
    topic = random.choice(FIGMA_WEB_TOPICS)
    await agent._broadcast(f"📚 Figma: изучаю *{topic}* (веб-ресурсы)...", "learning")
    material = await agent._fetch_learning_material(topic)
    if material:
        entry = {
            "topic": topic,
            "title": material.get("title", topic),
            "summary": material.get("summary", ""),
            "url": material.get("url", ""),
            "source": "figma_web",
            "keywords": agent._extract_keywords(f"{topic} {material.get('title', '')}"),
            "timestamp": datetime.now().isoformat(),
        }
        agent.learned_topics.append(entry)
        agent._persist_knowledge()
        await agent._broadcast(
            f"💡 [Figma] *{entry['title']}*\n{entry['summary'][:200]}",
            "learning_result",
        )
        return True
    return False


async def run_figma_create_session(agent) -> bool:
    from integrations.sonya_studio import run_studio_create_session
    return (await run_studio_create_session(agent)) is not None


async def sonya_figma_studio_loop(room_manager, interval_min: int = 12, interval_max: int = 28) -> None:
    """Фоновый цикл: Соня учится в Figma и создаёт проекты."""
    import asyncio
    import config as cfg_module

    while True:
        delay = random.uniform(interval_min * 60, interval_max * 60)
        await asyncio.sleep(delay)

        if not cfg_module.config.get("figma_study_enabled", True):
            continue

        frontend = room_manager.agents.get("frontend")
        if not frontend:
            continue
        if frontend.status in ("working", "thinking") or not frontend.task_queue.empty():
            continue

        from integrations.figma_oauth import is_figma_connected
        from integrations.figma_rate_limit import is_in_cooldown, cooldown_remaining

        try:
            frontend.status = "learning"
            frontend.location = "library"

            if is_in_cooldown():
                await frontend._broadcast(
                    f"⏳ Figma API: пауза {cooldown_remaining()}с. Использую локальные UI-референсы…",
                    "learning",
                )

            action = random.choices(["study", "study", "create"], weights=[0.4, 0.35, 0.25])[0]
            ok = False
            if action == "create":
                from integrations.sonya_studio import run_studio_create_session
                project = await run_studio_create_session(frontend)
                ok = project is not None
                if ok:
                    frontend.figma_creations = getattr(frontend, "figma_creations", 0) + 1
            else:
                ok = await run_figma_study_session(frontend)
                if ok:
                    frontend.figma_studies = getattr(frontend, "figma_studies", 0) + 1

            await room_manager.send_agents_state()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Figma studio loop: %s", e)
        finally:
            if frontend.status == "learning":
                frontend.status = "idle"
                frontend.location = "studio"
                await room_manager.send_agents_state()


def get_studio_stats() -> dict:
    ensure_seed_patterns()
    patterns = load_patterns()
    portfolio = load_portfolio()
    return {
        "studied_count": len(patterns.get("studied", [])),
        "patterns_colors": len(patterns.get("colors", [])),
        "portfolio_count": len(portfolio),
        "recent_studied": patterns.get("studied", [])[:5],
        "recent_portfolio": portfolio[:5],
        "reference_urls": get_reference_urls(),
    }
