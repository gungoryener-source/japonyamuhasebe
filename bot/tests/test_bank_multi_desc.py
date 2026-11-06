"""T-051: banka CSV'de birden çok 摘要 sütunu (MUFG 「摘要」+「摘要内容」) birleştirilir;
eski biçimle (yalnızca ilk 摘要) alınmış hareketler yeniden içe aktarmada yineleme sayılır."""
import pytest
from fastapi.testclient import TestClient

ADMIN = {"X-Admin-Key": "test-admin"}

MUFG = """口座番号,普通 1234567
日付,摘要,摘要内容,支払い金額,預かり金額,差引残高
2026/11/02,振込,ｶ)ｻｸﾗｾｲｻｸｼﾖ,,"113,243","1,200,000"
2026/11/05,口座振替,ﾗｸﾃﾝﾓﾊﾞｲﾙ,"3,278",,"1,196,722"
2026/11/05,口座振替,ﾗｸﾃﾝﾓﾊﾞｲﾙ,"3,278",,"1,193,444"
""".encode("cp932")


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    tok = client.post("/api/v1/admin/tokens", json={"user_id": "M1"}, headers=ADMIN).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_join_multiple_description_columns():
    import bank_csv
    rows = bank_csv.parse(MUFG)
    assert [r["description"] for r in rows] == ["振込 ｶ)ｻｸﾗｾｲｻｸｼﾖ", "口座振替 ﾗｸﾃﾝﾓﾊﾞｲﾙ", "口座振替 ﾗｸﾃﾝﾓﾊﾞｲﾙ"]
    assert [r["legacy_description"] for r in rows] == ["振込", "口座振替", "口座振替"]


def test_blank_columns_skipped_and_three_columns():
    import bank_csv
    raw = ("日付,摘要,摘要内容,備考,金額\n"
           "2026/11/01,振込,,ﾒﾓ,100\n"          # orta sütun boş → atlanır
           "2026/11/02,,ｱｵｲ,,200\n"             # ilk sütun boş → yalnızca ikincisi
           "2026/11/03,カード,,,300\n"           # yalnızca ilki → eski biçimle aynı, legacy anahtarı yok
           "2026/11/04,,,,400\n").encode()       # hepsi boş
    rows = bank_csv.parse(raw)
    assert [r["description"] for r in rows] == ["振込 ﾒﾓ", "ｱｵｲ", "カード", "(摘要なし)"]
    assert rows[1]["legacy_description"] == "(摘要なし)"
    assert "legacy_description" not in rows[2] and "legacy_description" not in rows[3]


def test_single_description_column_unchanged():
    import bank_csv
    raku = "﻿取引日,入出金(円),取引後残高(円),入出金内容\n20261101,-66000,500000,ﾄｳｷﾖｳｼｴｱｵﾌｲｽ\n".encode()
    assert bank_csv.parse(raku) == [{"d": "2026-11-01", "description": "ﾄｳｷﾖｳｼｴｱｵﾌｲｽ", "amount": -66000,
                                     "balance": 500000}]


def test_amount_columns_not_taken_as_description():
    import bank_csv
    # 「お預入れ」「お引出し」 摘要 kalıbına uymaz; 「取引区分」 ikinci 摘要 sütunu olarak birleşir
    raw = "お取引日,お取引内容,取引区分,お引出し,お預入れ,残高\n2026/11/01,ﾃｽﾄ,振込,,500,9500\n".encode()
    assert bank_csv.parse(raw)[0] == {"d": "2026-11-01", "description": "ﾃｽﾄ 振込", "amount": 500,
                                      "balance": 9500, "legacy_description": "ﾃｽﾄ"}


def test_reimport_after_legacy_import_is_duplicate(bot, client, auth):
    """T-051 öncesi içe aktarılmış (yalnızca 「摘要」) satırlar yeniden alınınca çoğalmamalı."""
    import bank_csv
    import store
    legacy_rows = [{k: v for k, v in r.items() if k != "legacy_description"} | {"description": r["legacy_description"]}
                   for r in bank_csv.parse(MUFG)]
    uid = "M1"
    assert store.insert_bank_rows(uid, legacy_rows) == (3, 0)
    r = client.post("/api/v1/bank/import", content=MUFG, headers=auth).json()
    assert (r["parsed"], r["imported"], r["duplicates"]) == (3, 0, 3)
    # yeni biçimle alınan ikinci içe aktarma da yineleme
    assert client.post("/api/v1/bank/import", content=MUFG, headers=auth).json()["duplicates"] == 3
    assert len(client.get("/api/v1/bank/transactions", headers=auth).json()["transactions"]) == 3


def test_new_import_stores_joined_name_and_expense_store(client, auth):
    r = client.post("/api/v1/bank/import", content=MUFG, headers=auth).json()
    assert (r["imported"], r["duplicates"]) == (3, 0)
    again = client.post("/api/v1/bank/import", content=MUFG, headers=auth).json()
    assert (again["imported"], again["duplicates"]) == (0, 3)
    txs = client.get("/api/v1/bank/transactions", headers=auth).json()["transactions"]
    out = next(t for t in txs if t["amount"] == -3278)
    assert out["description"] == "口座振替 ﾗｸﾃﾝﾓﾊﾞｲﾙ"
    e = client.post(f"/api/v1/bank/{out['id']}/entry", json={"category": "通信費", "rate": 10}, headers=auth)
    assert e.status_code == 201 and e.json()["store"] == "口座振替 ﾗｸﾃﾝﾓﾊﾞｲﾙ"


def test_joined_description_truncated_to_200(client, auth):
    raw = ("日付,摘要,摘要内容,金額\n2026/11/01," + "あ" * 150 + "," + "い" * 150 + ",-100\n").encode()
    assert client.post("/api/v1/bank/import", content=raw, headers=auth).json()["imported"] == 1
    t = client.get("/api/v1/bank/transactions", headers=auth).json()["transactions"][0]
    assert len(t["description"]) == 200 and t["description"].startswith("あ" * 150 + " ")
