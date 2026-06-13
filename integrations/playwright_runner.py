"""Playwright browser automation for QA (Фаза B/C)."""

from __future__ import annotations

import asyncio
from typing import Optional


def playwright_installed() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


async def browser_snapshot(url: str, timeout_ms: int = 15000) -> dict:
    """Открыть URL и вернуть title + текст страницы."""
    url = (url or "").strip()
    if not url:
        return {"ok": False, "error": "url required"}
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"

    if playwright_installed():
        return await _playwright_snapshot(url, timeout_ms)
    return await _httpx_fallback(url)


async def _playwright_snapshot(url: str, timeout_ms: int) -> dict:
    def _run() -> dict:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                title = page.title()
                text = page.inner_text("body")[:6000]
                return {
                    "ok": True,
                    "engine": "playwright",
                    "url": url,
                    "title": title,
                    "text": text,
                }
            finally:
                browser.close()

    try:
        return await asyncio.to_thread(_run)
    except Exception as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "browser" in msg.lower():
            return {
                "ok": False,
                "error": "Playwright browsers not installed. Run: playwright install chromium",
                "hint": "playwright install chromium",
            }
        return {"ok": False, "error": msg, "engine": "playwright"}


async def _httpx_fallback(url: str) -> dict:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "TakuraQA/1.0"})
        from html import unescape
        import re
        text = re.sub(r"<[^>]+>", " ", r.text)
        text = unescape(re.sub(r"\s+", " ", text)).strip()[:6000]
        return {
            "ok": r.status_code < 400,
            "engine": "httpx",
            "url": url,
            "status": r.status_code,
            "text": text,
            "warning": "Playwright not installed — basic HTTP fetch only",
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "engine": "httpx"}


async def run_smoke_test(url: str, checks: Optional[list] = None) -> dict:
    """Простой smoke: страница открывается, нет явных ошибок в title/body."""
    snap = await browser_snapshot(url)
    if not snap.get("ok") and snap.get("engine") == "httpx" and snap.get("status"):
        snap["ok"] = snap["status"] < 400
    if not snap.get("ok"):
        return {**snap, "passed": False}

    body = (snap.get("text") or "").lower()
    title = (snap.get("title") or "").lower()
    bad = ["error 404", "internal server error", "exception", "stack trace"]
    failed = [b for b in bad if b in body or b in title]
    custom = checks or []
    missing = [c for c in custom if c.lower() not in body]

    passed = not failed and not missing
    return {
        **snap,
        "passed": passed,
        "failed_patterns": failed,
        "missing_checks": missing,
    }
