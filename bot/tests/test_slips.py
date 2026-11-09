"""T-060: 仕切書（手書きの買取伝票）→ 確認キュー → 承認で売上、一覧 PDF。

AI の応答は実際の仕切書 3 枚（三通・ECO瀬戸・丸野商事）を人が読んだ値で再現している。
"""
import io
import json

import pytest
from fastapi.testclient import TestClient

import slips

ADMIN = {"X-Admin-Key": "test-admin"}

SANTSU = {"date": "2026-06-02", "issuer": "株式会社 三通", "registration_no": "",
          "lines": [{"item": "ステンレス", "qty": 45, "unit_price": 196, "amount": 8820},
                    {"item": "鉄A", "qty": 530, "unit_price": 54.5, "amount": 28885}], "total": 37705}
ECO = {"date": "2026-04-28", "issuer": "株式会社ECO瀬戸", "registration_no": "T4180001153800",
       "lines": [{"item": "鉄", "qty": 450, "unit_price": 50, "amount": 22500},
                 {"item": "アルミ", "qty": 70, "unit_price": 455, "amount": 31850},
                 {"item": "工雑A", "qty": 210, "unit_price": 250, "amount": 52500},
                 {"item": "給湯器", "qty": 30, "unit_price": 380, "amount": 11400}], "total": 118250}
MARUNO = {"date": "2026-05-14", "issuer": "(株)丸野商事", "registration_no": None,
          "lines": [{"item": "スクラップ", "qty": "1,210", "unit_price": "42", "amount": "50,820"},
                    {"item": "雑品上", "qty": None, "unit_price": None, "amount": None}], "total": "50820"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "US"}, headers=ADMIN)
    return {"Authorization": f"Bearer {r.json()['token']}"}


def ai_text(d: dict) -> str:
    return "以下です。\n```json\n" + json.dumps(d, ensure_ascii=False) + "\n```"


# ---------------------------------------------------------------- parsing / validation
def test_parse_ai_real_slips():
    s = slips.parse_ai(ai_text(SANTSU))
    assert s["d"] == "2026-06-02" and s["total"] == 37705 and len(s["lines"]) == 2
    assert slips.issues({**s, "lines": s["lines"]}) == []
    e = slips.parse_ai(ai_text(ECO))
    assert e["registration_no"] == "T4180001153800" and e["total"] == 118250 and slips.issues(e) == []
    m = slips.parse_ai(ai_text(MARUNO))
    assert m["lines"] == [{"item": "スクラップ", "qty": 1210.0, "unit_price": 42.0, "amount": 50820}]  # 空行は除外
    assert m["registration_no"] == "" and slips.issues(m) == []


def test_parse_ai_garbage():
    s = slips.parse_ai("読めませんでした")
    assert s == {"d": "", "issuer": "", "registration_no": "", "lines": [], "total": 0}
    assert "明細がありません" in slips.issues(s)


def test_issues_detects_misread_decimal():
    # 54.5 を 545 と読んだ場合: 数量×単価 と 金額 が合わない
    bad = slips.parse_ai(ai_text({**SANTSU, "lines": [SANTSU["lines"][0], {**SANTSU["lines"][1], "unit_price": 545}]}))
    msgs = slips.issues(bad)
    assert any("2行目" in m and "一致しません" in m for m in msgs)


def test_issues_total_mismatch_and_rounding():
    s = {"d": "2026-04-23", "issuer": "三通", "registration_no": "", "total": 24463,
         "lines": slips.clean_lines([{"item": "鉄筋", "qty": 475, "unit_price": 51.5, "amount": 24463}])}
    assert slips.issues(s) == []                      # 24,462.5 → 24,463（1円以内は許容）
    assert any("伝票合計" in m for m in slips.issues({**s, "total": 24000}))
    assert slips.round_half_up(24462.5) == 24463


def test_looks_like_slip():
    assert slips.looks_like_slip("口この商品は盗難品でほはありません 株式会社ECO瀬戸")
    assert slips.looks_like_slip("AI KAITAI 様 下記のとおり 申し上げます")
    assert not slips.looks_like_slip("ローソン 合計 ¥540 お預り ¥1000")


