"""Тесты REST API v1 — auth, CRUD items, OpenAPI."""

from __future__ import annotations

import uuid

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def api_client(monkeypatch):
    import os

    from api.config import get_settings
    from api.database import create_tables, reset_engine

    db_url = "sqlite+aiosqlite:///:memory:"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("API_JWT_SECRET", "test-secret-key")
    get_settings.cache_clear()
    reset_engine(db_url)

    import asyncio

    asyncio.run(create_tables())

    from app import app

    with TestClient(app, follow_redirects=True) as client:
        yield client

    import asyncio

    from api.database import get_engine

    try:
        asyncio.run(get_engine().dispose())
    except Exception:
        pass
    reset_engine()
    get_settings.cache_clear()


def _register(client: TestClient, email: str | None = None, password: str = "secret12") -> dict:
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Tester"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_openapi_docs(api_client):
    response = api_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/items" in paths
    assert "/api/v1/items/{item_id}" in paths


def test_auth_register_login_me(api_client):
    email = f"auth-{uuid.uuid4().hex[:8]}@example.com"
    reg = _register(api_client, email=email)
    assert reg["user"]["email"] == email
    assert reg["access_token"]
    assert reg["token_type"] == "bearer"

    me = api_client.get("/api/v1/auth/me", headers=_auth_headers(reg["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == email

    login = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "secret12"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    bad = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password"},
    )
    assert bad.status_code == 401


def test_auth_requires_bearer(api_client):
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_items_crud(api_client):
    reg = _register(api_client)
    headers = _auth_headers(reg["access_token"])

    create = api_client.post(
        "/api/v1/items",
        headers=headers,
        json={"title": "First item", "description": "Demo", "status": "active"},
    )
    assert create.status_code == 201
    item = create.json()
    assert item["title"] == "First item"
    assert item["status"] == "active"
    item_id = item["id"]

    listing = api_client.get("/api/v1/items", headers=headers)
    assert listing.status_code == 200
    data = listing.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1

    fetched = api_client.get(f"/api/v1/items/{item_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == item_id

    updated = api_client.patch(
        f"/api/v1/items/{item_id}",
        headers=headers,
        json={"title": "Updated", "status": "done"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated"
    assert updated.json()["status"] == "done"

    deleted = api_client.delete(f"/api/v1/items/{item_id}", headers=headers)
    assert deleted.status_code == 204

    missing = api_client.get(f"/api/v1/items/{item_id}", headers=headers)
    assert missing.status_code == 404


def test_items_are_scoped_per_user(api_client):
    user_a = _register(api_client)
    user_b = _register(api_client)

    created = api_client.post(
        "/api/v1/items",
        headers=_auth_headers(user_a["access_token"]),
        json={"title": "Private"},
    )
    item_id = created.json()["id"]

    forbidden = api_client.get(
        f"/api/v1/items/{item_id}",
        headers=_auth_headers(user_b["access_token"]),
    )
    assert forbidden.status_code == 404

    empty = api_client.get("/api/v1/items", headers=_auth_headers(user_b["access_token"]))
    assert empty.json()["total"] == 0


def test_duplicate_email_rejected(api_client):
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    _register(api_client, email=email)
    again = api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret12", "name": "Dup"},
    )
    assert again.status_code == 400
