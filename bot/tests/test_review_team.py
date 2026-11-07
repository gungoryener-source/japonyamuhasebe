"""Reviewer (2026-11-07): T-041 ekip üyeleri — yetki yükseltme ve LINE-only sahip defteri sınırları."""
import pytest
from fastapi.testclient import TestClient

PW = "correct-horse-1"
LINE_UID = "U" + "a" * 32


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def signup(client, email):
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": PW})
    assert r.status_code == 201, r.text
    return r.json()


def _line_owner_with_viewer(client, bot):
    """Yalnızca LINE ile kullanılan defter (hesap bağlı değil) + davetle katılan viewer."""
    owner_tok = bot.issue_token(LINE_UID, "line-panel")
    r = client.post("/api/v1/team/invites", headers=H(owner_tok), json={"role": "viewer"})
    assert r.status_code == 201, r.text
    view = signup(client, "view@example.jp")
    j = client.post("/api/v1/team/join", headers=H(view["token"]), json={"code": r.json()["code"]})
    assert j.status_code == 201, j.text
    return owner_tok, view, j.json()["token"]


def test_member_token_cannot_be_used_as_line_link_code(client, bot):
    """Üye oturum token'ı 「パネル」 bağlama kodu yerine verilirse viewer defterin sahibi olmamalı."""
    owner_tok, view, member_tok = _line_owner_with_viewer(client, bot)
    r = client.post("/api/v1/auth/link-line", headers=H(view["token"]), json={"code": member_tok})
    assert r.status_code == 400, r.text
    # viewer hâlâ viewer; kendi hesabı LINE defterine bağlanmadı
    assert client.get("/api/v1/auth/me", headers=H(member_tok)).json()["role"] == "viewer"
    me = client.get("/api/v1/auth/me", headers=H(view["token"])).json()
    assert me["user_id"] == view["user_id"] and me["role"] == "owner"
    # LINE sahibinin token'ı hâlâ sahip
    assert client.get("/api/v1/auth/me", headers=H(owner_tok)).json()["role"] == "owner"


def test_line_panel_code_still_links(client, bot):
    """Geriye uyum: gerçek LINE 「パネル」 kodu (account_id=0) bağlamaya devam eder."""
    acc = signup(client, "owner@example.jp")
    code = bot.issue_token(LINE_UID, "line-panel")
    r = client.post("/api/v1/auth/link-line", headers=H(acc["token"]), json={"code": code})
    assert r.status_code == 200, r.text
    assert r.json()["user_id"] == LINE_UID


def test_line_only_owner_member_listing_and_viewer_blocked(client, bot):
    owner_tok, view, member_tok = _line_owner_with_viewer(client, bot)
    m = client.get("/api/v1/team/members", headers=H(owner_tok)).json()["members"]
    assert [x["role"] for x in m] == ["viewer"]  # bağlı hesap yok → sahip satırı yok
    for path, body in (("/api/v1/team/invites", {"role": "viewer"}),):
        assert client.post(path, headers=H(member_tok), json=body).status_code == 403
    assert client.get("/api/v1/team/members", headers=H(member_tok)).status_code == 403
    assert client.post("/api/v1/billing/cancel", headers=H(member_tok)).status_code == 403


def test_member_cannot_switch_to_foreign_ledger(client, bot):
    _, view, _ = _line_owner_with_viewer(client, bot)
    other = signup(client, "other@example.jp")
    r = client.post("/api/v1/team/switch", headers=H(view["token"]), json={"user_id": other["user_id"]})
    assert r.status_code == 403
    r = client.post("/api/v1/team/switch", headers=H(view["token"]), json={"user_id": LINE_UID})
    assert r.status_code == 200 and r.json()["role"] == "viewer"


# ------------------------------------------------------------ T-025 (reviewer)
async def test_slow_ocr_reading_reply_failure_still_pushes(bot, monkeypatch, tmp_path):
    """「読み取り中」 reply ağ hatası verse bile OCR sonucu push ile gitmeli ve kayıt tek olmalı."""
    import asyncio

    import store
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINE_REPLY_WAIT_SEC", "0.05")
    pushed = []

    async def fake_push(uid, messages):
        pushed.append((uid, messages))

    async def bad_reply(token, messages):
        raise ConnectionError("down")

    async def fake_get_image(mid):
        return b"\xff\xd8jpg"

    async def slow_ocr(img):
        await asyncio.sleep(0.2)
        return [{"date": "2026-11-01", "kind": "exp", "store": "ローソン", "amount": 540, "rate": 8,
                 "category": "会議費", "invoice_no": ""}]

    monkeypatch.setattr(bot, "push", fake_push)
    monkeypatch.setattr(bot, "reply", bad_reply)
    monkeypatch.setattr(bot, "get_image", fake_get_image)
    monkeypatch.setattr(bot, "ocr_receipt", slow_ocr)
    await bot.handle_image("UR1", "tok", "m1")
    assert len(pushed) == 1 and pushed[0][1][0]["text"].startswith("登録しました")
    assert len(store.search_entries("UR1")) == 1
