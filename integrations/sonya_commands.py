"""Распознавание русскоязычных команд Sonya Design Studio."""

import re
from typing import Optional

STUDIO_MARKERS = (
    "studio", "студи", "sonya studio", "design studio", "sonya design",
    "sonya studio", "design studio",
)

UI_HINTS = (
    "ui", "ux", "интерфейс", "react", "figma", "дизайн", "макет", "верст",
    "landing", "лендинг", "dashboard", "дашборд", "кнопк", "форм", "hero",
    "компонент", "превью", "preview",
)


def _norm(text: str) -> str:
    return (text or "").strip().lower().replace("ё", "е")


def _has_studio_context(tl: str) -> bool:
    if any(m in tl for m in STUDIO_MARKERS):
        return True
    if re.search(r"нов(ый|ая|ое)\s+(ui\s+)?(проект|макет)", tl):
        return True
    if re.search(r"(создай|сделай|сгенерируй|запусти)\s+.*(проект|макет)", tl):
        return any(h in tl for h in UI_HINTS)
    return False


def title_from_task(text: str, fallback: str = "") -> str:
    """Человекочитаемое имя проекта из текста задачи."""
    raw = (text or "").strip()
    if not raw:
        return fallback
    m = re.search(r"[«\"']([^»\"']+)[»\"']", raw)
    if m:
        return m.group(1).strip()[:80]
    tl = _norm(raw)
    cleaned = re.sub(
        r"^(?:@?\s*соня\s*,?\s*)?(?:сделай|создай|сгенерируй|запусти|напиши|разработай|сверстай|построй|нужен|хочу)\s+",
        "",
        tl,
    ).strip()
    cleaned = re.sub(r"^(?:мне\s+)?(?:современный|новый|красивый|адаптивный)\s+", "", cleaned).strip()
    if cleaned.startswith("landing page "):
        cleaned = "Landing · " + cleaned[len("landing page "):]
    elif cleaned.startswith("landing "):
        cleaned = "Landing · " + cleaned[len("landing "):]
    elif cleaned.startswith("лендинг "):
        cleaned = "Лендинг · " + cleaned[len("лендинг "):]
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        return fallback
    return cleaned[:80].capitalize()


def _extract_title(text: str) -> str:
    return title_from_task(text, "")


def match_studio_intent(text: str) -> Optional[dict]:
    """Возвращает intent: create | apply_comments | publish | open_studio."""
    if not text or not str(text).strip():
        return None

    raw = text.strip()
    tl = _norm(raw)

    if re.search(r"(примени|учти|исправь|внеси).*(коммент|правк|замечан)", tl):
        return {"action": "apply_comments", "task": raw}

    if re.search(r"(опублик|выгруз|handoff|экспорт).*(проект|studio|студи|макет|figma)?", tl):
        if any(w in tl for w in ("проект", "studio", "студи", "макет", "figma", "handoff", "опублик")):
            return {"action": "publish", "task": raw}

    if tl in (
        "новый проект", "новый макет", "studio", "sonya studio", "создай проект",
        "сделай проект", "новый ui проект", "создай макет",
    ):
        return {"action": "create", "title": "", "task": raw}

    if re.search(
        r"^(создай|сделай|сгенерируй|запусти)\s+.*"
        r"(проект|макет|landing|лендинг|dashboard|дашборд|форм|интерфейс|ui|кнопк|hero|компонент)",
        tl,
    ):
        return {"action": "create", "title": _extract_title(raw), "task": raw}

    if re.search(r"^(создай|сделай|сгенерируй|запусти)\s+(новый\s+)?(ui\s+)?(проект|макет|landing|лендинг)", tl):
        return {"action": "create", "title": _extract_title(raw), "task": raw}

    if _has_studio_context(tl):
        if not re.search(r"(коммент|опублик|publish|handoff|diff|верси)", tl):
            return {"action": "create", "title": _extract_title(raw), "task": raw}

    if re.search(r"открой.*(studio|студи)", tl):
        return {"action": "open_studio", "task": raw}

    return None


def is_studio_ui_task(text: str) -> bool:
    """Задача явно про UI — для PM-маршрутизации."""
    tl = _norm(text)
    if match_studio_intent(text):
        return True
    return any(h in tl for h in UI_HINTS)