# ---------------------------------------------------------------- store flow
def test_approve_creates_sales_entry(bot):
    import store
    s = slips.create("U1", slips.parse_ai(ai_text(ECO)), image_path="receipts/x.jpg", reader="ai")
    assert s["status"] == "pending" and s["issues"] == []
    a = slips.approve("U1", s["id"])
    assert a["status"] == "approved" and a["entry_id"]
    rows = store.search_entries("U1")
    assert len(rows) == 1
    r = rows[0]
    assert (r["kind"], r["category"], r["amount"], r["rate"], r["store"], r["invoice_no"]) == \
        ("inc", "売上高", 118250, 10, "株式会社ECO瀬戸", "T4180001153800")
    with pytest.raises(ValueError):
        slips.approve("U1", s["id"])                   # 二重承認しない


def test_approve_blocked_when_issues(bot):
    s = slips.create("U1", {})
    with pytest.raises(ValueError, match="明細がありません"):
        slips.approve("U1", s["id"])


def test_duplicate_detection(bot):
    a = slips.create("U1", slips.parse_ai(ai_text(SANTSU)))
    b = slips.create("U1", slips.parse_ai(ai_text(SANTSU)))
    rows = {r["id"]: r for r in slips.list_("U1")}
    assert rows[b["id"]]["duplicate_of"] == a["id"]
    slips.reject("U1", b["id"])
    assert slips.duplicate_of("U1", slips.get("U1", a["id"])) is None


def test_other_user_cannot_see(bot):
    s = slips.create("U1", {})
    assert slips.get("U2", s["id"]) is None


# ---------------------------------------------------------------- API
def test_api_review_edit_approve_and_pdf(client, auth, bot):
    s = slips.create("US", slips.parse_ai(ai_text({**SANTSU, "lines": [SANTSU["lines"][0],
                                                                    {**SANTSU["lines"][1], "unit_price": 545}]})))
    r = client.get("/api/v1/slips?status=pending", headers=auth).json()
    assert r["counts"]["pending"] == 1 and r["slips"][0]["issues"]
    assert client.post(f"/api/v1/slips/{s['id']}/approve", headers=auth).status_code == 409
    fixed = [SANTSU["lines"][0], {**SANTSU["lines"][1], "unit_price": 54.5}]
    p = client.patch(f"/api/v1/slips/{s['id']}", json={"lines": fixed}, headers=auth)
    assert p.status_code == 200 and p.json()["issues"] == []
    assert client.post(f"/api/v1/slips/{s['id']}/approve", headers=auth).json()["status"] == "approved"
    assert client.patch(f"/api/v1/slips/{s['id']}", json={"total": 1}, headers=auth).status_code == 409
    slips.create("US", slips.parse_ai(ai_text(ECO)))
    pdf = client.get("/api/v1/reports/slips.pdf?date_from=2026-01-01&date_to=2026-12-31&status=all", headers=auth)
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    from pypdf import PdfReader
    text = "".join(pg.extract_text() for pg in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "仕切書一覧（2026年）" in text and "155,955" in text and "伝票 2 件" in text


def test_api_validation_and_auth(client, auth, bot):
    s = slips.create("US", {})
    assert client.get("/api/v1/slips").status_code == 401
    assert client.patch(f"/api/v1/slips/{s['id']}", json={"d": "2026/06/02"}, headers=auth).status_code == 400
    assert client.patch(f"/api/v1/slips/{s['id']}", json={"kind": "x"}, headers=auth).status_code == 422
    assert client.get("/api/v1/slips/99999", headers=auth).status_code == 404
    assert client.post(f"/api/v1/slips/{s['id']}/reject", headers=auth).json()["status"] == "rejected"


# ---------------------------------------------------------------- LINE
async def test_line_slip_mode_with_ai(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bot, "ANTHROPIC_KEY", "k")

    async def fake_ai(img, key, model):
        return slips.parse_ai(ai_text(MARUNO))

    monkeypatch.setattr(slips, "ai_extract", fake_ai)
    msg, opts = bot.respond("UL", "仕切書")
    assert "30分間" in msg
    text, options = await bot.process_image("UL", b"\xff\xd8", "m1", "LINE")
    assert "仕切書を受け付けました" in text and "丸野商事" in text and "¥50,820" in text
    assert [s["status"] for s in slips.list_("UL")] == ["pending"]
    import store
    assert store.search_entries("UL") == []           # 承認までは帳簿に入らない


async def test_line_slip_autodetect_without_ai(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bot, "ANTHROPIC_KEY", "")

    async def fake_ocr(img):
        return {"slip": True, "error": "仕切書"}

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)
    text, _ = await bot.process_image("UA", b"\xff\xd8", "m2", "LINE")
    assert "金額はパネルで入力してください" in text
    s = slips.list_("UA")[0]
    assert s["reader"] == "manual" and s["lines"] == []


