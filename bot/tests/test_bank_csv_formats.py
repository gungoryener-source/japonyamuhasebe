"""T-033: banka CSV başlıkları — kaynaklar docs/BANK_CSV.md.

Fixture'lar sentetiktir (kişisel veri yok); yalnızca başlık satırları kaynaklardan birebir alınmıştır.
"""
import pytest

import bank_csv

# ゆうちょBizダイレクト 操作説明書 18.4 (2023-05): 入出金区分 = 「受入」/「払出」, 取引金額 işaretsiz.
YUCHO_BIZ = (
    "取引日,入出金区分,取引内容,送金人名等,受入明細番号,取扱口数,取引金額,現在（貸付）高,EDI 情報等\n"
    "20261105,払出,振替,,,,\"3,300\",\"196,700\",\n"
    "20261102,受入,振込,ｻｸﾗｼﾖｳｼﾞ(ｶ,000123,1,\"100,000\",\"200,000\",INV-0001\n"
).encode("cp932")

# 京都銀行 Web-EB 入出金明細照会結果ファイル（ＣＳＶ形式） başlık satırı (項番1〜13).
KYOTO = (
    "照会口座,番号,勘定日,（起算日）,出金金額（円）,入金金額（円）,小切手区分,残高（円）,取引区分,明細区分,金融機関名,支店名,摘要\n"
    "普通 0000000,1,2026/11/02,2026/11/02,,\"50,000\",,\"150,000\",振込,,ほげ銀行,本店,ｶ)ﾃｽﾄ\n"
    "普通 0000000,2,2026/11/04,2026/11/04,\"8,800\",,,\"141,200\",口座振替,,,,ﾃﾞﾝｷﾀﾞｲ\n"
).encode("cp932")

# イーバンク銀行 (現 楽天銀行) — felica2money wiki (üçüncü taraf).
RAKUTEN = (
    "取引日,入出金(円),残高(円),入出金先内容\n"
    "20261101,-1200,98800,VISAデビット\n"
    "20261103,30000,128800,振込 ﾔﾏﾀﾞ ﾀﾛｳ\n"
).encode("cp932")

# ジャパンネット銀行 (現 PayPay銀行) — tarih üç sütunda (felica2money wiki, üçüncü taraf).
JNB = (
    '"操作日(年)","操作日(月)","操作日(日)","取引順番号","摘要","お支払金額","お預り金額","残高"\n'
    '"2026","11","01","1","Vデビット　ｱﾏｿﾞﾝ","2,980","","97,020"\n'
    '"2026","11","2","2","振込　ｽｽﾞｷ","","5,000","102,020"\n'
).encode("cp932")

# ソニー銀行 円普通預金 — felica2money wiki (üçüncü taraf).
SONY = (
    '"お取り引き日","摘要","お預け入れ額","お引き出し額","差し引き残高"\n'
    '"2026年11月01日","給与","250,000","","350,000"\n'
    '"2026年11月03日","カード","","4,400","345,600"\n'
).encode("cp932")


def _short(rows):
    return [(r["d"], r["amount"], r["balance"]) for r in rows]


def test_yucho_biz_direction_column():
    rows = bank_csv.parse(YUCHO_BIZ)
    assert _short(rows) == [("2026-11-05", -3300, 196700), ("2026-11-02", 100000, 200000)]
    # 送金人名等 摘要'ye eklenir (消込 eşleşmesi için gerekli); 受入明細番号 tutar/摘要 değildir
    assert rows[1]["description"] == "振込 ｻｸﾗｼﾖｳｼﾞ(ｶ"
    assert rows[0]["description"] == "振替"


@pytest.mark.parametrize("kind,sign", [("受入", 1), ("払出", -1), ("入金", 1), ("出金", -1), ("1", 1), ("2", -1)])
def test_direction_values(kind, sign):
    raw = f"取引日,入払区分,摘要,取引金額,残高\n2026/11/01,{kind},x,500,1000\n".encode()
    assert bank_csv.parse(raw)[0]["amount"] == 500 * sign


def test_direction_unknown_row_skipped_not_guessed():
    raw = ("取引日,入出金区分,摘要,取引金額\n"
           "2026/11/01,訂正,x,500\n"
           "2026/11/02,払出,y,700\n").encode()
    rows = bank_csv.parse(raw)
    assert [(r["d"], r["amount"]) for r in rows] == [("2026-11-02", -700)]


