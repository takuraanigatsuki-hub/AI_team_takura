"""Тесты генерации React Preview."""

from agents.react_preview import generate_react_preview, _build_register_form


def test_register_form_preview_title():
    result = generate_react_preview("Создай форму регистрации в React")
    assert result["title"] == "Регистрация"


def test_register_form_has_fields():
    code = _build_register_form("Создай форму регистрации в React")
    assert "function App()" in code
    assert "/api/auth/register" in code
    assert "confirmPassword" in code
    assert "Пароли не совпадают" in code
    assert "Создать аккаунт" in code


def test_register_form_english_trigger():
    result = generate_react_preview("Build signup form for SaaS")
    assert result["title"] == "Регистрация"
    assert "RegistrationForm" not in result["code"]  # source file name, not in output


def test_login_still_works():
    result = generate_react_preview("Сделай форму логина")
    assert result["title"] == "Форма входа"
    assert "Вход" in result["code"]
