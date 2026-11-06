"""Reviewer (2026-11-07): bank_csv sınır durumları, 消込 önerisi kuralları, kayıt silme ↔ banka bağı."""
import pytest
from fastapi.testclient import TestClient

import bank_csv

ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    tok = client.post("/api/v1/admin/tokens", json={"user_id": "RV1"}, headers=ADMIN).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


# ---------------------------------------------------------------- bank_csv (birim)
@pytest.mark.parametrize("s,exp", [
    ("2026/11/05", "2026-11-05"), ("2026-1-5", "2026-01-05"), ("20261105", "2026-11-05"),
    ("2026年11月5日", "2026-11-05"), ("R8.11.5", "2026-11-05"), ("令和8年1月31日", "2026-01-31"),
    ("2026/02/30", None), ("", None), ("合計", None),
])
def test_date_formats(s, exp):
    assert bank_csv._date(s) == exp


@pytest.mark.parametrize("s,exp", [
    ("1,234", 1234), ("¥1,234", 1234), ("1,234円", 1234), ("△500", -500), ("▲500", -500),
    ("-66000", -66000), ("", None), ("-", None), ("abc", None),
])
def test_num_formats(s, exp):
    assert bank_csv._num(s) == exp


def test_parse_skips_footer_zero_and_blank_rows():
    raw = ("日付,摘要,出金,入金,残高\n"
           "2026/11/01,振込,,1000,1000\n"
           "\n"
           "2026/11/02,ゼロ,0,0,1000\n"          # 0 円 → atlanır
           "合計,,0,1000,\n").encode("cp932")    # tarih değil → atlanır
    rows = bank_csv.parse(raw)
    assert rows == [{"d": "2026-11-01", "description": "振込", "amount": 1000, "balance": 1000}]


def test_parse_header_must_be_in_first_15_rows():
    pre = "口座情報,x\n" * 15
    with pytest.raises(ValueError):
        bank_csv.parse((pre + "日付,摘要,金額\n2026/11/01,a,100\n").encode())
    ok = bank_csv.parse(("口座情報,x\n" * 14 + "日付,摘要,金額\n2026/11/01,a,100\n").encode())
    assert ok[0]["amount"] == 100


def test_parse_short_row_and_empty_description():
    rows = bank_csv.parse("日付,金額,摘要\n2026/11/01,-300\n".encode())
    assert rows == [{"d": "2026-11-01", "description": "(摘要なし)", "amount": -300, "balance": None}]


# ---------------------------------------------------------------- 消込 önerisi
def _invoice(client, auth, issued, price=10_000):
    body = {"client": "株式会社テスト", "issued": issued, "due": "2026-12-31",
            "items": [{"name": "作業", "qty": 1, "unit_price": price, "rate": 10}]}
    return client.post("/api/v1/invoices", json=body, headers=auth).json()


def test_suggestion_requires_deposit_on_or_after_issue_and_one_per_invoice(client, auth):
    inv = _invoice(client, auth, "2026-11-10")
    assert inv["total"] == 11_000
    csv = ("日付,摘要,金額\n"
           "2026/11/09,前日入金,11000\n"     # fatura tarihinden önce → öneri yok
           "2026/11/10,当日入金,11000\n"     # aynı gün → öneri
           "2026/11/11,翌日入金,11000\n"     # aynı fatura ikinci kez önerilmez
           "2026/11/12,出金,-11000\n").encode()
    r = client.post("/api/v1/bank/import", content=csv, headers=auth).json()
    assert [(s["date"], s["invoice_no"]) for s in r["suggestions"]] == [("2026-11-10", inv["no"])]


def test_match_amount_mismatch_is_400(client, auth):
    inv = _invoice(client, auth, "2026-11-01")
    client.post("/api/v1/bank/import", content="日付,摘要,金額\n2026/11/02,入金,10999\n".encode(), headers=auth)
    tx = client.get("/api/v1/bank/transactions", headers=auth).json()["transactions"][0]
    r = client.post("/api/v1/bank/match", json={"tx_id": tx["id"], "invoice_no": inv["no"]}, headers=auth)
    assert r.status_code == 400
    assert client.post("/api/v1/bank/match", json={"tx_id": 999, "invoice_no": inv["no"]}, headers=auth).status_code == 404


# ---------------------------------------------------------------- silme ↔ banka bağı (düzeltme)
def test_deleting_bank_expense_allows_re_recording(client, auth):
    client.post("/api/v1/bank/import", content="日付,摘要,金額\n2026/11/05,家賃,-80000\n".encode(), headers=auth)
    tx = client.get("/api/v1/bank/transactions", headers=auth).json()["transactions"][0]
    e = client.post(f"/api/v1/bank/{tx['id']}/entry", json={"category": "通信費"}, headers=auth)
    assert e.status_code == 201
    assert client.delete(f"/api/v1/entries/{e.json()['id']}", headers=auth).status_code == 204
    tx2 = client.get("/api/v1/bank/transactions", headers=auth).json()["transactions"][0]
    assert tx2["entry_id"] is None
    again = client.post(f"/api/v1/bank/{tx['id']}/entry", json={"category": "地代家賃"}, headers=auth)
    assert again.status_code == 201 and again.json()["amount"] == 80_000


def test_delete_other_users_entry_is_404_and_keeps_bank_link(client, auth):
    client.post("/api/v1/bank/import", content="日付,摘要,金額\n2026/11/05,家賃,-80000\n".encode(), headers=auth)
    tx = client.get("/api/v1/bank/transactions", headers=auth).json()["transactions"][0]
    eid = client.post(f"/api/v1/bank/{tx['id']}/entry", json={"category": "地代家賃"}, headers=auth).json()["id"]
    other = client.post("/api/v1/admin/tokens", json={"user_id": "RV2"}, headers=ADMIN).json()["token"]
    assert client.delete(f"/api/v1/entries/{eid}", headers={"Authorization": f"Bearer {other}"}).status_code == 404
    assert client.get("/api/v1/bank/transactions", headers=auth).json()["transactions"][0]["entry_id"] == eid


def test_patch_with_no_fields_is_400(client, auth):
    e = client.post("/api/v1/entries", json={"date": "2026-11-01", "kind": "exp", "store": "A", "amount": 1100,
                                             "category": "雑費", "rate": 10}, headers=auth).json()
    assert client.patch(f"/api/v1/entries/{e['id']}", json={}, headers=auth).status_code == 400
    assert client.patch(f"/api/v1/entries/{e['id']}", json={"amount": None}, headers=auth).status_code == 400
