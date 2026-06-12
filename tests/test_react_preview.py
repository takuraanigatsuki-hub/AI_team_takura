"""Unit tests — React Preview generation."""

from agents.react_preview import (
    generate_react_preview,
    is_site_task,
    is_production_polish_task,
    apply_figma_tokens,
    polish_preview,
)


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
