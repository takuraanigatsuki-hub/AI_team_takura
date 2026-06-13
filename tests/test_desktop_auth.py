"""Desktop auth — device flow and handoff."""

import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient
    with TestClient(app, follow_redirects=False) as c:
        yield c


def test_desktop_shell(client):
    headers = {"User-Agent": "AITeamRoomDesktop/1.1 (Windows; Native)"}
    r = client.get("/client", headers=headers)
    assert r.status_code == 200
    assert "ds-splash" in r.text
    assert "desktop-app.js" in r.text


def test_download_page(client):
    r = client.get("/download")
    assert r.status_code == 200
    assert "download-page.js" in r.text


def test_device_flow(client):
    r = client.post("/api/auth/device/start")
    assert r.status_code == 200
    data = r.json()
    assert "device_id" in data
    assert "user_code" in data
    assert "poll_secret" in data
    assert len(data["user_code"]) == 6

    r2 = client.get(f"/api/auth/device/poll/{data['device_id']}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "expired"

    r3 = client.get(
        f"/api/auth/device/poll/{data['device_id']}",
        params={"secret": data["poll_secret"]},
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "pending"


def test_device_start_no_auth_required(client):
    """device/start must work without session (desktop initiates flow)."""
    r = client.post("/api/auth/device/start")
    assert r.status_code == 200
    assert r.json().get("device_id")


def test_device_approve_requires_auth(client):
    r = client.post("/api/auth/device/start")
    device_id = r.json()["device_id"]
    r2 = client.post("/api/auth/device/approve", json={"device_id": device_id})
    assert r2.status_code == 401
