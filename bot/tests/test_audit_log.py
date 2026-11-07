"""T-065 訂正・削除の履歴: kayıt/fatura oluşturma, düzeltme, silme audit_log'a önce/sonra görüntüsüyle yazılır."""
import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

PW = "correct-horse-1"
ENTRY = {"date": "2026-10-05", "kind": "exp", "store": "コンビニ", "amount": 1100, "category": "消耗品費", "rate": 10}
INVOICE = {"client": "株式会社テスト", "issued": "2026-10-01", "due": "2026-10-31",
           "items": [{"name": "制作費", "qty": 1, "unit_price": 10000, "rate": 10}]}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def signup(client, email):
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": PW})
    assert r.status_code == 201, r.text
    return r.json()


def _line(client, text, user="U1"):
    body = json.dumps({"events": [{
        "type": "message", "replyToken": "r", "source": {"userId": user},
        "message": {"type": "text", "id": "1", "text": text}}]}).encode()
    sig = base64.b64encode(hmac.new(b"test-secret", body, hashlib.sha256).digest()).decode()
    assert client.post("/callback", content=body, headers={"X-Line-Signature": sig}).status_code == 200


def test_entry_create_update_delete_history(client):
    owner = signup(client, "owner@example.jp")
    h = H(owner["token"])
    eid = client.post("/api/v1/entries", headers=h, json=ENTRY).json()["id"]
    r = client.patch(f"/api/v1/entries/{eid}", headers=h, json={"amount": 1210, "category": "雑費"})
    assert r.status_code == 200
    # Değişmeyen düzeltme geçmişe yazılmaz
    assert client.patch(f"/api/v1/entries/{eid}", headers=h, json={"amount": 1210}).status_code == 200
    assert client.delete(f"/api/v1/entries/{eid}", headers=h).status_code == 204

    hist = client.get(f"/api/v1/entries/{eid}/history", headers=h)
    assert hist.status_code == 200      # silinmiş kaydın geçmişi de okunur
    rows = hist.json()
    assert [x["action"] for x in rows] == ["create", "update", "delete"]
    create, update, delete = rows
    assert create["before"] is None and create["after"]["amount"] == 1100
    assert update["before"]["amount"] == 1100 and update["after"]["amount"] == 1210
    assert update["changed"] == ["amount", "category"]
    assert delete["before"]["amount"] == 1210 and delete["after"] is None
    assert all(x["actor"].startswith("WEB:owner:") and x["actor"] != "WEB:owner:0" for x in rows)

    recent = client.get("/api/v1/audit?entity=entry&action=delete", headers=h).json()
    assert [x["entity_id"] for x in recent] == [str(eid)]


def test_history_404_and_isolation(client):
    a = H(signup(client, "a@example.jp")["token"])
    b = H(signup(client, "b@example.jp")["token"])
    eid = client.post("/api/v1/entries", headers=a, json=ENTRY).json()["id"]
    assert client.get(f"/api/v1/entries/{eid}/history", headers=b).status_code == 404
    assert client.get("/api/v1/audit", headers=b).json() == []
    assert client.get("/api/v1/entries/999999/history", headers=a).status_code == 404
    assert client.get("/api/v1/audit?entity=bogus", headers=a).status_code == 400
    assert client.get("/api/v1/audit?action=bogus", headers=a).status_code == 400
    assert client.get("/api/v1/entries/1/history").status_code == 401


def test_invoice_create_and_paid_logged(client):
    h = H(signup(client, "inv@example.jp")["token"])
    inv = client.post("/api/v1/invoices", headers=h, json=INVOICE).json()
    assert client.post(f"/api/v1/invoices/{inv['no']}/paid?paid_on=2026-10-20", headers=h).status_code == 200
    rows = client.get("/api/v1/audit?entity=invoice", headers=h).json()
    assert [x["action"] for x in rows] == ["update", "create"]           # yeniden eskiye
    assert rows[0]["before"]["status"] == "unpaid" and rows[0]["after"]["status"] == "paid"
    assert set(rows[0]["changed"]) == {"status", "paid_on"}
    # 消込 ile oluşan 売上 kaydı da geçmişte (create)
    entries = client.get("/api/v1/audit?entity=entry&action=create", headers=h).json()
    assert len(entries) == 1 and entries[0]["after"]["source"] == "INVOICE"


def test_line_fix_and_undo_logged(bot, client):
    import store
    _line(client, "ローソン 540円 軽減")
    _line(client, "取消")
    rows = store.audit_recent("U1", entity="entry")
    assert [x["action"] for x in rows] == ["delete", "create"]
    assert rows[0]["actor"] == "LINE" and rows[0]["before"]["amount"] == 540


def test_line_category_fix_logged(bot):
    import store
    store.init_db()
    eid = store.add_entry("U2", {"date": "2026-10-05", "kind": "exp", "store": "店", "amount": 500,
                                 "category": "雑費", "rate": 10})
    store.update_entry("U2", eid, actor="LINE", category="消耗品費")
    h = store.audit_history("U2", "entry", eid)
    assert [x["action"] for x in h] == ["create", "update"]
    assert h[1]["changed"] == ["category"] and h[1]["actor"] == "LINE"
    # Olmayan kaydı düzeltmek geçmiş yazmaz
    assert store.update_entry("U2", 424242, category="雑費") is None
    assert store.audit_history("U2", "entry", 424242) == []


def test_viewer_can_read_history_but_not_edit(client):
    owner = signup(client, "o@example.jp")
    view = signup(client, "v@example.jp")
    code = client.post("/api/v1/team/invites", headers=H(owner["token"]), json={"role": "viewer"}).json()["code"]
    vt = client.post("/api/v1/team/join", headers=H(view["token"]), json={"code": code}).json()["token"]
    eid = client.post("/api/v1/entries", headers=H(owner["token"]), json=ENTRY).json()["id"]
    assert client.delete(f"/api/v1/entries/{eid}", headers=H(vt)).status_code == 403
    assert [x["action"] for x in client.get(f"/api/v1/entries/{eid}/history", headers=H(vt)).json()] == ["create"]