def test_direction_column_with_signed_amount_keeps_abs_logic():
    raw = "取引日,入出金区分,取引金額\n2026/11/01,払出,-700\n2026/11/02,受入,-50\n".encode()
    assert [r["amount"] for r in bank_csv.parse(raw)] == [-700, 50]


def test_kyoto_anser_csv():
    rows = bank_csv.parse(KYOTO)
    assert _short(rows) == [("2026-11-02", 50000, 150000), ("2026-11-04", -8800, 141200)]
    assert rows[0]["description"] == "振込 ｶ)ﾃｽﾄ"


def test_rakuten_signed_amount():
    rows = bank_csv.parse(RAKUTEN)
    assert _short(rows) == [("2026-11-01", -1200, 98800), ("2026-11-03", 30000, 128800)]
    assert rows[1]["description"] == "振込 ﾔﾏﾀﾞ ﾀﾛｳ"


def test_jnb_split_date_columns():
    rows = bank_csv.parse(JNB)
    assert _short(rows) == [("2026-11-01", -2980, 97020), ("2026-11-02", 5000, 102020)]
    assert rows[0]["description"] == "Vデビット　ｱﾏｿﾞﾝ"


def test_jnb_split_date_short_row_skipped():
    raw = JNB.decode("cp932") + '"2026","11"\n'
    assert len(bank_csv.parse(raw.encode())) == 2


def test_sony_yen():
    rows = bank_csv.parse(SONY)
    assert _short(rows) == [("2026-11-01", 250000, 350000), ("2026-11-03", -4400, 345600)]


def test_number_columns_not_used_as_amount():
    # 「受入明細番号」 eskiden 「受入」 → 入金 sütunu sayılabilirdi
    raw = "日付,受入明細番号,摘要,入金,出金\n2026/11/01,999,x,100,\n".encode()
    assert bank_csv.parse(raw)[0]["amount"] == 100


def test_utf8_bom_variant_same_result():
    assert bank_csv.parse(b"\xef\xbb\xbf" + RAKUTEN.decode("cp932").encode()) == bank_csv.parse(RAKUTEN)


def test_api_import_yucho(client_auth):
    client, auth = client_auth
    r = client.post("/api/v1/bank/import", headers=auth, content=YUCHO_BIZ)
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 2
    rows = client.get("/api/v1/bank/transactions", headers=auth).json()["transactions"]
    amounts = sorted(x["amount"] for x in rows)
    assert amounts == [-3300, 100000]


@pytest.fixture()
def client_auth(bot):
    from fastapi.testclient import TestClient
    client = TestClient(bot.app)
    tok = client.post("/api/v1/admin/tokens", json={"user_id": "BK33"},
                      headers={"X-Admin-Key": "test-admin"}).json()["token"]
    return client, {"Authorization": f"Bearer {tok}"}


# --- review (2026-11-08): T-033 kenar durumları ---

def test_direction_empty_value_row_skipped():
    # 入出金区分 boşsa yön bilinmez → satır atlanır (işaretsiz tutar gelir sayılmaz)
    raw = "取引日,入出金区分,摘要,取引金額\n2026/11/01,,x,500\n2026/11/02, 受入 ,y,700\n".encode()
    assert [(r["d"], r["amount"]) for r in bank_csv.parse(raw)] == [("2026-11-02", 700)]


def test_direction_zero_or_blank_amount_skipped():
    raw = "取引日,入出金区分,摘要,取引金額\n2026/11/01,払出,x,0\n2026/11/02,受入,y,\n".encode()
    assert bank_csv.parse(raw) == []


def test_split_date_fullwidth_parens_and_invalid_day_skipped():
    raw = ("操作日（年）,操作日（月）,操作日（日）,摘要,お支払金額,お預り金額,残高\n"
           "2026,2,30,x,100,,900\n"          # 存在しない日付 → atlanır
           "2026,3,1,y,,250,1150\n").encode("cp932")
    assert _short(bank_csv.parse(raw)) == [("2026-03-01", 250, 1150)]


def test_split_date_needs_all_three_parts():
    # yalnızca 年/月 sütunu varsa tarih başlığı sayılmaz → başlık bulunamaz
    raw = "操作日(年),操作日(月),摘要,お支払金額\n2026,11,x,100\n".encode()
    with pytest.raises(ValueError):
        bank_csv.parse(raw)


def test_balance_genzaidaka_variant():
    raw = "取引日,摘要,出金,入金,現在高\n2026/11/01,x,300,,9700\n".encode()
    assert _short(bank_csv.parse(raw)) == [("2026-11-01", -300, 9700)]
