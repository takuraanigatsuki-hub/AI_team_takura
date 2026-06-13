"""Маршрутизация задач — презентация/таблица/3D не должны превращаться в сайт."""

from room.task_routing import (
    classify_task_kind,
    should_emit_react_preview,
    should_export_site,
    should_run_architecture_debate,
    should_sync_to_github,
)
from agents.pm_orchestrator import PMOrchestratorAgent
from agents.react_preview import generate_react_preview


def test_classify_presentation():
    assert classify_task_kind("Сделай презентацию для инвесторов") == "presentation"
    assert classify_task_kind("Нужен powerpoint про продукт") == "presentation"
    assert classify_task_kind("Экспорт в pptx") == "presentation"


def test_presentation_blocks_react_even_with_pm_subtask():
    assert should_emit_react_preview(
        "Сверстать сайт на React: landing page",
        "Сделай презентацию для инвесторов",
    ) is False


def test_classify_table():
    assert classify_task_kind("Сделай таблицу продаж") == "table"


def test_classify_model_3d():
    assert classify_task_kind("Создай 3D модель дома") == "model_3d"
    assert classify_task_kind("Спроектируй модель данных API") != "model_3d"


def test_classify_site():
    assert classify_task_kind("Сделай landing page") == "site"


def test_no_react_preview_for_presentation_or_3d():
    assert should_emit_react_preview("Сделай презентацию") is False
    assert should_emit_react_preview("Создай 3D модель") is False
    assert should_emit_react_preview("Сделай таблицу") is True
    assert should_emit_react_preview("Сделай landing") is True


def test_no_site_export_for_table():
    assert should_export_site("Сделай таблицу") is False
    assert should_export_site("Сделай landing page") is True


def test_debate_only_for_architecture():
    assert should_run_architecture_debate("Сделай landing page") is False
    assert should_run_architecture_debate("мне нужно создать таблицу для бухгалтерии") is False
    assert should_run_architecture_debate("Спроектируй API") is True


def test_accounting_table_routing():
    t = "мне нужно создать таблицу для бухгалтерии"
    assert classify_task_kind(t) == "table"
    pm = PMOrchestratorAgent()
    a = pm._analyze_and_assign(t, {})
    assert set(a.keys()) == {"frontend", "evaluator"}
    preview = generate_react_preview(t)
    assert preview["title"] == "Бухгалтерская таблица"
    assert "Дебет" in preview["code"]


def test_no_github_sync_for_table():
    t = "мне нужно создать таблицу для бухгалтерии"
    assert should_sync_to_github(t) is False


def test_pm_routes_presentation_to_presenter_only():
    pm = PMOrchestratorAgent()
    agents = {}
    a = pm._analyze_and_assign("Сделай презентацию о продукте", agents)
    assert "presenter" in a
    assert "frontend" not in a
    assert "backend" not in a


def test_pm_routes_table_to_frontend_not_full_stack():
    pm = PMOrchestratorAgent()
    a = pm._analyze_and_assign("Сделай таблицу с данными", {})
    assert set(a.keys()) == {"frontend", "evaluator"}


def test_table_preview_not_site():
    preview = generate_react_preview("Сделай таблицу продаж за Q1")
    assert preview["title"] == "Таблица данных"
    assert preview.get("is_site") is not True
    assert "<table" in preview["code"]


def test_pm_task_not_todo_list():
    preview = generate_react_preview("Виктор, распредели задачи по команде")
    assert preview["title"] != "Todo-лист"


def test_router_enforces_presenter_only():
    from room.llm_router import _enforce_kind_agents
    routed = _enforce_kind_agents(
        "presentation",
        {"frontend": "site", "presenter": "deck", "architect": "plan"},
        "Сделай презентацию",
    )
    assert set(routed.keys()) == {"presenter", "evaluator"}
    assert "frontend" not in routed


def test_router_enforces_modeler_only():
    from room.llm_router import _enforce_kind_agents
    routed = _enforce_kind_agents(
        "model_3d",
        {"frontend": "site", "modeler": "scene", "presenter": "deck"},
        "Создай 3D модель",
    )
    assert set(routed.keys()) >= {"modeler", "evaluator"}
    assert "frontend" not in routed
    assert "presenter" not in routed
