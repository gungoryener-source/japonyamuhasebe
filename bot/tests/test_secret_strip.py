"""Panele yapıştırılan LINE anahtarlarının sonundaki boşluk/satır sonu imzayı bozmamalı."""
import base64
import hashlib
import hmac
import importlib


def test_secret_with_trailing_whitespace_still_verifies(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "  abc123secret \n")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok \n")
    import app
    app = importlib.reload(app)
    body = b'{"events":[]}'
    sig = base64.b64encode(hmac.new(b"abc123secret", body, hashlib.sha256).digest()).decode()
    assert app.verify_signature(body, sig)
    assert app.CHANNEL_TOKEN == "tok"
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test-secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
    importlib.reload(app)


def test_health_reports_secret_format_only(bot):
    from fastapi.testclient import TestClient
    r = TestClient(bot.app).get("/").json()
    assert r["line_secret_len"] == len("test-secret") and r["line_secret_format_ok"] is False
    assert "test-secret" not in str(r)
