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
