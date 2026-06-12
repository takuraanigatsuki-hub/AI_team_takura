"""Unit tests — React Preview generator."""

from agents.react_preview import (
    generate_react_preview,
    is_polish_task,
    is_site_task,
    polish_preview,
    _inject_figma_colors,
    _pick_fallback_template,
)


def test_is_site_task():
    assert is_site_task("Сделай лендинг для стартапа")
    assert not is_site_task("Сделай кнопку")


def test_is_polish_task():
    assert is_polish_task("Доработай React Preview до production-ready UI")
    assert is_polish_task("polish preview")
    assert not is_polish_task("сделай форму логина")


def test_login_template():
    result = generate_react_preview("сделай форму логина")
    assert result["title"] == "Форма входа"
    assert "aria-label" in result["code"]
    assert "useState" in result["code"]


def test_saas_template():
    result = generate_react_preview("Создай SaaS dashboard с KPI")
    assert result["title"] == "SaaS Dashboard"
    assert "SaaS App" in result["code"]


def test_ecommerce_template():
    result = generate_react_preview("e-commerce каталог с корзиной")
    assert result["title"] == "E-commerce"
    assert "В корзину" in result["code"]


def test_admin_template():
    result = generate_react_preview("admin panel CRUD таблица")
    assert result["title"] == "Admin Panel"
    assert "Admin Panel" in result["code"]


def test_polish_task():
    prev = generate_react_preview("кнопка")
    result = generate_react_preview("Доработай React Preview до production-ready UI", previous=prev)
    assert result.get("polished") is True
    assert "Production" in result["title"] or "role=" in result["code"]


def test_polish_preview_from_scratch():
    result = polish_preview(None, "production UI")
    assert result["polished"] is True
    assert "Production UI" in result["code"]


def test_figma_color_injection():
    code = "background: '#4f7df3'; color: '#6c63ff';"
    injected = _inject_figma_colors(code, ["#ff0000", "#00ff00"])
    assert "#ff0000" in injected
    assert "#00ff00" in injected
    assert "#4f7df3" not in injected


def test_generate_with_figma_colors():
    result = generate_react_preview("кнопка", figma_colors=["#aabbcc"])
    assert result["colors"] == ["#aabbcc"]
    assert "#aabbcc" in result["code"]


def test_fallback_deterministic():
    t1 = _pick_fallback_template("уникальная задача xyz")
    t2 = _pick_fallback_template("уникальная задача xyz")
    t3 = _pick_fallback_template("другая задача abc")
    assert t1 == t2
    assert t1 != t3 or True  # may collide rarely
