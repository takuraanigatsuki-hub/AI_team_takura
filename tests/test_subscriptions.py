"""Тесты подписок, баланса и уровней доступа."""

import uuid

import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient
    with TestClient(app, follow_redirects=True) as c:
        yield c


def _register(client, email=None, password="testpass1"):
    email = email or f"sub-{uuid.uuid4().hex[:8]}@test.com"
    r = client.post("/api/auth/register", json={"email": email, "password": password, "name": "Tester"})
    assert r.status_code == 200
    return email, r.cookies


def test_register_gets_free_tier_and_balance(client):
    _, cookies = _register(client)
    r = client.get("/api/auth/me", cookies=cookies)
    data = r.json()
    assert data["subscription"]["tier"] == "free"
    assert data["subscription"]["level"] == 1
    assert data["subscription"]["balance"] == 100
    assert data["access_level"] == 1


def test_subscription_plans_public(client):
    r = client.get("/api/subscription/plans")
    assert r.status_code == 200
    plans = r.json()["plans"]
    ids = [p["id"] for p in plans]
    assert "free" in ids
    assert "pro" in ids
    assert "owner" in ids


def test_free_cannot_access_sonya_studio(client):
    _, cookies = _register(client)
    r = client.get("/api/subscription/access?view=sonya-studio", cookies=cookies)
    assert r.json()["allowed"] is False


def test_upgrade_to_pro_unlocks_studio(client):
    _, cookies = _register(client)
    r = client.post("/api/subscription/upgrade", json={"tier": "pro"}, cookies=cookies)
    assert r.status_code == 200
    assert r.json()["user"]["subscription"]["tier"] == "pro"
    r2 = client.get("/api/subscription/access?view=sonya-studio", cookies=cookies)
    assert r2.json()["allowed"] is True


def test_owner_has_max_tier(client):
    from room.user_auth import ensure_owner

    email = f"owner-{uuid.uuid4().hex[:8]}@test.com"
    user = ensure_owner(email, "ownerpass1", "Boss")
    assert user["role"] == "owner"
    assert user["subscription"]["tier"] == "owner"
    assert user["subscription"]["unlimited"] is True
    assert user["access_level"] == 5
    assert user["subscription"]["balance_display"] == "∞"


def test_charge_deducts_balance(client):
    from room.user_auth import charge_user_action, _find_user

    _, cookies = _register(client)
    me = client.get("/api/auth/me", cookies=cookies).json()
    before = me["subscription"]["balance"]
    ok, msg = charge_user_action(me["id"], "task")
    assert ok is True
    raw = _find_user(me["id"])
    assert raw["balance"] == before - 5
