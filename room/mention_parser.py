"""@mention парсер — @соня @pm @все"""

AGENT_ALIASES = {
    "pm": "pm", "виктор": "pm",
    "architect": "architect", "алекс": "architect", "архитектор": "architect",
    "backend": "backend", "макс": "backend", "бэкенд": "backend",
    "frontend": "frontend", "sonya": "frontend", "соня": "frontend", "сonya": "frontend",
    "фронт": "frontend", "фронтенд": "frontend", "ui": "frontend", "ux": "frontend",
    "дизайн": "frontend", "верстка": "frontend", "макет": "frontend",
    "qa": "qa", "рита": "qa",
    "reviewer": "reviewer", "дэн": "reviewer", "ревьюер": "reviewer",
    "doc_writer": "doc_writer", "лена": "doc_writer", "docs": "doc_writer",
    "devops": "devops", "кирилл": "devops",
    "cursor": "cursor", "лео": "cursor",
    "presenter": "presenter", "ника": "presenter", "презентац": "presenter",
    "modeler": "modeler", "зоя": "modeler", "3d": "modeler",
    "все": "all", "all": "all", "команда": "all",
}


def parse_mentions(text: str) -> tuple[str, str | None]:
    """Возвращает (очищенный текст, target agent_id или None)."""
    import re
    target = None
    cleaned = text
    for match in re.finditer(r"@([\w\u0400-\u04FF]+)", text, re.IGNORECASE):
        alias = match.group(1).lower()
        agent_id = AGENT_ALIASES.get(alias)
        if agent_id:
            target = agent_id
            cleaned = cleaned.replace(match.group(0), "").strip()
    return cleaned, target


def list_aliases() -> dict:
    return AGENT_ALIASES
