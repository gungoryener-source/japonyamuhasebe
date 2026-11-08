"""T-077: クレジットカード明細 CSV（見出しは語句で割り当て、会社名では分岐しない）。"""
import pytest
from fastapi.testclient import TestClient

import card_csv

HDR = "ご利用日,ご利用店名,ご利用金額,支払区分,今回回数,お支払日\n"


def csv_bytes(body: str, enc="utf-8") -> bytes:
    return body.encode(enc)


def test_basic_utf8_and_cp932():
    body = HDR + "2026/10/03,セブン-イレブン,1280,1,1,2026/11/27\n2026/10/05,JR東日本,-500,1,1,2026/11/27\n"
    for enc in ("utf-8", "cp932"):
        r = card_csv.parse(csv_bytes(body, enc))
        assert [(x["d"], x["amount"]) for x in r] == [("2026-10-03", -1280), ("2026-10-05", 500)]   # 返金は入金（正）
        assert r[0]["src"] == "card" and "(支払日 2026-11-27)" in r[0]["description"]


def test_metadata_before_header_and_note_rows_skipped():
    body = ("カード名,テストカード\n会員名,*****\n\n" + HDR +
            "2026/10/03,店A,1000,1,1,2026/11/27\n"
            "2026/10/09,店B,30000,3,1,2026/11/27\n"
            "※分割・リボ払いの手数料は別途ご請求します,,,,,\n"
            "合計,,31000,,,\n"
            "2026/10/20,分割払い手数料,120,,,2026/11/27\n"
            "2026/10/21,店C,0,1,1,\n"
            ",,,,,\n")
    r = card_csv.parse(csv_bytes(body))
    assert [x["amount"] for x in r] == [-1000, -30000]
    assert "[3]" in r[1]["description"] and "[1]" not in r[0]["description"]       # 分割は区分を残す


def test_other_headers_and_no_pay_date():
    r = card_csv.parse(csv_bytes("利用日,利用先,利用金額\n2026/10/03,Amazon,\"¥2,980\"\n"))
    assert r == [{"d": "2026-10-03", "description": "Amazon", "amount": -2980, "balance": None, "src": "card"}]


def test_does_not_use_payment_amount_column():
    r = card_csv.parse(csv_bytes("利用日,利用店名,支払金額,利用金額\n2026/10/03,店,900,1000\n"))
    assert r[0]["amount"] == -1000


def test_formula_text_kept_verbatim():
    r = card_csv.parse(csv_bytes(HDR + "2026/10/03,=HYPERLINK(\"x\"),500,1,1,\n"))
    assert r[0]["description"].startswith("=HYPERLINK")


def test_no_header_raises():
    with pytest.raises(ValueError):
        card_csv.parse(csv_bytes("a,b,c\n1,2,3\n"))


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def hdr(client, uid):
    t = client.post("/api/v1/admin/tokens", json={"user_id": uid}, headers={"X-Admin-Key": "test-admin"}).json()["token"]
    return {"Authorization": f"Bearer {t}"}


def test_api_import_dedup_and_pipeline(client):
    h = hdr(client, "C1")
    body = csv_bytes(HDR + "2026/10/03,コーヒー,500,1,1,\n2026/10/03,コーヒー,500,1,1,\n2026/10/04,書店,2200,1,1,\n")
    assert client.post("/api/v1/card/import", content=body).status_code == 401
    r = client.post("/api/v1/card/import", content=body, headers=h).json()
    assert (r["parsed"], r["imported"], r["duplicates"]) == (3, 3, 0)          # 同日同額の2件は別明細
    r2 = client.post("/api/v1/card/import", content=body, headers=h).json()
    assert (r2["imported"], r2["duplicates"]) == (0, 3)                         # 再取込みは重複
    tx = client.get("/api/v1/bank/transactions", headers=h).json()["transactions"]
    assert len(tx) == 3 and all(t["account"] == "クレジットカード" and t["amount"] < 0 for t in tx)
    # 未確認のまま → 経費に登録できる（既存フロー）。消込候補（請求書）にはならない
    assert client.get("/api/v1/bank/transactions", headers=h).json()["suggestions"] == []
    assert client.post("/api/v1/card/import", content=b"x,y\n1,2\n", headers=h).status_code == 400
    assert client.post("/api/v1/card/import", content=b"", headers=h).status_code == 400
    other = hdr(client, "C2")
    assert client.get("/api/v1/bank/transactions", headers=other).json()["transactions"] == []


def test_does_not_count_toward_receipt_quota(client):
    h = hdr(client, "C3")
    before = client.get("/api/v1/billing/status", headers=h).json()
    client.post("/api/v1/card/import", content=csv_bytes(HDR + "2026/10/03,店,500,1,1,\n"), headers=h)
    after = client.get("/api/v1/billing/status", headers=h).json()
    assert before == after
