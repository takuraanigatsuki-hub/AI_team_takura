"""Unit tests — React Preview generation and Figma → React."""

from agents.react_preview import (
    generate_react_preview,
    is_site_task,
    is_production_polish_task,
    is_figma_import_task,
    is_figma_refine_task,
    apply_figma_tokens,
    polish_preview,
)
from integrations.figma_client import parse_figma_url
from integrations.figma_react import (
    build_launchkit_code,
    generate_react_from_figma,
    refine_react_from_figma,
    resolve_component_for_file,
)

FIGMA_URL = "https://www.figma.com/site/uYRfrETGR8pcwChwLtJ6Ua/Untitled?t=S7zOAy3vHRn3HWqR-0"


def test_login_form_preview():
    preview = generate_react_preview("сделай форму логина")
    assert preview["title"] == "Форма входа"
    assert "function App()" in preview["code"]
    assert "useState" in preview["code"]


def test_site_task_detection():
    assert is_site_task("создай landing page для стартапа") is True
    assert is_site_task("сделай кнопку") is False


def test_production_polish_task():
    assert is_production_polish_task("Доработай React Preview до production-ready UI") is True
    preview = generate_react_preview("Доработай React Preview до production-ready UI")
    assert preview.get("polished") is True
    assert "const ds = {" in preview["code"]
    assert preview["title"].startswith("Production UI")


def test_apply_figma_tokens():
    base = generate_react_preview("кнопка")
    figma = {"summary": {"colors": ["#ff0000", "#00ff00", "#0000ff"]}}
    out = apply_figma_tokens(base, figma)
    assert out.get("figma_applied") is True
    assert "#ff0000" in out["code"]
    assert "figmaTokens" in out["code"]


def test_polish_preview_preserves_app():
    base = {"title": "Test", "code": "function App(){ return <div>Hi</div>; }"}
    out = polish_preview(base)
    assert "function App()" in out["code"]
    assert out.get("polished") is True


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


def test_figma_refine_task_detection():
    task = "Доработай React UI точнее по импортированному Figma-макету: цвета, spacing, типографика"
    assert is_figma_refine_task(task) is True


def test_refine_launchkit_uses_tokens_and_spacing():
    figma_result = {
        "file_key": "uYRfrETGR8pcwChwLtJ6Ua",
        "url": FIGMA_URL,
        "summary": {
            "file_name": "Untitled",
            "colors": ["#6c63ff", "#56cfe1", "#0b0d12", "#e8eaef", "#8b93a7"],
            "fonts": ["Inter 800"],
            "frames": [{"name": "Hero"}],
        },
    }
    task = "Доработай React UI точнее по импортированному Figma-макету: цвета, spacing, типографика"
    preview = refine_react_from_figma(figma_result, task=task)
    assert preview["figma_refined"] is True
    assert preview["title"] == "LaunchKit · Figma (refined)"
    assert "tokens.space" in preview["code"]
    assert "fontSize.hero" in preview["code"]
    assert "statItem" in preview["code"]
    assert "gridTemplateColumns: '1fr 1fr'" in preview["code"]
    assert "#6c63ff" in preview["code"]
    assert "'Inter'" in preview["code"]
