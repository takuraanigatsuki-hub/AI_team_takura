"""Smoke tests — базовые API endpoints."""

import httpx
import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient
    with TestClient(app, follow_redirects=True) as c:
        yield c


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "AI Team Room" in r.text
    assert 'id="features"' in r.text
    assert 'id="how"' in r.text
    assert 'id="pricing"' in r.text
    assert "lp-hero" in r.text
    assert "Регистрация" in r.text or "btnRegister" in r.text


def test_startup_landing(client):
    r = client.get("/startup")
    assert r.status_code == 200
    assert "LaunchKit" in r.text
    assert 'id="features"' in r.text
    assert 'id="cta"' in r.text
    assert "sl-hero" in r.text


def test_app_spa(client):
    r = client.get("/app", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers.get("location") == "/workspace"

    r = client.get("/workspace")
    assert r.status_code == 200
    assert 'id="appSidebar"' in r.text or "app-sidebar" in r.text
    assert "3D студия" in r.text or "3D Studio" in r.text
    assert "search.js" in r.text
    assert 'id="siteSearchInput"' not in r.text
    assert "SiteSearch" in r.text


def test_portal_spa(client):
    r = client.get("/portal")
    assert r.status_code == 200
    assert 'id="profileView"' in r.text
    assert 'APP_SHELL = \'portal\'' in r.text
    assert "three.min.js" not in r.text


def test_cabinet_redirect(client):
    r = client.get("/cabinet", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers.get("location") == "/portal?view=profile"


def test_auth_register_login(client):
    import uuid
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={
        "email": email,
        "password": "secret12",
        "name": "Tester",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["user"]["setup_complete"] is False
    cookie = r.cookies.get("ai_team_session")
    assert cookie

    r2 = client.get("/api/auth/me")
    assert r2.status_code == 200
    assert r2.json()["email"] == email

    r3 = client.post("/api/auth/setup", json={
        "name": "Tester",
        "goal": "Build SaaS",
        "default_view": "dashboard",
        "theme": "dark",
    })
    assert r3.status_code == 200
    assert r3.json()["user"]["setup_complete"] is True

    client.post("/api/auth/logout")
    r4 = client.get("/api/auth/me")
    assert r4.status_code == 401

    r5 = client.post("/api/auth/login", json={"email": email, "password": "secret12"})
    assert r5.status_code == 200


def test_ensure_owner(client):
    import uuid
    from room.user_auth import ensure_owner, login
    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    user = ensure_owner(email, "ownerpass1", "Boss")
    assert user["role"] == "owner"
    assert user["is_owner"] is True
    assert user["setup_complete"] is True
    assert "admin" in user["privileges"]
    assert "manage_users" in user["privileges"]
    assert user["subscription"]["tier"] == "owner"
    assert user["subscription"]["unlimited"] is True
    assert user["access_level"] == 5
    u2, _ = login(email, "ownerpass1")
    assert u2["role"] == "owner"


def test_agents(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    data = r.json()
    assert "agents" in data
    assert len(data["agents"]) >= 11


def test_templates(client):
    r = client.get("/api/templates")
    assert r.status_code == 200
    assert len(r.json().get("templates", [])) >= 3


def test_timeline(client):
    r = client.get("/api/timeline/replay?hours=1")
    assert r.status_code == 403


def test_kanban(client):
    r = client.get("/api/kanban")
    assert r.status_code == 200
    assert "columns" in r.json()


def test_projects(client):
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert "projects" in r.json()


def test_search(client):
    r = client.get("/api/search?q=")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert data["count"] == 0

    r2 = client.get("/api/search?q=test")
    assert r2.status_code == 200
    assert "results" in r2.json()


def test_integrations_status(client):
    r = client.get("/api/integrations/status")
    assert r.status_code == 200
    data = r.json()
    assert "llm" in data


def test_power_pack_endpoints(client):
    r = client.get("/api/project-memory")
    assert r.status_code == 200
    r = client.get("/api/sprint")
    assert r.status_code == 200
    r = client.get("/api/llm/usage")
    assert r.status_code == 401
    r = client.get("/api/artifact-templates")
    assert r.status_code == 200
    assert len(r.json().get("templates", [])) >= 5
    r = client.get("/api/mentions/aliases")
    assert r.status_code == 200
    assert "aliases" in r.json()


def test_telegram_status(client):
    r = client.get("/api/telegram/status")
    assert r.status_code == 401
