"""Sonya Design Studio API tests."""

import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient
    with TestClient(app, follow_redirects=True) as c:
        yield c


def test_sonya_project_lifecycle(client):
    from integrations.sonya_studio import get_project, list_projects

    r = client.post("/api/sonya/projects", json={
        "title": "Test Landing",
        "task": "Landing page для SaaS с hero блоком",
    })
    assert r.status_code == 200
    pid = r.json()["project"]["id"]
    assert pid

    r2 = client.get(f"/api/sonya/projects/{pid}")
    assert r2.status_code == 200
    data = r2.json()
    assert data["current_version"]["react_code"]
    assert "function App" in data["current_version"]["react_code"]

    r3 = client.post(f"/api/sonya/projects/{pid}/comments", json={
        "text": "Сделай кнопку CTA зелёной",
        "x": 0.7,
        "y": 0.8,
    })
    assert r3.status_code == 200
    assert r3.json()["comment"]["status"] == "open"

    r4 = client.post(f"/api/sonya/projects/{pid}/apply-comments")
    assert r4.status_code == 200
    updated = r4.json()["project"]
    assert updated["current_version"]["version_num"] >= 2
    assert updated["open_comments"] == 0

    r5 = client.post(f"/api/sonya/projects/{pid}/publish", json={"figma_url": ""})
    assert r5.status_code == 200
    pub = r5.json()["project"]
    assert pub["status"] == "published"
    assert pub["figma_handoff"]["css_tokens"]

    assert any(p["id"] == pid for p in list_projects())


def test_sonya_create_by_agent(client):
    r = client.post("/api/sonya/projects/create-new")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["project"]["id"]


def test_studio_store_offline():
    from integrations.sonya_studio import create_project, add_comment, publish_project, build_revision_task

    p = create_project(title="Offline", task="Кнопка и форма входа")
    pid = p["id"]
    add_comment(pid, text="Увеличь заголовок", x=0.5, y=0.2, author="Tester")
    full = __import__("integrations.sonya_studio", fromlist=["get_project"]).get_project(pid)
    task = build_revision_task(full)
    assert "Увеличь заголовок" in task
    pub = publish_project(pid)
    assert pub["status"] == "published"
