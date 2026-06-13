"""Login by username and unique display names."""

import uuid

import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient
    with TestClient(app, follow_redirects=True) as c:
        yield c


def test_register_with_username_and_unique_name(client):
    suffix = uuid.uuid4().hex[:8]
    email = f"user-{suffix}@example.com"
    username = f"user_{suffix}"[:20]
    name = f"Tester {suffix[:4]}"

    r = client.post("/api/auth/register", json={
        "email": email,
        "password": "secret12",
        "name": name,
        "username": username,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["username"] == username.lower()
    assert data["user"]["name"] == name

    r2 = client.post("/api/auth/login", json={"login": username, "password": "secret12"})
    assert r2.status_code == 200
    assert r2.json()["user"]["email"] == email


def test_login_by_email_still_works(client):
    suffix = uuid.uuid4().hex[:8]
    email = f"mail-{suffix}@example.com"
    client.post("/api/auth/register", json={
        "email": email,
        "password": "secret12",
        "name": f"Mail User {suffix[:4]}",
        "username": f"mail_{suffix}"[:20],
    })
    r = client.post("/api/auth/login", json={"email": email, "password": "secret12"})
    assert r.status_code == 200


def test_duplicate_username_rejected(client):
    suffix = uuid.uuid4().hex[:8]
    username = f"dup_{suffix}"[:16]
    client.post("/api/auth/register", json={
        "email": f"a-{suffix}@example.com",
        "password": "secret12",
        "name": f"Alpha {suffix[:3]}",
        "username": username,
    })
    r = client.post("/api/auth/register", json={
        "email": f"b-{suffix}@example.com",
        "password": "secret12",
        "name": f"Beta {suffix[:3]}",
        "username": username,
    })
    assert r.status_code == 400
    assert "логин" in r.json()["detail"].lower()


def test_duplicate_name_rejected(client):
    suffix = uuid.uuid4().hex[:8]
    shared_name = f"SameName {suffix[:4]}"
    client.post("/api/auth/register", json={
        "email": f"x-{suffix}@example.com",
        "password": "secret12",
        "name": shared_name,
        "username": f"x_{suffix}"[:16],
    })
    r = client.post("/api/auth/register", json={
        "email": f"y-{suffix}@example.com",
        "password": "secret12",
        "name": shared_name,
        "username": f"y_{suffix}"[:16],
    })
    assert r.status_code == 400
    assert "имя" in r.json()["detail"].lower()


def test_check_username_endpoint(client):
    r = client.get("/api/auth/check-username", params={"u": "ab"})
    assert r.status_code == 200
    assert r.json()["available"] is False

    r2 = client.get("/api/auth/check-username", params={"u": f"free_{uuid.uuid4().hex[:10]}"})
    assert r2.status_code == 200
    assert r2.json()["available"] is True
