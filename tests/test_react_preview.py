"""Тесты генерации React Preview."""

from agents.react_preview import generate_react_preview, generate_react_from_figma, is_figma_import_task
from integrations.figma_fixtures import get_fixture


def test_figma_import_task_detection():
    assert is_figma_import_task("Импортируй Figma и создай React UI")
    assert not is_figma_import_task("Сделай счётчик")


def test_figma_preview_via_generate_react_preview():
    figma = get_fixture("uYRfrETGR8pcwChwLtJ6Ua")
    result = generate_react_preview("UI по макету Figma", figma_result=figma)
    assert result["figma_imported"] is True
    assert "Imported from Figma" in result["code"]


def test_login_still_works():
    result = generate_react_preview("Сделай форму логина")
    assert result["title"] == "Форма входа"
    assert "Вход" in result["code"]
