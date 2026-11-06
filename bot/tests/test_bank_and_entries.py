import pytest
from fastapi.testclient import TestClient

ADMIN = {"X-Admin-Key": "test-admin"}

# 三菱UFJ / ゆうちょ風（Shift_JIS, 入金・出金 ayrı sütun, başlıktan önce hesap satırı）
MUFG = """口座番号,普通 1234567
日付,摘要,摘要内容,支払い金額,預かり金額,差引残高
2026/11/02,振込,ｶ)ｻｸﾗｾｲｻｸｼﾖ,,"113,243","1,200,000"
2026/11/05,口座振替,ﾗｸﾃﾝﾓﾊﾞｲﾙ,"3,278",,"1,196,722"
2026/11/05,口座振替,ﾗｸﾃﾝﾓﾊﾞｲﾙ,"3,278",,"1,193,444"
""".encode("cp932")

# 楽天銀行風（UTF-8 BOM, 符号付き金額）
RAKUTEN = "﻿取引日,入出金(円),取引後残高(円),入出金内容\n20261101,-66000,500000,ﾄｳｷﾖｳｼｴｱｵﾌｲｽ\n20261103,990000,1490000,ｱｵｲｼﾖｳｼﾞ\n".encode()


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    tok = client.post("/api/v1/admin/tokens", json={"user_id": "B1"}, headers=ADMIN).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_bank_csv_parse_variants():
    import bank_csv
    rows = bank_csv.parse(MUFG)
    assert rows[0] == {"d": "2026-11-02", "description": "振込 ｶ)ｻｸﾗｾｲｻｸｼﾖ", "amount": 113_243, "balance": 1_200_000,
                       "legacy_description": "振込"}   # T-051: 摘要 + 摘要内容
    assert rows[1]["amount"] == -3278 and len(rows) == 3
    r2 = bank_csv.parse(RAKUTEN)
    assert [(r["d"], r["amount"]) for r in r2] == [("2026-11-01", -66000), ("2026-11-03", 990000)]
    with pytest.raises(ValueError):
        bank_csv.parse(b"a,b,c\n1,2,3\n")


def test_import_dedupe_match_and_expense(client, auth):
    body = {"client": "株式会社サクラ", "issued": "2026-11-01", "due": "2026-11-30",
            "items": [{"name": "保守", "qty": 1, "unit_price": 100_000, "rate": 10},
                      {"name": "弁当", "qty": 3, "unit_price": 1_001, "rate": 8}]}
    inv = client.post("/api/v1/invoices", json=body, headers=auth).json()
    assert inv["total"] == 113_243
    r = client.post("/api/v1/bank/import", content=MUFG, headers=auth).json()
    assert (r["parsed"], r["imported"], r["duplicates"]) == (3, 3, 0)   # aynı gün iki eş satır ayrı sayılır
    assert r["suggestions"] == [{"tx_id": 1, "invoice_no": inv["no"], "client": "株式会社サクラ", "amount": 113_243, "date": "2026-11-02"}]
    again = client.post("/api/v1/bank/import", content=MUFG, headers=auth).json()
    assert (again["imported"], again["duplicates"]) == (0, 3)

    m = client.post("/api/v1/bank/match", json={"tx_id": 1, "invoice_no": inv["no"]}, headers=auth)
    assert m.status_code == 200 and m.json()["status"] == "paid" and m.json()["paid_on"] == "2026-11-02"
    assert client.post("/api/v1/bank/match", json={"tx_id": 1, "invoice_no": inv["no"]}, headers=auth).status_code == 409
    assert client.get("/api/v1/bank/transactions", headers=auth).json()["suggestions"] == []

    e = client.post("/api/v1/bank/2/entry", json={"category": "通信費", "rate": 10}, headers=auth)
    assert e.status_code == 201 and e.json()["amount"] == 3278 and e.json()["kind"] == "exp"
    assert client.post("/api/v1/bank/2/entry", json={"category": "通信費"}, headers=auth).status_code == 409
    assert client.post("/api/v1/bank/1/entry", json={"category": "通信費"}, headers=auth).status_code == 409
    assert client.post("/api/v1/bank/3/entry", json={"category": "売上高"}, headers=auth).status_code == 400


def test_bank_isolated_between_users(client, auth):
    client.post("/api/v1/bank/import", content=RAKUTEN, headers=auth)
    other = client.post("/api/v1/admin/tokens", json={"user_id": "B2"}, headers=ADMIN).json()["token"]
    h2 = {"Authorization": f"Bearer {other}"}
    assert client.get("/api/v1/bank/transactions", headers=h2).json()["transactions"] == []
    assert client.post("/api/v1/bank/1/entry", json={"category": "地代家賃"}, headers=h2).status_code == 404


def test_bank_import_errors(client, auth):
    assert client.post("/api/v1/bank/import", content=b"", headers=auth).status_code == 400
    assert client.post("/api/v1/bank/import", content=b"x,y\n1,2", headers=auth).status_code == 400


def test_patch_and_delete_entry(client, auth):
    e = client.post("/api/v1/entries", json={"date": "2026-11-01", "kind": "exp", "store": "A", "amount": 1100,
                                             "category": "雑費", "rate": 10}, headers=auth).json()
    p = client.patch(f"/api/v1/entries/{e['id']}", json={"category": "通信費", "rate": 8, "date": "2026-11-02"}, headers=auth)
    assert p.status_code == 200 and (p.json()["category"], p.json()["rate"], p.json()["d"]) == ("通信費", 8, "2026-11-02")
    assert client.patch(f"/api/v1/entries/{e['id']}", json={"rate": 5}, headers=auth).status_code == 400
    assert client.patch("/api/v1/entries/999", json={"rate": 8}, headers=auth).status_code == 404
    assert client.delete(f"/api/v1/entries/{e['id']}", headers=auth).status_code == 204
    assert client.delete(f"/api/v1/entries/{e['id']}", headers=auth).status_code == 404


async def test_receipt_ocr_endpoint(client, auth, bot, monkeypatch):
    async def fake(img):
        assert img == b"IMG"
        return [{"date": "2026-11-01", "kind": "exp", "store": "ローソン", "category": "会議費", "invoice_no": "", "amount": 540, "rate": 8}]
    monkeypatch.setattr(bot, "ocr_receipt", fake)
    r = client.post("/api/v1/receipts/ocr", content=b"IMG", headers=auth).json()
    assert r["ok"] and r["entries"][0]["amount"] == 540
    assert client.get("/api/v1/entries", headers=auth).json() == []   # kaydetmez

    async def fail(img):
        return {"error": "合計金額が見つかりませんでした", "partial": {"date": "2026-11-01"}}
    monkeypatch.setattr(bot, "ocr_receipt", fail)
    r = client.post("/api/v1/receipts/ocr", content=b"IMG", headers=auth).json()
    assert not r["ok"] and r["partial"]["date"] == "2026-11-01"


def test_channels(client, auth):
    r = client.get("/api/v1/channels", headers=auth).json()
    assert r["line"]["configured"] is True and r["whatsapp"]["configured"] is False
    assert "通信費" in r["categories"] and "secret" not in str(r).lower()
