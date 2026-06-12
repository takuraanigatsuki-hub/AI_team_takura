"""E2E smoke — Playwright (optional, skip if not installed)."""

import pytest

playwright = pytest.importorskip("playwright", reason="playwright not installed")


@pytest.mark.e2e
def test_preview_page_loads():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded", timeout=15000)
        assert "AI Team Room" in page.title()
        browser.close()
