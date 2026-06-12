"""Тесты генерации React Preview и Figma → React."""

from agents.react_preview import generate_react_preview, is_figma_import_task
from integrations.figma_client import parse_figma_url
from integrations.figma_react import (
    build_launchkit_code,
    generate_react_from_figma,
    resolve_component_for_file,
)


FIGMA_URL = "https://www.figma.com/site/uYRfrETGR8pcwChwLtJ6Ua/Untitled?t=S7zOAy3vHRn3HWqR-0"


def test_parse_figma_site_url():
    parsed = parse_figma_url(FIGMA_URL)
    assert parsed is not None
    assert parsed["file_key"] == "uYRfrETGR8pcwChwLtJ6Ua"
    assert parsed["file_type"] == "site"


def test_figma_import_task_detection():
    task = f"Импортируй Figma и создай React UI: {FIGMA_URL}"
    assert is_figma_import_task(task) is True


def test_known_figma_component_mapping():
    assert resolve_component_for_file("uYRfrETGR8pcwChwLtJ6Ua") == "LaunchKitLanding.jsx"


def test_launchkit_react_from_figma():
    figma_result = {
        "file_key": "uYRfrETGR8pcwChwLtJ6Ua",
        "url": FIGMA_URL,
        "summary": {
            "file_name": "Untitled",
            "colors": ["#6c63ff", "#56cfe1", "#0b0d12"],
            "fonts": ["Inter 700"],
            "frames": [{"name": "Hero"}, {"name": "Features"}],
        },
    }
    preview = generate_react_from_figma(figma_result, task="Импорт Figma LaunchKit")
    assert preview["title"] == "LaunchKit · Figma → React"
    assert preview["is_site"] is True
    assert "function App()" in preview["code"]
    assert "LaunchKit" in preview["code"]
    assert "Запустите продукт" in preview["code"]
    assert "Figma → React" in preview["code"]


def test_launchkit_code_has_interactivity():
    code = build_launchkit_code("Тестовая задача")
    assert "useState" in code
    assert "Получить доступ" in code
    assert "Возможности" in code
    assert "chartHeights" in code


def test_figma_task_preview_without_api():
    """Без API-токена generate_react_preview использует известный маппинг."""
    task = f"Импортируй Figma и создай React UI: {FIGMA_URL}"
    result = generate_react_preview(task)
    assert result["title"] == "LaunchKit · Figma → React"
    assert result["is_site"] is True
    assert "LaunchKit" in result["code"]
