"""Классификация задач — кому что поручать (не всё в landing)."""


def classify_task_kind(text: str) -> str:
    """Тип артеfactа/работы: site, ui, table, presentation, model_3d, api, …"""
    t = (text or "").strip().lower()
    if not t:
        return "generic"

    if any(w in t for w in [
        "презентац", "slides", "pitch", "слайд", "deck", "доклад", "keynote",
        "powerpoint", "power point", "pptx", " ppt ", "пауэрпоинт", "поверпоинт",
    ]):
        return "presentation"

    if any(w in t for w in ["3d", "3д", "three.js", "threejs", "glb", "gltf", "blender", "webgl"]):
        return "model_3d"
    if "модел" in t and any(w in t for w in ["3d", "3д", "three", "сцен", "объект", "glb", "визуал", "threejs"]):
        return "model_3d"

    if any(w in t for w in [
        "таблиц", "таблицу", "таблицы", "table", "excel", "spreadsheet", "csv",
        "data grid", "бухгалтер", "учёт", "учет", "accounting", "ledger",
    ]):
        return "table"

    if any(w in t for w in [
        "сайт", "website", "веб-сайт", "web-сайт", "web site",
        "лендинг", "landing", "портал", "webpage", "веб-страниц", "веб приложен",
    ]):
        return "site"

    if any(w in t for w in ["api", "бэкенд", "backend", "сервер", "endpoint", "fastapi", "rest "]):
        return "api"

    if any(w in t for w in ["архитектур", "diagram", "c4", "adr", "микросервис"]):
        return "architecture"

    if any(w in t for w in ["тест", "test", "pytest", "playwright", "e2e"]):
        return "tests"

    if any(w in t for w in ["docker", "deploy", "kubernetes", "ci/cd", "devops", "инфраструктур"]):
        return "infra"

    if any(w in t for w in ["документ", "readme", "описан", "инструкци"]):
        return "document"

    if any(w in t for w in [
        "интерфейс", "ui", "ux", "фронтенд", "frontend", "компонент", "react",
        "верст", "кнопк", "форм", "дашборд", "dashboard", "css", "hero", "макет",
    ]):
        return "ui"

    return "generic"


def resolve_task_intent(subtask: str, original_task: str = "") -> str:
    """Классификация по исходной задаче пользователя, не по формулировке PM."""
    original = (original_task or "").strip()
    if original:
        kind = classify_task_kind(original)
        if kind != "generic":
            return kind
    return classify_task_kind(subtask)


def should_emit_react_preview(task_text: str, original_task: str = "") -> bool:
    """Соня не должна открывать React Preview для презентаций и 3D."""
    kind = resolve_task_intent(task_text, original_task)
    return kind in ("site", "ui", "table")


def wants_powerpoint_file(task_text: str, original_task: str = "") -> bool:
    return resolve_task_intent(task_text, original_task) == "presentation"


def should_export_site(task_text: str) -> bool:
    return classify_task_kind(task_text) == "site"


def should_run_architecture_debate(task_text: str) -> bool:
    """Debate только для явной архитектуры/API — не для таблиц, UI, презентаций."""
    return classify_task_kind(task_text) in ("architecture", "api")


def should_sync_to_github(task_text: str) -> bool:
    """GitHub / Cloud Agent — только для явных coding-задач, не для таблиц/UI/презентаций."""
    from config import config

    if not config.get("github_sync_on_tasks", False):
        return False
    kind = classify_task_kind(task_text)
    if kind in ("table", "presentation", "model_3d", "site", "ui", "document"):
        return False
    t = (task_text or "").lower()
    code_hints = [
        "github", "git ", "pull request", "pr ", "cursor", "рефактор", "refactor",
        "implement", "backend", "endpoint", "fastapi", "api ", "код", "code ",
        "deploy", "docker", "kubernetes", "микросервис", "архитектур",
    ]
    if kind in ("api", "architecture", "infra", "tests"):
        return True
    return any(h in t for h in code_hints)


def should_use_m365(task_text: str) -> bool:
    """Microsoft 365 — таблицы, презентации, документы."""
    kind = classify_task_kind(task_text)
    return kind in ("table", "presentation", "document")


def delivery_channel(task_text: str) -> str:
    """Куда отдавать результат: m365, preview, github."""
    if should_use_m365(task_text):
        return "m365"
    kind = classify_task_kind(task_text)
    if kind in ("site", "ui", "table"):
        return "preview"
    if should_sync_to_github(task_text):
        return "github"
    return "chat"