async def test_line_slip_turkish(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bot, "ANTHROPIC_KEY", "")
    bot.respond("UT", "Türkçe")
    msg, opts = bot.respond("UT", "Hurda fişi")
    assert "30 dakika" in msg
    text, _ = await bot.process_image("UT", b"\xff\xd8", "m3", "LINE")
    assert "Hurda fişi alındı" in text and "Tutarları panelde girin" in text


def test_slip_history_create_update_approve_reject(client, auth, bot):
    """T-065c: 仕切書の作成・修正・承認・却下が audit_log に残り、GET /slips/{id}/history で見える。"""
    s = slips.create("US", slips.parse_ai(ai_text({**SANTSU, "lines": [SANTSU["lines"][0]]})))
    sid = s["id"]
    h = client.get(f"/api/v1/slips/{sid}/history", headers=auth).json()
    assert [r["action"] for r in h] == ["create"] and h[0]["before"] is None
    client.patch(f"/api/v1/slips/{sid}", json={"issuer": "修正後商店"}, headers=auth)
    client.patch(f"/api/v1/slips/{sid}", json={"issuer": "修正後商店"}, headers=auth)        # 変更なし → 履歴を増やさない
    h = client.get(f"/api/v1/slips/{sid}/history", headers=auth).json()
    assert [r["action"] for r in h] == ["create", "update"] and h[1]["changed"] == ["issuer"]
    assert h[1]["after"]["issuer"] == "修正後商店" and h[1]["actor"].startswith("WEB:")
    s3 = slips.create("US", slips.parse_ai(ai_text({**SANTSU, "lines": [SANTSU["lines"][0],
                                                                     {**SANTSU["lines"][1], "unit_price": 545}]})))
    client.patch(f"/api/v1/slips/{s3['id']}", json={"lines": [SANTSU["lines"][0], {**SANTSU["lines"][1], "unit_price": 54.5}]}, headers=auth)
    assert client.post(f"/api/v1/slips/{s3['id']}/approve", headers=auth).status_code == 200
    h = client.get(f"/api/v1/slips/{s3['id']}/history", headers=auth).json()
    assert [r["action"] for r in h] == ["create", "update", "update"]
    assert h[-1]["changed"] == ["entry_id", "status"] and h[-1]["after"]["status"] == "approved"
    s2 = slips.create("US", {"kind": "exp", "d": "2026-10-01", "issuer": "X", "total": 100})
    assert client.post(f"/api/v1/slips/{s2['id']}/reject", headers=auth).json()["status"] == "rejected"
    h2 = client.get(f"/api/v1/slips/{s2['id']}/history", headers=auth).json()
    assert h2[-1]["changed"] == ["status"] and h2[-1]["after"]["status"] == "rejected"
    assert client.get("/api/v1/audit?entity=slip", headers=auth).status_code == 200


def test_slip_history_isolation_and_404(client, auth, bot):
    s = slips.create("US", {})
    assert client.get("/api/v1/slips/99999/history", headers=auth).status_code == 404
    other = client.post("/api/v1/admin/tokens", json={"user_id": "UX9"}, headers={"X-Admin-Key": "test-admin"}).json()["token"]
    assert client.get(f"/api/v1/slips/{s['id']}/history", headers={"Authorization": f"Bearer {other}"}).status_code == 404
    assert client.get(f"/api/v1/slips/{s['id']}/history").status_code == 401
