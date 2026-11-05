import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def wa(bot, monkeypatch):
    import whatsapp
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "app-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    sent = []

    async def fake_send(payload):
        sent.append(payload)

    monkeypatch.setattr(whatsapp, "send", fake_send)
    whatsapp.sent = sent
    return whatsapp


def _post(client, msg, secret="app-secret"):
    body = json.dumps({"entry": [{"changes": [{"value": {"messages": [msg]}}]}]}).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/whatsapp", content=body, headers={"X-Hub-Signature-256": sig})


def test_verify(bot, wa):
    c = TestClient(bot.app)
    ok = c.get("/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42"})
    assert ok.status_code == 200 and ok.text == "42"
    assert c.get("/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "1"}).status_code == 403


def test_signature_required(bot, wa):
    c = TestClient(bot.app)
    assert _post(c, {"from": "8190", "type": "text", "text": {"body": "x 1"}}, secret="bad").status_code == 401


def test_text_entry_uses_list_message(bot, wa):
    import store
    c = TestClient(bot.app)
    assert _post(c, {"from": "819012345678", "type": "text", "text": {"body": "タクシー 2300"}}).status_code == 200
    p = wa.sent[-1]
    assert p["to"] == "819012345678" and p["interactive"]["type"] == "list"
    rows = p["interactive"]["action"]["sections"][0]["rows"]
    assert {"id": "取消", "title": "取消"} in rows and all(len(r["title"]) <= 24 for r in rows)
    e = store.last_entry("wa:819012345678")
    assert e["amount"] == 2300 and e["source"] == "WhatsApp"


def test_button_reply_routes_to_core(bot, wa):
    c = TestClient(bot.app)
    _post(c, {"from": "8190", "type": "text", "text": {"body": "ローソン 540 軽減"}})
    _post(c, {"from": "8190", "type": "interactive", "interactive": {"type": "list_reply", "list_reply": {"id": "取消", "title": "取消"}}})
    p = wa.sent[-1]
    assert "取り消しました" in p["interactive"]["body"]["text"]
    assert p["interactive"]["type"] == "button"   # 「合計」 only (camera removed)


def test_unsupported_type(bot, wa):
    c = TestClient(bot.app)
    _post(c, {"from": "8190", "type": "sticker", "sticker": {}})
    assert wa.sent[-1]["type"] == "text"


def test_whatsapp_and_line_ledgers_are_separate(bot, wa):
    import store
    c = TestClient(bot.app)
    _post(c, {"from": "U1", "type": "text", "text": {"body": "本 1000"}})
    assert store.last_entry("U1") is None
