"""Тесты Сони — Figma, React Preview, offline-паттерны."""

import asyncio
import pytest


@pytest.fixture
def client():
    from app import app
    from starlette.testclient import TestClient
    with TestClient(app, follow_redirects=True) as c:
        yield c


def test_parse_figma_url_site_not_api():
    from integrations.figma_client import parse_figma_url, is_figma_api_url

    url = "https://www.figma.com/site/abc123/My-Site"
    parsed = parse_figma_url(url)
    assert parsed is not None
    assert parsed["file_type"] == "site"
    assert parsed["api_supported"] is False
    assert is_figma_api_url(url) is False


def test_parse_figma_url_design_supported():
    from integrations.figma_client import parse_figma_url, is_figma_api_url, is_valid_file_key

    url = "https://www.figma.com/design/abc123/My-File?node-id=1-2"
    parsed = parse_figma_url(url)
    assert parsed["file_type"] == "design"
    assert parsed["api_supported"] is True
    assert is_figma_api_url(url) is True
    assert is_valid_file_key("abc123") is True
    assert is_valid_file_key("1175755450846438274") is False


def test_community_numeric_id_not_api_url():
    from integrations.figma_client import is_figma_api_url

    url = "https://www.figma.com/community/file/1175755450846438274"
    assert is_figma_api_url(url) is False


def test_rate_limit_cooldown_capped():
    from integrations.figma_rate_limit import reset_cooldown, set_cooldown, cooldown_remaining

    reset_cooldown()
    set_cooldown(999999)
    assert cooldown_remaining() <= 600


def test_sonya_study_and_create_offline():
    from unittest.mock import patch
    from integrations.figma_learning import (
        ensure_seed_patterns,
        run_figma_study_session,
        run_figma_create_session,
        load_portfolio,
    )
    from integrations.figma_rate_limit import reset_cooldown
    from agents.frontend_dev import FrontendDevAgent

    reset_cooldown()
    ensure_seed_patterns()

    class FakeRoom:
        async def broadcast_learning(self, *_a, **_k):
            pass

        async def broadcast_work(self, *_a, **_k):
            pass

        async def send_agents_state(self):
            pass

    async def run():
        async def noop(*_a, **_k):
            pass

        agent = FrontendDevAgent(FakeRoom())
        agent._persist_knowledge = lambda: None
        agent._broadcast = noop

        with patch("integrations.figma_learning.random.random", return_value=0.0):
            ok_study = await run_figma_study_session(agent)
        assert ok_study is True

        ok_create = await run_figma_create_session(agent)
        assert ok_create is True
        assert len(load_portfolio()) >= 1

    asyncio.run(run())


def test_figma_studio_trigger(client):
    from integrations.figma_rate_limit import reset_cooldown

    reset_cooldown()
    r = client.post("/api/figma/studio/trigger?action=study")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r2 = client.post("/api/figma/studio/trigger?action=create")
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_react_preview_for_sonya_tasks():
    from agents.react_preview import generate_react_preview

    tasks = [
        "Создай форму регистрации в React",
        "Сделай landing page для стартапа",
        "Dashboard с KPI карточками",
    ]
    for t in tasks:
        preview = generate_react_preview(t)
        assert preview.get("code")
        assert "function App" in preview["code"] or "App()" in preview["code"]


def test_figma_discovery_extract_urls():
    from integrations.figma_discovery import extract_figma_urls, file_key_to_url

    text = "See https://www.figma.com/design/abc123XYZ/My-Landing?node-id=1-2 and more"
    urls = extract_figma_urls(text)
    assert len(urls) == 1
    assert "abc123XYZ" in urls[0]
    assert file_key_to_url("abc123XYZ", "Test") == "https://www.figma.com/design/abc123XYZ/test"


def test_figma_discovery_web_cache_enqueue(tmp_path, monkeypatch):
    from integrations import figma_discovery as fd

    disc_file = tmp_path / "sonya_figma_discovery.json"
    monkeypatch.setattr(fd, "DISCOVERY_FILE", str(disc_file))

    url = "https://www.figma.com/design/fk1qJWkEEIOPSIlMa5Q1OS/eCommerce-Landing"
    state = fd.load_discovery()
    state["web_cache"] = [url]
    fd.save_discovery(state)

    added = fd._enqueue_cached_web_urls(state)
    assert added == 1
    assert state["queue"][0]["file_key"] == "fk1qJWkEEIOPSIlMa5Q1OS"


def test_figma_discovery_catalog_not_empty():
    from integrations.figma_discovery import get_catalog

    catalog = get_catalog()
    assert len(catalog) >= 1
    assert catalog[0].get("file_key")


def test_figma_discovery_queue_and_status(tmp_path, monkeypatch):
    from integrations import figma_discovery as fd

    disc_file = tmp_path / "sonya_figma_discovery.json"
    monkeypatch.setattr(fd, "DISCOVERY_FILE", str(disc_file))

    state = fd.load_discovery()
    assert state["queue"] == []

    fd.mark_studied("key1", name="File One", url="https://www.figma.com/design/key1/x", source="team")
    status = fd.get_discovery_status()
    assert status["studied_keys_count"] == 1
    assert status["auto_discover_enabled"] is True

    fd.mark_failed("key2", "403", url="https://www.figma.com/design/key2/x", source="catalog")
    status2 = fd.get_discovery_status()
    assert status2["failed_keys_count"] == 1


def test_figma_discover_endpoint(client):
    from integrations.figma_rate_limit import reset_cooldown

    reset_cooldown()
    r = client.post("/api/figma/studio/discover?scan_only=true")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "discovery" in data
    assert "scan" in data
