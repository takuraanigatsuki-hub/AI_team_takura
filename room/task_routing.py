"""Классификация задач — кому что поручать (не всё в landing)."""


def classify_task_kind(text: str) -> str:
    """Тип артеfactа/работы: site, ui, table, presentation, model_3d, api, …"""
    t = (text or "").strip().lower()
    if not t:
        return "generic"

    if any(w in t for w in ["презентац", "slides", "pitch", "слайд", "deck", "доклад", "keynote"]):
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


def should_emit_react_preview(task_text: str) -> bool:
    """Соня не должна открывать React Preview для презентаций и 3D."""
    return classify_task_kind(task_text) in ("site", "ui", "table")


def should_export_site(task_text: str) -> bool:
    return classify_task_kind(task_text) == "site"


def should_run_architecture_debate(task_text: str) -> bool:
    """Debate только для явной архитектуры/API — не для таблиц, UI, презентаций."""
    return classify_task_kind(task_text) in ("architecture", "api")
