"""Sonya Studio diff, handoff export, notify."""

import io
import zipfile

import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient
    with TestClient(app, follow_redirects=True) as c:
        yield c


def _make_two_version_project(client):
    r = client.post("/api/sonya/projects", json={
        "title": "Diff Test",
        "task": "Landing с hero блоком",
    })
    pid = r.json()["project"]["id"]
    client.post(f"/api/sonya/projects/{pid}/comments", json={
        "text": "Сделай кнопку синей",
        "x": 0.5,
        "y": 0.5,
    })
    client.post(f"/api/sonya/projects/{pid}/apply-comments")
    return pid


def test_compare_versions(client):
    pid = _make_two_version_project(client)
    r = client.get(f"/api/sonya/projects/{pid}/diff?from_ref=1&to_ref=2")
    assert r.status_code == 200
    data = r.json()
    assert data["from"]["version_num"] == 1
    assert data["to"]["version_num"] == 2
    assert "summary" in data
    assert "diff" in data


def test_handoff_package(client):
    pid = _make_two_version_project(client)
    client.post(f"/api/sonya/projects/{pid}/publish", json={"figma_url": ""})

    r = client.get(f"/api/sonya/projects/{pid}/handoff")
    assert r.status_code == 200
    pkg = r.json()
    assert pkg["schema"] == "sonya-studio-handoff/v1"
    assert pkg["react_code"]
    assert pkg["css_tokens"]
    assert "tokens.css" not in pkg["react_code"]


def test_handoff_zip_download(client):
    pid = _make_two_version_project(client)
    client.post(f"/api/sonya/projects/{pid}/publish", json={"figma_url": ""})

    r = client.get(f"/api/sonya/projects/{pid}/handoff/download")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/zip")
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(zf.namelist())
    assert {"handoff.json", "tokens.css", "App.jsx", "README.txt"}.issubset(names)


def test_notify_studio_respects_config(monkeypatch):
    import asyncio
    import config as cfg
    from integrations.sonya_studio_notify import notify_studio

    monkeypatch.setitem(cfg.config, "telegram_notify_studio", False)
    called = []

    async def fake_notify(text, chat_id=None):
        called.append(text)

    monkeypatch.setattr("integrations.telegram_bot.notify_task", fake_notify)
    asyncio.run(notify_studio("comment", project_title="T", project_id="proj-1", author="A", text="Hi"))
    assert called == []

    monkeypatch.setitem(cfg.config, "telegram_notify_studio", True)
    monkeypatch.setitem(cfg.config, "telegram_notify_tasks", True)
    asyncio.run(notify_studio("project", project_title="New", project_id="proj-2"))
    assert len(called) == 1
    assert "Studio" in called[0]
