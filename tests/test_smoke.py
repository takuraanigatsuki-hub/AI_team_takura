"""Smoke tests — базовые API endpoints."""

import httpx
import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient
    with TestClient(app) as c:
        yield c


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "AI Team Room" in r.text


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
    assert r.status_code == 200
    assert "events" in r.json()


def test_kanban(client):
    r = client.get("/api/kanban")
    assert r.status_code == 200
    assert "columns" in r.json()


def test_projects(client):
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert "projects" in r.json()


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
    assert r.status_code == 200
    r = client.get("/api/artifact-templates")
    assert r.status_code == 200
    assert len(r.json().get("templates", [])) >= 5
    r = client.get("/api/mentions/aliases")
    assert r.status_code == 200
    assert "aliases" in r.json()
