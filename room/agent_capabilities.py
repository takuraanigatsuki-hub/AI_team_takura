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
    t = task_text.lower()
    caps = get_capabilities(agent_id)

    if agent_id == "presenter" or any(w in t for w in ["презентац", "slides", "pitch", "слайд", "deck"]):
        return "presentation"
    if agent_id == "modeler" or any(w in t for w in ["3d", "3д", "three.js", "threejs", "модел", "glb", "gltf", "blender"]):
        return "model_3d"
    if agent_id == "frontend" or any(w in t for w in ["ui", "react", "landing", "сайт", "интерфейс", "верст"]):
        return "ui"
    if agent_id in ("backend", "cursor") or any(w in t for w in ["api", "backend", "endpoint", "сервер"]):
        return "code"
    if agent_id == "architect" or any(w in t for w in ["архитектур", "diagram", "c4", "adr"]):
        return "architecture"
    if agent_id == "qa" or any(w in t for w in ["тест", "test", "pytest", "playwright"]):
        return "tests"
    if agent_id == "doc_writer" or any(w in t for w in ["readme", "документ", "guide"]):
        return "document"
    if agent_id == "devops" or any(w in t for w in ["docker", "k8s", "deploy", "ci/cd"]):
        return "infra"
    if agent_id == "reviewer":
        return "review"
    if agent_id == "pm":
        return "plan"
    return caps.get("outputs", ["project"])[0]
