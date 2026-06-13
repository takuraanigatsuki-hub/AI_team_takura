"""Маршрутизация задач + корректность артеfactов (презентация, 3D, таблица, сайт)."""

import asyncio
from types import SimpleNamespace

import pytest

from agents.artifact_producer import produce_artifact
from agents.pm_orchestrator import PMOrchestratorAgent
from room.agent_capabilities import detect_artifact_type
from room.llm_router import _enforce_kind_agents, _keyword_route
from room.role_triage import run_role_triage
from room.task_routing import (
    classify_task_kind,
    delivery_channel,
    resolve_task_intent,
    should_emit_react_preview,
)


class _FakeAgent:
    def __init__(self, agent_id: str, name: str = "", emoji: str = ""):
        self.agent_id = agent_id
        self.name = name or agent_id
        self.emoji = emoji or "🤖"
        self.learned_topics = []


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("task,expected", [
    ("Сделай презентацию для инвесторов", "presentation"),
    ("Нужен powerpoint pitch deck", "presentation"),
    ("Создай 3D модель дома", "model_3d"),
    ("Three.js сцена продукта", "model_3d"),
    ("Сделай таблицу продаж", "table"),
    ("Сделай landing page", "site"),
])
def test_classify_task_kinds(task, expected):
    assert classify_task_kind(task) == expected


def test_resolve_intent_from_original_task():
    subtask = "Сверстать сайт на React: landing page"
    original = "Сделай презентацию PowerPoint про продукт"
    assert resolve_task_intent(subtask, original) == "presentation"
    assert should_emit_react_preview(subtask, original) is False


def test_pm_assignments_by_kind():
    pm = PMOrchestratorAgent()
    pres = pm._analyze_and_assign("Сделай презентацию о продукте", {})
    assert set(pres.keys()) == {"presenter", "evaluator"}
    assert "frontend" not in pres

    model = pm._analyze_and_assign("Создай 3D модель персонажа", {})
    assert "modeler" in model
    assert "frontend" not in model

    table = pm._analyze_and_assign("Сделай таблицу Excel", {})
    assert set(table.keys()) == {"frontend", "evaluator"}

    site = pm._analyze_and_assign("Сделай landing page", {})
    assert "frontend" in site
    assert "presenter" not in site


def test_router_enforces_kind():
    pres = _enforce_kind_agents(
        "presentation",
        {"frontend": "site", "presenter": "deck", "architect": "x"},
        "Презентация",
    )
    assert set(pres.keys()) == {"presenter", "evaluator"}

    model = _enforce_kind_agents(
        "model_3d",
        {"frontend": "site", "modeler": "3d", "reviewer": "check"},
        "3D модель",
    )
    assert "modeler" in model
    assert "reviewer" in model
    assert "frontend" not in model

    site = _enforce_kind_agents(
        "site",
        {"presenter": "wrong", "frontend": "react", "modeler": "wrong"},
        "Landing",
    )
    assert "frontend" in site
    assert "presenter" not in site
    assert "modeler" not in site


def test_keyword_route_presentation():
    pm = PMOrchestratorAgent()
    pm_assign = pm._analyze_and_assign("Сделай pptx для стартапа", {})
    routed = _keyword_route("Сделай pptx для стартапа", pm_assign)
    assert "presenter" in routed
    assert "frontend" not in routed


def test_detect_artifact_type_with_pm_subtask():
    sub = "Создать презентацию (слайды): pitch"
    orig = "Сделай презентацию для инвесторов"
    assert detect_artifact_type("presenter", sub, orig) == "presentation"

    sub3d = "Создать 3D-сцену: дом"
    orig3d = "Создай 3D модель дома"
    assert detect_artifact_type("modeler", sub3d, orig3d) == "model_3d"

    # PM subtask alone still works for presenter/modeler agent id
    assert detect_artifact_type("presenter", sub, "") == "presentation"
    assert detect_artifact_type("modeler", sub3d, "") == "model_3d"


def test_delivery_channels():
    assert delivery_channel("Сделай презентацию") == "m365"
    assert delivery_channel("Создай 3D модель") == "preview"
    assert delivery_channel("Сделай landing") == "preview"
    assert delivery_channel("Сверстать React", "Сделай презентацию") == "m365"


def test_produce_presentation_artifact():
    agent = _FakeAgent("presenter", "Ника", "📽️")
    art = _run(produce_artifact(
        agent,
        "Создать презентацию (слайды): pitch deck",
        "## Проблема\n- Боль\n\n## Решение\n- Продукт",
        original_task="Сделай презентацию для инвесторов",
    ))
    assert art["type"] == "presentation"
    assert "presentation.pptx" in art["files"]
    assert art["files"]["presentation.pptx"][:2] == b"PK"
    assert "slide" in art["preview_html"].lower()
    assert "React" not in art["preview_html"]
    assert art["task"] == "Сделай презентацию для инвесторов"


def test_produce_model_3d_artifact():
    agent = _FakeAgent("modeler", "Зоя", "🧊")
    art = _run(produce_artifact(
        agent,
        "Создать 3D-сцену: дом",
        "Three.js scene",
        original_task="Создай 3D модель дома",
    ))
    assert art["type"] == "model_3d"
    assert "scene.html" in art["files"]
    assert "THREE." in art["preview_html"]
    assert "landing" not in art["preview_html"].lower() or "THREE" in art["preview_html"]


def test_produce_table_artifact():
    agent = _FakeAgent("frontend", "Соня", "🎨")
    art = _run(produce_artifact(
        agent,
        "Сверстать таблицу данных (React, не landing): продажи",
        "Таблица готова",
        original_task="Сделай таблицу продаж Q1",
    ))
    assert art["type"] == "table"
    assert "<table" in art["preview_html"]
    assert art.get("preview_html") and "MySite" not in art["preview_html"]


def test_produce_ui_site_artifact():
    agent = _FakeAgent("frontend", "Соня", "🎨")
    art = _run(produce_artifact(
        agent,
        "Сверстать сайт на React: SaaS landing",
        "function App(){ return <div>SaaS</div>; }",
        original_task="Сделай landing page для SaaS",
    ))
    assert art["type"] == "ui"
    assert "component.jsx" in art["files"]


def test_role_triage_filters_wrong_agents():
    pm = PMOrchestratorAgent()
    assignments = pm._analyze_and_assign("Сделай презентацию", {})
    assignments["frontend"] = "Сверстать сайт на React (ошибка)"
    agents = {
        "presenter": SimpleNamespace(name="Ника", emoji="📽️"),
        "evaluator": SimpleNamespace(name="Ева", emoji="🎓"),
        "frontend": SimpleNamespace(name="Соня", emoji="🎨"),
    }

    async def _noop(*args, **kwargs):
        return None

    rm = SimpleNamespace(broadcast_work=_noop)
    accepted = _run(run_role_triage(
        "Сделай презентацию", assignments, agents, rm, silent=True,
    ))
    assert "presenter" in accepted
    assert "frontend" not in accepted
