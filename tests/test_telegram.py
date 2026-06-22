import json

import httpx
import pytest

from app.telegram.notifier import TelegramNotifier


@pytest.mark.asyncio
async def test_notifier_noop_when_disabled():
    n = TelegramNotifier(token="", chat_id="")
    assert n.enabled is False
    ok = await n.send("hi")
    assert ok is False


@pytest.mark.asyncio
async def test_notifier_sends_message_via_httpx(monkeypatch):
    captured: dict = {}

    class _FakeResp:
        status_code = 200
        text = "ok"

        def json(self):
            return {"ok": True}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None):
            captured["url"] = url
            captured["json"] = json
            return _FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    n = TelegramNotifier(token="123:abc", chat_id="42")
    ok = await n.send("<b>hi</b>")
    assert ok is True
    assert captured["url"].endswith("/sendMessage")
    assert captured["json"]["chat_id"] == "42"
    assert "<b>hi</b>" in captured["json"]["text"]


@pytest.mark.asyncio
async def test_notify_order_formats(monkeypatch):
    sent = []

    async def fake_send(text, **kw):
        sent.append(text)
        return True

    n = TelegramNotifier(token="123:abc", chat_id="42")
    monkeypatch.setattr(n, "send", fake_send)
    await n.notify_order(side="buy", symbol="BTC/USDT", quantity=0.05,
                          price=60_000, mode="paper", reason="agent says buy")
    assert sent and "BUY BTC/USDT" in sent[0] and "0.050000" in sent[0]
    assert "agent says buy" in sent[0]
