"""T-061/T-062: 通帳取込（AI 読取）・取引先照合・確認・通帳整理表 Excel。

テストデータは架空（実在の通帳・取引先の値は使わない）。形式だけ実物に合わせている。
"""
import io
import json

import openpyxl
import pytest
from fastapi.testclient import TestClient

import counterparties as cp
import passbook

ADMIN = {"X-Admin-Key": "test-admin"}

PAGE = {"bank": "テスト銀行 本店", "opening_balance": 834545, "rows": [
    {"date": "2024-11-06", "withdrawal": 220, "deposit": 0, "description": "ATM手数料", "balance": 834325},
    {"date": "2024-11-07", "withdrawal": 200000, "deposit": 0, "description": "ﾌﾙﾊｼｲｰﾋﾟｰｵｰ(ｶ", "balance": 634325},
    {"date": "2024-11-07", "withdrawal": 550, "deposit": 0, "description": "ATM振込手数", "balance": 633775},
    {"date": "2024-11-07", "withdrawal": 200000, "deposit": 0, "description": "ATM支払", "balance": 433775},
    {"date": "2024-11-15", "withdrawal": 0, "deposit": 4300000, "description": "振込ｶ)ｴﾑｱｰﾙｴﾌ", "balance": 4733775},
    {"date": "2024-11-15", "withdrawal": 300000, "deposit": 0, "description": "ｶ)ﾄｸﾜｰﾙﾄﾞ", "balance": 4433775},
    {"date": "2024-11-19", "withdrawal": 0, "deposit": 2, "description": "お利息", "balance": 4433777},
    {"date": "2024-11-20", "withdrawal": 3300, "deposit": 0, "description": "EB基本手数料", "balance": 4430000},  # 誤読（正: 4430477）
    {"date": "2024-11-21", "withdrawal": 46200, "deposit": 0, "description": "ｾﾞﾝﾎﾟﾚﾝ(ｶ", "balance": 4384277},
]}


def ai_text(d):
    return "```json\n" + json.dumps(d, ensure_ascii=False) + "\n```"


