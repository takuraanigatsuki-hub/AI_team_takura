"""HTTP client proxy/VPN settings."""

from integrations.http_client import client_kwargs, describe_outbound, explicit_proxy, proxy_mode


def test_auto_direct_without_proxy(monkeypatch):
    monkeypatch.delenv("OUTBOUND_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.setenv("OUTBOUND_PROXY_MODE", "auto")
    kw = client_kwargs(30)
    assert kw["trust_env"] is False
    assert "proxy" not in kw


def test_auto_uses_explicit_proxy(monkeypatch):
    monkeypatch.setenv("OUTBOUND_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setenv("OUTBOUND_PROXY_MODE", "auto")
    kw = client_kwargs(30)
    assert kw.get("proxy") == "http://127.0.0.1:7890"
    assert "proxy (http://127.0.0.1:7890)" in describe_outbound()


def test_system_mode(monkeypatch):
    monkeypatch.setenv("OUTBOUND_PROXY_MODE", "system")
    kw = client_kwargs(30)
    assert kw["trust_env"] is True


def test_explicit_proxy_helper(monkeypatch):
    monkeypatch.setenv("OUTBOUND_PROXY", "http://127.0.0.1:1080")
    assert explicit_proxy() == "http://127.0.0.1:1080"
    assert proxy_mode() in ("auto", "direct", "system", "proxy", "")
