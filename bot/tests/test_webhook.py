import base64
import hashlib
import hmac
import json

from fastapi.testclient import TestClient


def _post(client, text, secret="test-secret", user="U1"):
    body = json.dumps({"events": [{
        "type": "message", "replyToken": "r", "source": {"userId": user},
        "message": {"type": "text", "id": "1", "text": text}}]}).encode()
    sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    return client.post("/callback", content=body, headers={"X-Line-Signature": sig})


def test_bad_signature_rejected(bot):
    c = TestClient(bot.app)
    assert _post(c, "x 100", secret="wrong").status_code == 400


def test_save_summary_undo(bot):
    c = TestClient(bot.app)
    assert _post(c, "ローソン 540円 軽減").status_code == 200
    assert "ローソン" in bot.sent[-1][0]["text"]
    assert bot.month_summary("U1") == (0, 540)
    assert _post(c, "取消").status_code == 200
    assert "取り消しました" in bot.sent[-1][0]["text"]
    assert _post(c, "取消").status_code == 200
    assert "ありません" in bot.sent[-1][0]["text"]


def test_users_are_isolated(bot):
    c = TestClient(bot.app)
    _post(c, "タクシー 2300", user="A")
    _post(c, "取消", user="B")
    assert "ありません" in bot.sent[-1][0]["text"]


def test_health(bot):
    r = TestClient(bot.app).get("/")
    assert r.status_code == 200 and r.json()["ok"]


def test_admin_requires_key(bot):
    assert TestClient(bot.app).post("/admin/richmenu?key=nope").status_code == 403


def test_entries_requires_admin_key(bot):
    c = TestClient(bot.app)
    assert c.get("/entries/U1").status_code == 401
    assert c.get("/entries/U1", headers={"X-Admin-Key": "wrong"}).status_code == 401
    _post(c, "タクシー 2300", user="U1")
    r = c.get("/entries/U1", headers={"X-Admin-Key": "test-admin"})
    assert r.status_code == 200 and r.json()[0]["amount"] == 2300
    assert c.get("/entries/U1?year=20%25", headers={"X-Admin-Key": "test-admin"}).status_code == 400


def test_saved_text_transitional_ratio(bot):
    base = {"store": "店", "amount": 1100, "category": "雑費", "rate": 10, "kind": "exp", "invoice_no": ""}
    assert "控除80%" in bot.saved_text({**base, "date": "2026-09-30"})
    assert "控除70%" in bot.saved_text({**base, "date": "2026-10-01"})
    assert "登録番号" not in bot.saved_text({**base, "kind": "inc", "date": "2026-10-01"})
    assert "T1234567890123" in bot.saved_text({**base, "invoice_no": "T1234567890123", "date": "2026-10-01"})


def test_panel_command_issues_token(bot):
    import store
    c = TestClient(bot.app)
    _post(c, "パネル", user="U9")
    text = bot.sent[-1][0]["text"]
    tok = [w for w in text.split() if w.startswith("tk_")][0]
    assert store.user_for_token(tok) == "U9"


def test_edit_last_entry_category_and_rate(bot):
    import store
    c = TestClient(bot.app)
    _post(c, "ヨドバシ 3300", user="E1")
    _post(c, "科目変更", user="E1")
    labels = [i["action"]["text"] for i in bot.sent[-1][0]["quickReply"]["items"]]
    assert "科目:通信費" in labels and len(labels) <= 13
    _post(c, "科目:通信費", user="E1")
    assert "変更しました" in bot.sent[-1][0]["text"]
    _post(c, "税率8%", user="E1")
    e = store.last_entry("E1")
    assert (e["category"], e["rate"]) == ("通信費", 8)
    _post(c, "科目:存在しない", user="E1")
    assert "変更できませんでした" in bot.sent[-1][0]["text"]


def test_edit_without_entries(bot):
    c = TestClient(bot.app)
    _post(c, "税率10%", user="EMPTY")
    assert "ありません" in bot.sent[-1][0]["text"]
