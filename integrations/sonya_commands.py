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


def _extract_title(text: str) -> str:
    m = re.search(r"[«\"']([^»\"']+)[»\"']", text)
    if m:
        return m.group(1).strip()[:80]
    m = re.search(r"(?:проект|макет|landing|лендинг)\s+[«\"']?([^,.!»\"']{3,60})", text, re.I)
    if m:
        return m.group(1).strip()
    return ""


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
