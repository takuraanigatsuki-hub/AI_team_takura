"""Роли и возможности каждого агента."""

AGENT_CAPABILITIES = {
    "pm": {
        "label": "PM & Оркестрация",
        "outputs": ["plan", "roadmap", "sprint"],
        "skills": ["планирование", "декомпозиция", "приоритеты", "метрики"],
        "can_code": False,
        "can_present": True,
        "can_3d": False,
    },
    "architect": {
        "label": "Архитектура",
        "outputs": ["architecture", "diagram", "adr", "code"],
        "skills": ["C4", "микросервисы", "DDD", "API design", "Python/Go"],
        "can_code": True,
        "can_present": True,
        "can_3d": False,
    },
    "backend": {
        "label": "Backend",
        "outputs": ["api", "service", "database", "code"],
        "skills": ["FastAPI", "PostgreSQL", "Redis", "async", "REST/gRPC"],
        "can_code": True,
        "can_present": False,
        "can_3d": False,
    },
    "frontend": {
        "label": "Frontend & UI",
        "outputs": ["ui", "react", "design", "site"],
        "skills": ["React", "TypeScript", "CSS", "Figma", "a11y"],
        "can_code": True,
        "can_present": False,
        "can_3d": False,
    },
    "qa": {
        "label": "QA & Тесты",
        "outputs": ["tests", "report", "checklist"],
        "skills": ["pytest", "Playwright", "k6", "TDD", "CI tests"],
        "can_code": True,
        "can_present": False,
        "can_3d": False,
    },
    "reviewer": {
        "label": "Code Review",
        "outputs": ["review", "refactor", "code"],
        "skills": ["SOLID", "clean code", "security review", "patterns"],
        "can_code": True,
        "can_present": False,
        "can_3d": False,
    },
    "doc_writer": {
        "label": "Документация",
        "outputs": ["doc", "readme", "presentation", "guide"],
        "skills": ["Markdown", "OpenAPI", "ADR", "technical writing"],
        "can_code": False,
        "can_present": True,
        "can_3d": False,
    },
    "devops": {
        "label": "DevOps",
        "outputs": ["infra", "docker", "ci", "code"],
        "skills": ["Docker", "K8s", "GitHub Actions", "Terraform"],
        "can_code": True,
        "can_present": False,
        "can_3d": False,
    },
    "cursor": {
        "label": "Cursor SDK",
        "outputs": ["code", "refactor", "feature"],
        "skills": ["AI coding", "cloud agents", "GitHub PR", "refactoring"],
        "can_code": True,
        "can_present": False,
        "can_3d": False,
    },
    "presenter": {
        "label": "Презентации",
        "outputs": ["presentation", "slides", "pitch"],
        "skills": ["storytelling", "slides", "pitch deck", "Keynote-style HTML"],
        "can_code": False,
        "can_present": True,
        "can_3d": False,
    },
    "modeler": {
        "label": "3D & Визуал",
        "outputs": ["model_3d", "scene", "threejs"],
        "skills": ["Three.js", "glTF", "Blender workflow", "WebGL scenes"],
        "can_code": True,
        "can_present": False,
        "can_3d": True,
    },
    "evaluator": {
        "label": "Оценка навыков",
        "outputs": ["review", "evaluation", "feedback"],
        "skills": ["quality", "coaching", "skill scoring", "acceptance"],
        "can_code": False,
        "can_present": True,
        "can_3d": False,
    },
}


def get_capabilities(agent_id: str) -> dict:
    return AGENT_CAPABILITIES.get(agent_id, {
        "label": agent_id,
        "outputs": ["project"],
        "skills": [],
        "can_code": True,
        "can_present": False,
        "can_3d": False,
    })


def detect_artifact_type(agent_id: str, task_text: str) -> str:
    from room.task_routing import classify_task_kind

    t = task_text.lower()
    kind = classify_task_kind(task_text)
    caps = get_capabilities(agent_id)

    if kind == "presentation" or agent_id == "presenter":
        return "presentation"
    if kind == "model_3d" or agent_id == "modeler":
        return "model_3d"
    if kind == "table":
        return "table"
    if kind == "site" or (agent_id == "frontend" and kind == "ui"):
        return "ui"
    if kind == "api" or agent_id in ("backend", "cursor"):
        return "code"
    if kind == "architecture" or agent_id == "architect":
        return "architecture"
    if kind == "tests" or agent_id == "qa":
        return "tests"
    if kind == "document" or agent_id == "doc_writer":
        return "document"
    if kind == "infra" or agent_id == "devops":
        return "infra"
    if kind == "evaluator" or agent_id == "evaluator":
        return "review"
    if agent_id == "reviewer":
        return "review"
    if agent_id == "pm":
        return "plan"
    if agent_id == "frontend" or any(w in t for w in ["ui", "react", "landing", "сайт", "интерфейс", "верст"]):
        return "ui"
    return caps.get("outputs", ["project"])[0]
