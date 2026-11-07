"""Reviewer 2026-11-08: T-065/T-065b (audit_log) ve T-050 (2割/3割要件・経過措置上限) için eksik sınır testleri."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tax.consumption import Purchase, transitional_cap_warnings

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


# ---------------------------------------------------------------- audit_log
def test_noop_patch_writes_no_audit_and_changed_lists_only_diff(client):
    h = H(signup(client, "noop@example.jp")["token"])
    eid = client.post("/api/v1/entries", headers=h, json=ENTRY).json()["id"]
    # Aynı değerle düzeltme → 履歴 satırı eklenmez
    assert client.patch(f"/api/v1/entries/{eid}", headers=h, json={"amount": 1100, "rate": 10}).status_code == 200
    hist = client.get(f"/api/v1/entries/{eid}/history", headers=h).json()
    assert [x["action"] for x in hist] == ["create"]
    assert hist[0]["before"] is None and hist[0]["changed"] == []
    # Tek alan değişince changed yalnızca o alan
    assert client.patch(f"/api/v1/entries/{eid}", headers=h, json={"amount": 1200, "rate": 10}).status_code == 200
    hist = client.get(f"/api/v1/entries/{eid}/history", headers=h).json()
    assert [x["action"] for x in hist] == ["create", "update"]
    assert hist[1]["changed"] == ["amount"] and hist[1]["before"]["amount"] == 1100


def test_audit_limit_bounds_and_order(client):
    h = H(signup(client, "lim@example.jp")["token"])
    ids = [client.post("/api/v1/entries", headers=h, json={**ENTRY, "amount": 100 + i}).json()["id"] for i in range(3)]
    assert [x["entity_id"] for x in client.get("/api/v1/audit", headers=h).json()] == [str(i) for i in reversed(ids)]
    assert [x["entity_id"] for x in client.get("/api/v1/audit?limit=1", headers=h).json()] == [str(ids[-1])]
    assert client.get("/api/v1/audit?limit=0", headers=h).status_code == 422
    assert client.get("/api/v1/audit?limit=1001", headers=h).status_code == 422


def test_invoice_paid_twice_logs_once(client):
    h = H(signup(client, "twice@example.jp")["token"])
    no = client.post("/api/v1/invoices", headers=h, json=INVOICE).json()["no"]
    for _ in range(2):
        assert client.post(f"/api/v1/invoices/{no}/paid?paid_on=2026-10-20", headers=h).status_code == 200
    rows = client.get("/api/v1/audit?entity=invoice&action=update", headers=h).json()
    assert len(rows) == 1
    assert len(client.get("/api/v1/audit?entity=entry&action=create", headers=h).json()) == 1  # 売上 iki kez yazılmaz


def test_bank_match_audits_invoice_bank_and_entry(client, bot):
    import store
    s = signup(client, "match@example.jp")
    h, uid = H(s["token"]), s["user_id"]
    inv = client.post("/api/v1/invoices", headers=h, json=INVOICE).json()
    store.insert_bank_rows(uid, [{"d": "2026-10-25", "description": "ﾌﾘｺﾐ ﾃｽﾄ", "amount": inv["total"], "balance": 111000}])
    tid = store.list_bank_tx(uid)[0]["id"]
    r = client.post("/api/v1/bank/match", headers=h, json={"tx_id": tid, "invoice_no": inv["no"]})
    assert r.status_code == 200, r.text
    bank = client.get(f"/api/v1/bank/{tid}/history", headers=h).json()
    assert len(bank) == 1 and bank[0]["changed"] == ["invoice_no"] and bank[0]["actor_role"] == "owner"
    inv_rows = client.get("/api/v1/audit?entity=invoice&action=update", headers=h).json()
    assert inv_rows[0]["after"]["status"] == "paid" and inv_rows[0]["actor_kind"] == "web"
    inc = client.get("/api/v1/audit?entity=entry&action=create", headers=h).json()
    assert len(inc) == 1 and inc[0]["actor_role"] == "owner" and inc[0]["after"]["source"] == "INVOICE"
    # İkinci eşleştirme 409 ve yeni audit satırı yok
    assert client.post("/api/v1/bank/match", headers=h, json={"tx_id": tid, "invoice_no": inv["no"]}).status_code == 409
    assert len(client.get(f"/api/v1/bank/{tid}/history", headers=h).json()) == 1


def test_store_update_other_users_entry_is_not_audited(bot):
    import store
    eid = store.add_entry("UA", dict(ENTRY), source="WEB")
    assert store.update_entry("UB", eid, actor="x", amount=1) is None
    assert store.delete_entry("UB", eid, actor="x") is False
    assert store.audit_recent("UB") == []
    assert [r["action"] for r in store.audit_history("UA", "entry", eid)] == ["create"]
    assert store.get_entry("UA", eid)["amount"] == 1100


# ---------------------------------------------------------------- T-050 経過措置上限
def test_cap_ignores_purchases_before_invoice_system():
    """2023-10-01 前の仕入れ（区分記載請求書・100%）は経過措置の上限計算に入らない。"""
    ps = [Purchase(100_000_000, 10, date(2023, 9, 30), False, "X"),
          Purchase(1, 10, date(2023, 10, 1), False, "X")]
    assert transitional_cap_warnings(ps, date(2026, 10, 1)) == []
    ps.append(Purchase(100_000_000, 10, date(2026, 10, 1), False, "X"))
    assert transitional_cap_warnings(ps, date(2026, 10, 1))[0]["excess"] == 1


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "UREV"}, headers={"X-Admin-Key": "test-admin"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.mark.parametrize("q,status", [
    ("", 200),
    ("&specific_period_sales=10000000", 200),
    ("&specific_period_sales=10000001", 400),
    ("&specific_period_sales=10000001&specific_period_salaries=10000000", 200),
    ("&specific_period_sales=10000001&specific_period_salaries=10000001", 400),
    ("&base_period_sales=10000001&specific_period_salaries=0", 400),
    ("&specific_period_salaries=-1", 422),
])
def test_api_sanwari_specific_period(client, auth, q, status):
    r = client.get("/api/v1/tax/consumption?year=2027&method=sanwari" + q, headers=auth)
    assert r.status_code == status, r.text
    if status == 400:
        assert "期間" in r.json()["detail"]
