"""Тесты распознавания русских команд Sonya Studio."""

from integrations.sonya_commands import match_studio_intent


def test_create_russian_commands():
    cases = [
        "создай новый проект",
        "Сделай landing для SaaS",
        "Соня, создай макет dashboard",
        "новый ui проект в studio",
        "@соня создай форму входа",
    ]
    for text in cases:
        intent = match_studio_intent(text.replace("@соня ", ""))
        assert intent is not None, text
        assert intent["action"] == "create", text


def test_apply_and_publish_russian():
    assert match_studio_intent("примени комментарии к проекту")["action"] == "apply_comments"
    assert match_studio_intent("опубликуй проект в figma")["action"] == "publish"


def test_unrelated_task_not_studio():
    assert match_studio_intent("напиши unit-тесты для api") is None


def test_title_from_task_not_page_fragment():
    from integrations.sonya_commands import title_from_task
    assert title_from_task("Сделай landing page для моего продукта") == "Landing · для моего продукта"
    assert title_from_task("Сделай landing для SaaS") == "Landing · для saas"
    assert title_from_task("Создай dashboard для аналитики") == "Dashboard для аналитики"