def make_xlsx() -> bytes:
    """利用者の通帳整理表と同じ並び（架空の取引先）。"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "テスト銀行通帳"
    ws.append([None, "支出", "入金", None, None, "詳細", None, "2023-07-25 開始", None, None, "更新"])
    ws.append([None, None, None, None, None, None, None, None, None, "インボイス登録番号", None])
    ws.append(["2024-11-01", None, 300000, "⇒", None, "売上", "株式会社ＭＲＦ", None, None, "T6180001147206", None])
    ws.append(["2024-11-02", 500000, None, "⇒", None, "外注工賃", "株式会社トクワールド", None, None, "T6180001077782", None])
    ws.append(["2024-11-03", 46200, None, "⇒", None, "地代家賃", "全保連株式会社", None, None, "T9360001002793", None])
    ws.append(["2024-11-04", 220, None, "⇒", None, "手数料", "ATM手数料", None, None, None, None])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "UP"}, headers=ADMIN)
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------------------------------------------------------------- 照合キー
@pytest.mark.parametrize("desc,key", [
    ("ｶ)ｴﾑｱｰﾙｴﾌ", "エムアールエフ"), ("振込ｶ)ｴﾑｱｰﾙｴﾌ", "エムアールエフ"), ("ﾌﾙﾊｼｲｰﾋﾟｰｵｰ(ｶ", "フルハシイーピーオー"),
    ("ｶ)ﾄｸﾜｰﾙﾄﾞ", "トクワールド"), ("ﾕ)ﾔﾏﾀﾞｼﾖｳﾃﾝ", "ヤマダシヨウテン"), ("ﾄﾞ)ｱｵｿﾞﾗ", "アオゾラ"),
])
def test_key_from_description(desc, key):
    assert cp.key_from_description(desc) == key


def test_key_from_name():
    assert cp.key_from_name("株式会社ＭＲＦ") == "エムアールエフ"
    assert cp.key_from_name("フルハシEPO株式会社") == "フルハシイーピーオー"
    assert cp.key_from_name("全保連株式会社") == ""                      # 漢字 → フリガナが必要
    assert cp.key_from_name("全保連株式会社", "ゼンポレン") == "ゼンポレン"
    assert cp.key_from_name("x", "ゼンポレンカブシキガイシャ") == "ゼンポレン"
    assert cp.keys_match("フルハシイーピー", "フルハシイーピーオー")       # 通帳で切れた名称
    assert not cp.keys_match("エム", "エムアールエフ")


def test_system_rules():
    assert cp.system_rule("ATM手数料") == ("支払手数料", True)
    assert cp.system_rule("お利息") == ("受取利息", True)
    assert cp.system_rule("ATM支払") == ("現金", False)
    assert cp.system_rule("ｾﾌﾞﾝｷﾞﾝｺｳ") is None or cp.system_rule("セブン銀行") == ("現金", False)
    assert cp.corporate_check_digit_ok("6180001147206")


def test_parse_houjin_xml():
    xml = """<?xml version="1.0" encoding="UTF-8"?><corporations><count>2</count>
      <corporation><corporateNumber>9360001002793</corporateNumber><process>01</process><name>全保連株式会社</name>
        <furigana>ゼンポレン</furigana><prefectureName>沖縄県</prefectureName><cityName>那覇市</cityName><streetNumber>1</streetNumber><closeDate></closeDate></corporation>
      <corporation><corporateNumber>1111111111111</corporateNumber><process>99</process><name>消滅</name></corporation>
    </corporations>"""
    r = cp.parse_houjin_xml(xml)
    assert len(r) == 1 and r[0]["furigana"] == "ゼンポレン" and r[0]["corporate_number"] == "9360001002793"
    assert cp.parse_houjin_xml("<broken") == []


# ---------------------------------------------------------------- 通帳の読取・残高チェック
def test_parse_ai_and_balances():
    p = passbook.parse_ai(ai_text(PAGE))
    assert p["bank"] == "テスト銀行 本店" and len(p["rows"]) == 9 and p["opening_balance"] == 834545
    assert p["rows"][4] == {"d": "2024-11-15", "description": "振込ｶ)ｴﾑｱｰﾙｴﾌ", "amount": 4300000, "balance": 4733775}
    rows = passbook.check_balances(p["rows"], p["opening_balance"])
    oks = [r["balance_ok"] for r in rows]
    assert oks[:7] == [True] * 7 and oks[7] is False       # 誤読した行を検出
    assert oks[8] is False                                   # 次の行も前残高（誤読）とずれる
    assert passbook.parse_ai("読めません") == {"bank": "", "rows": [], "opening_balance": None}


# ---------------------------------------------------------------- API（取込 → 照合 → 確認 → Excel）
def test_full_flow(client, auth, bot, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    async def fake_read(data, key, model):
        return passbook.parse_ai(ai_text(PAGE))

    monkeypatch.setattr(passbook, "ai_read", fake_read)
    # 1) 既存の通帳整理表から取引先を取り込む
    r = client.post("/api/v1/counterparties/import", content=make_xlsx(), headers=auth)
    assert r.status_code == 200 and r.json()["imported"] == 3
    # 2) 通帳 PDF を取込（2回送っても重複しない）
    r1 = client.post("/api/v1/bank/passbook", content=b"%PDF-1.4 x", headers=auth).json()
    assert r1["read"] == 9 and r1["imported"] == 9 and r1["balance_errors"] == 2
    r2 = client.post("/api/v1/bank/passbook", content=b"%PDF-1.4 x", headers=auth).json()
    assert r2["imported"] == 0 and r2["duplicates"] == 9
    # 3) 照合
    rv = client.get("/api/v1/bank/review", headers=auth).json()
    rows = {x["description"]: x for x in rv["rows"]}
    assert rows["振込ｶ)ｴﾑｱｰﾙｴﾌ"]["counterparty"]["name"] == "株式会社ＭＲＦ"
    assert rows["振込ｶ)ｴﾑｱｰﾙｴﾌ"]["counterparty"]["registration_no"] == "T6180001147206"
    assert rows["振込ｶ)ｴﾑｱｰﾙｴﾌ"]["category"] == "売上高"
    assert rows["ｶ)ﾄｸﾜｰﾙﾄﾞ"]["category"] == "外注工賃"
    assert rows["ATM手数料"]["category"] == "支払手数料" and rows["ATM手数料"]["match"] == "rule"
    assert rows["ATM支払"]["book"] is False
    assert rows["ｾﾞﾝﾎﾟﾚﾝ(ｶ"]["counterparty"] is None                  # 漢字名 → まだ不明
    assert rows["EB基本手数料"]["balance_ok"] == 0
    assert rv["counts"]["balance_errors"] == 2
    # 4) 自動で決まった行をまとめて確定（残高 NG は除外）
    ids = [x["id"] for x in rv["rows"]]
    b = client.post("/api/v1/bank/confirm-matched", json={"ids": ids}, headers=auth).json()
    assert b["confirmed"] == 6 and b["skipped"] == 3
    # 5) 不明な取引先を1回確認 → 覚える
    zid = rows["ｾﾞﾝﾎﾟﾚﾝ(ｶ"]["id"]
    c = client.post(f"/api/v1/bank/{zid}/confirm", json={"category": "地代家賃", "counterparty_name": "全保連株式会社",
                                                         "registration_no": "T9360001002793"}, headers=auth)
    assert c.status_code == 200 and c.json()["entry_id"]
    assert cp.match("UP", "ｾﾞﾝﾎﾟﾚﾝ(ｶ")["how"] == "learned"
    assert client.post(f"/api/v1/bank/{zid}/confirm", json={"category": "地代家賃"}, headers=auth).status_code == 409
    # 帳簿: 売上・経費・利息（非課税）・手数料。現金引出は記帳しない
    import store
    ents = store.search_entries("UP")
    by_store = {(e["store"], e["amount"]): e for e in ents}
    sale = by_store[("株式会社ＭＲＦ", 4300000)]
    assert sale["kind"] == "inc" and sale["category"] == "売上高" and sale["invoice_no"] == "T6180001147206"
    assert by_store[("お利息", 2)]["rate"] == 0 and by_store[("お利息", 2)]["category"] == "受取利息"
    assert by_store[("全保連株式会社", 46200)]["invoice_no"] == "T9360001002793"
    assert not any(e["amount"] == 200000 and e["store"] == "ATM支払" for e in ents)
    # 6) 通帳整理表 Excel
    x = client.get("/api/v1/reports/bank.xlsx?date_from=2024-11-01&date_to=2024-11-30", headers=auth)
    assert x.status_code == 200
    ws = openpyxl.load_workbook(io.BytesIO(x.content)).active
    data = list(ws.iter_rows(min_row=2, values_only=True))
    assert len(data) == 10 and data[-1][0] == "合計"
    mrf = [r for r in data if r[4] == "株式会社ＭＲＦ"][0]
    assert mrf[2] == 4300000 and mrf[7] == "T6180001147206" and mrf[8] == "記帳済"


def test_passbook_needs_ai_and_lookup_needs_nta(client, auth, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("NTA_APP_ID", raising=False)
    assert client.post("/api/v1/bank/passbook", content=b"%PDF-", headers=auth).status_code == 503
    assert client.get("/api/v1/counterparties/lookup?desc=x", headers=auth).status_code == 503
    assert client.post("/api/v1/counterparties/import", content=b"not excel", headers=auth).status_code == 400
    assert client.post("/api/v1/counterparties", json={"name": "A", "registration_no": "T1"}, headers=auth).status_code == 400


# ---------------------------------------------------------------- LINE
async def test_line_passbook_mode_and_pdf(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bot, "ANTHROPIC_KEY", "k")

    async def fake_read(data, key, model):
        return passbook.parse_ai(ai_text(PAGE))

    monkeypatch.setattr(passbook, "ai_read", fake_read)
    msg, _ = bot.respond("UL2", "通帳")
    assert "30分間" in msg
    text, opts = await bot.process_image("UL2", b"\xff\xd8", "p1", "LINE")
    assert "通帳を読み取りました" in text and "新規 9件" in text and "残高が合わない行が 2件" in text
    text2, _ = await bot.process_image("UL3", b"%PDF-1.7", "p2", "LINE")    # PDF はモードなしでも通帳
    assert "新規 9件" in text2
    bot.respond("UL4", "Türkçe")
    bot.respond("UL4", "Banka defteri")
    t3, _ = await bot.process_image("UL4", b"\xff\xd8", "p3", "LINE")
    assert "Banka defteri okundu" in t3


async def test_line_passbook_without_ai(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bot, "ANTHROPIC_KEY", "")
    text, _ = await bot.process_image("UL5", b"%PDF-1.7", "p", "LINE")
    assert "AI の設定が必要" in text
