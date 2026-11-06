"""T-042b: LINE / WhatsApp kayıt yolunda ücretsiz plan sınırı (経費 30件/月)."""
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

import store


@pytest.fixture()
def stripe_on(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("PANEL_URL", "https://panel.example")
    monkeypatch.delenv("BILLING_ENFORCE_LIMITS", raising=False)


def _count(uid):
    with store.tx() as con:
        return int(con.execute("SELECT COUNT(*) n FROM entries WHERE user_id=?", (uid,)).fetchone()["n"])


def _fill(bot, uid, n, source="LINE"):
    for i in range(n):
        msg, _ = bot.respond(uid, f"コンビニ {100 + i}", source)
        assert msg.startswith("登録しました")


def test_line_text_limit_boundary(bot, stripe_on):
    _fill(bot, "LL1", 29)
    msg, _ = bot.respond("LL1", "タクシー 2300")          # 30件目: まだ可
    assert msg.startswith("登録しました") and _count("LL1") == 30
    msg, options = bot.respond("LL1", "タクシー 2400")    # 31件目: 拒否
    assert "上限（経費30件）" in msg and "記録されていません" in msg
    assert "https://panel.example/billing/" in msg
    assert _count("LL1") == 30 and options == [("合計", "合計")]


def test_income_and_commands_not_blocked(bot, stripe_on):
    _fill(bot, "LL2", 30)
    msg, _ = bot.respond("LL2", "入金 330000 合同会社ミナト")   # 売上は経費の上限対象外
    assert msg.startswith("登録しました")
    assert bot.respond("LL2", "合計")[0].startswith("今月の集計")
    assert "取り消しました" in bot.respond("LL2", "取消")[0]


def test_no_limit_without_stripe(bot, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    _fill(bot, "LL3", 31)
    assert _count("LL3") == 31


def test_enforce_off_switch(bot, stripe_on, monkeypatch):
    monkeypatch.setenv("BILLING_ENFORCE_LIMITS", "0")
    _fill(bot, "LL4", 31)


def test_paid_plan_not_limited(bot, stripe_on, monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_PERSONAL", "price_personal")
    import billing
    billing._upsert("LL5", plan="personal", status="active", stripe_subscription="sub_1")
    _fill(bot, "LL5", 31)


def test_limit_message_without_panel_url(bot, stripe_on, monkeypatch):
    monkeypatch.delenv("PANEL_URL")
    _fill(bot, "LL6", 30)
    msg, _ = bot.respond("LL6", "タクシー 2400")
    assert "上限" in msg and "「パネル」" in msg and "http" not in msg


async def test_line_image_blocked_before_ocr(bot, stripe_on, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _fill(bot, "LL7", 30)
    called = []

    async def fake_ocr(img):
        called.append(1)
        return [{"date": "2026-11-01", "kind": "exp", "store": "A", "amount": 500, "rate": 10,
                 "category": "雑費", "invoice_no": ""}]

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)
    msg, _ = await bot.process_image("LL7", b"jpg", "m1", "LINE")
    assert "上限" in msg and not called and _count("LL7") == 30
    assert not (tmp_path / "receipts").exists()


async def test_line_image_ok_under_limit(bot, stripe_on, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _fill(bot, "LL8", 29)

    async def fake_ocr(img):
        return [{"date": "2026-11-01", "kind": "exp", "store": "A", "amount": 500, "rate": 10,
                 "category": "雑費", "invoice_no": ""}]

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)
    msg, _ = await bot.process_image("LL8", b"jpg", "m1", "LINE")
    assert msg.startswith("登録しました") and _count("LL8") == 30


def test_whatsapp_limit(bot, stripe_on, monkeypatch):
    import whatsapp
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "app-secret")
    sent = []

    async def fake_send(payload):
        sent.append(payload)

    monkeypatch.setattr(whatsapp, "send", fake_send)
    _fill(bot, "wa:8190", 30, "WhatsApp")
    body = json.dumps({"entry": [{"changes": [{"value": {"messages": [
        {"from": "8190", "type": "text", "text": {"body": "タクシー 2300"}}]}}]}]}).encode()
    sig = "sha256=" + hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()
    assert TestClient(bot.app).post("/whatsapp", content=body, headers={"X-Hub-Signature-256": sig}).status_code == 200
    p = sent[-1]
    assert "上限（経費30件）" in p["interactive"]["body"]["text"]
    assert _count("wa:8190") == 30
