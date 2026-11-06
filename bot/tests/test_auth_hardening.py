"""Kimlik karşılaştırmaları ASCII olmayan girdide 500 değil 401/403 dönmeli (hmac.compare_digest str + non-ASCII → TypeError)."""
import json

from fastapi.testclient import TestClient

NON_ASCII = "été".encode("utf-8")  # sunucuda latin-1 ile çözülür → ASCII olmayan str


def test_line_signature_non_ascii_rejected(bot):
    body = json.dumps({"events": []}).encode()
    r = TestClient(bot.app).post("/callback", content=body, headers={"X-Line-Signature": NON_ASCII})
    assert r.status_code == 400


def test_admin_endpoints_non_ascii_key(bot):
    c = TestClient(bot.app)
    assert c.get("/entries/U1", headers={"X-Admin-Key": NON_ASCII}).status_code == 401
    assert c.post("/admin/richmenu", params={"key": "ключ"}).status_code == 403
    assert c.post("/api/v1/admin/tokens", json={"user_id": "U1"}, headers={"X-Admin-Key": NON_ASCII}).status_code == 401
    assert c.post("/api/v1/admin/demo-seed", headers={"X-Admin-Key": NON_ASCII}).status_code == 401


def test_whatsapp_non_ascii_verify_and_signature(bot, monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "app-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    c = TestClient(bot.app)
    r = c.get("/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "トークン", "hub.challenge": "1"})
    assert r.status_code == 403
    r = c.post("/whatsapp", content=b"{}", headers={"X-Hub-Signature-256": b"sha256=" + NON_ASCII})
    assert r.status_code == 401
