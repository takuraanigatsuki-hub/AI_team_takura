"""Доступ к техническим API — только для админов."""

import uuid

import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient
    with TestClient(app, follow_redirects=True) as c:
        yield c


def _register_member(client):
    email = f"member-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={
        "email": email,
        "password": "secret12",
        "name": "Member",
    })
    assert r.status_code == 200
    client.post("/api/auth/setup", json={
        "name": "Member",
        "goal": "Test",
        "default_view": "dashboard",
        "theme": "dark",
    })
    return email


def test_config_public_subset_for_member(client):
    _register_member(client)
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    assert "llm_configured" in data
    assert "cursor_repo_url" not in data
    assert "cursor_enabled" not in data
    assert "m365_configured" not in data


def test_git_status_forbidden_for_member(client):
    _register_member(client)
    r = client.get("/api/git/status")
    assert r.status_code == 403


def test_cursor_status_forbidden_for_member(client):
    _register_member(client)
    r = client.get("/api/cursor/status")
    assert r.status_code == 403


def test_config_post_platform_fields_forbidden_for_member(client):
    _register_member(client)
    r = client.post("/api/config", json={"cursor_repo_url": "https://github.com/evil/repo"})
    assert r.status_code == 403


def test_telegram_status_requires_admin(client):
    r = client.get("/api/telegram/status")
    assert r.status_code == 401

    _register_member(client)
    r2 = client.get("/api/telegram/status")
    assert r2.status_code == 403
