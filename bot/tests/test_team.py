"""T-041 ekip üyeleri: davet, katılım, rol kontrolü (owner / accountant / viewer), üye çıkarma, defter geçişi."""
from datetime import datetime, timedelta

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


def invite(client, owner_tok, role):
    r = client.post("/api/v1/team/invites", headers=H(owner_tok), json={"role": role})
    assert r.status_code == 201, r.text
    return r.json()["code"]


@pytest.fixture()
def team_setup(client):
    """owner + accountant + viewer; her üyenin owner defteri için token'ı."""
    owner = signup(client, "owner@example.jp")
    acc = signup(client, "acc@example.jp")
    view = signup(client, "view@example.jp")
    r1 = client.post("/api/v1/team/join", headers=H(acc["token"]), json={"code": invite(client, owner["token"], "accountant")})
    r2 = client.post("/api/v1/team/join", headers=H(view["token"]), json={"code": invite(client, owner["token"], "viewer")})
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["user_id"] == owner["user_id"] and r1.json()["role"] == "accountant"
    return {"owner": owner, "acc": acc, "view": view, "acc_tok": r1.json()["token"], "view_tok": r2.json()["token"]}


# ------------------------------------------------------------ katılım
def test_join_gives_access_to_owner_ledger(client, team_setup):
    t = team_setup
    assert client.post("/api/v1/entries", headers=H(t["owner"]["token"]), json=ENTRY).status_code == 201
    for tok in (t["acc_tok"], t["view_tok"]):
        rows = client.get("/api/v1/entries", headers=H(tok)).json()
        rows = rows["entries"] if isinstance(rows, dict) else rows
        assert len(rows) == 1
    me = client.get("/api/v1/auth/me", headers=H(t["view_tok"])).json()
    assert me == {"user_id": t["owner"]["user_id"], "role": "viewer",
                  "account": {"id": t["view"]["account"]["id"], "email": "view@example.jp", "email_verified": False}}
    assert client.get("/api/v1/auth/me", headers=H(t["owner"]["token"])).json()["role"] == "owner"
    # Üyenin kendi defteri ayrı kalır
    own = client.get("/api/v1/entries", headers=H(t["acc"]["token"])).json()
    assert len(own["entries"] if isinstance(own, dict) else own) == 0


def test_invite_single_use_and_expiry(client, bot):
    owner = signup(client, "owner@example.jp")
    a, b = signup(client, "a@example.jp"), signup(client, "b@example.jp")
    code = invite(client, owner["token"], "viewer")
    assert client.post("/api/v1/team/join", headers=H(a["token"]), json={"code": code}).status_code == 201
    assert client.post("/api/v1/team/join", headers=H(b["token"]), json={"code": code}).status_code == 400
    # süresi dolmuş
    code2 = invite(client, owner["token"], "viewer")
    import store
    import team
    past = (datetime.now(store.JST) - timedelta(seconds=1)).isoformat()
    with store.tx() as con:
        con.execute("UPDATE team_invites SET expires_at=? WHERE code_hash=?", (past, team._hash(code2)))
    assert client.post("/api/v1/team/join", headers=H(b["token"]), json={"code": code2}).status_code == 400
    assert client.post("/api/v1/team/join", headers=H(b["token"]), json={"code": "iv_nope"}).status_code == 400


def test_invite_ttl_is_seven_days(client):
    owner = signup(client, "owner@example.jp")
    r = client.post("/api/v1/team/invites", headers=H(owner["token"]), json={"role": "accountant"}).json()
    import store
    exp = datetime.fromisoformat(r["expires_at"])
    delta = exp - datetime.now(store.JST)
    assert timedelta(days=6, hours=23) < delta <= timedelta(days=7)
    assert r["code"].startswith("iv_")


def test_join_rejections(client, team_setup):
    t = team_setup
    # kendi defterine katılamaz
    code = invite(client, t["owner"]["token"], "viewer")
    assert client.post("/api/v1/team/join", headers=H(t["owner"]["token"]), json={"code": code}).status_code == 409
    # zaten üye
    assert client.post("/api/v1/team/join", headers=H(t["acc"]["token"]), json={"code": code}).status_code == 409
    # kod 409'da tüketilmedi → başka biri kullanabilir
    other = signup(client, "other@example.jp")
    assert client.post("/api/v1/team/join", headers=H(other["token"]), json={"code": code}).status_code == 201


def test_join_requires_account(client, bot):
    owner = signup(client, "owner@example.jp")
    code = invite(client, owner["token"], "viewer")
    import store
    line_tok = store.issue_token("U_line_only", "line-panel")  # hesapsız LINE defteri
    assert client.post("/api/v1/team/join", headers=H(line_tok), json={"code": code}).status_code == 403


def test_invite_role_validation(client):
    owner = signup(client, "owner@example.jp")
    for role in ("owner", "admin", ""):
        assert client.post("/api/v1/team/invites", headers=H(owner["token"]), json={"role": role}).status_code == 422


def test_open_invite_cap(client):
    import team
    owner = signup(client, "owner@example.jp")
    for _ in range(team.MAX_OPEN_INVITES):
        invite(client, owner["token"], "viewer")
    assert client.post("/api/v1/team/invites", headers=H(owner["token"]), json={"role": "viewer"}).status_code == 409


# ------------------------------------------------------------ rol kontrolü
def test_viewer_cannot_write(client, team_setup):
    t = team_setup
    v = H(t["view_tok"])
    eid = client.post("/api/v1/entries", headers=H(t["owner"]["token"]), json=ENTRY).json()["id"]
    assert client.post("/api/v1/entries", headers=v, json=ENTRY).status_code == 403
    assert client.patch(f"/api/v1/entries/{eid}", headers=v, json={"amount": 1}).status_code == 403
    assert client.delete(f"/api/v1/entries/{eid}", headers=v).status_code == 403
    assert client.post("/api/v1/receipts/ocr", headers=v, content=b"x").status_code == 403
    assert client.post("/api/v1/bank/import", headers=v, content=b"x").status_code == 403
    assert client.post("/api/v1/bank/match", headers=v, json={"tx_id": 1, "invoice_no": "X"}).status_code == 403
    assert client.post("/api/v1/bank/1/entry", headers=v, json={}).status_code == 403
    assert client.put("/api/v1/profile", headers=v, json={"business_name": "x"}).status_code == 403
    assert client.post("/api/v1/invoices", headers=v, json=INVOICE).status_code == 403
    assert client.post("/api/v1/invoices/X/paid", headers=v).status_code == 403
    # okuma serbest
    for path in ("/api/v1/summary", "/api/v1/entries", "/api/v1/invoices", "/api/v1/profile",
                 "/api/v1/bank/transactions", "/api/v1/pl?year=2026", "/api/v1/export.csv?year=2026",
                 "/api/v1/billing/status"):
        assert client.get(path, headers=v).status_code == 200, path
    # kayıt değişmedi
    rows = client.get("/api/v1/entries", headers=v).json()
    rows = rows["entries"] if isinstance(rows, dict) else rows
    assert [r["amount"] for r in rows] == [1100]


def test_accountant_can_edit_accounting_data(client, team_setup):
    t = team_setup
    a = H(t["acc_tok"])
    r = client.post("/api/v1/entries", headers=a, json=ENTRY)
    assert r.status_code == 201
    eid = r.json()["id"]
    assert client.patch(f"/api/v1/entries/{eid}", headers=a, json={"amount": 2200}).status_code == 200
    assert client.put("/api/v1/profile", headers=a, json={"business_name": "テスト商店"}).status_code == 200
    assert client.post("/api/v1/invoices", headers=a, json=INVOICE).status_code == 201
    assert client.delete(f"/api/v1/entries/{eid}", headers=a).status_code == 204
    # kayıt sahibin defterine yazıldı
    assert client.get("/api/v1/profile", headers=H(t["owner"]["token"])).json()["business_name"] == "テスト商店"


@pytest.mark.parametrize("who", ["acc_tok", "view_tok"])
def test_owner_only_operations(client, team_setup, who):
    t = team_setup
    h = H(t[who])
    assert client.get("/api/v1/team/members", headers=h).status_code == 403
    assert client.post("/api/v1/team/invites", headers=h, json={"role": "viewer"}).status_code == 403
    acc_id = t["acc"]["account"]["id"]
    assert client.patch(f"/api/v1/team/members/{acc_id}", headers=h, json={"role": "viewer"}).status_code == 403
    assert client.delete(f"/api/v1/team/members/{acc_id}", headers=h).status_code == 403
    assert client.post("/api/v1/billing/checkout", headers=h, json={"plan": "personal"}).status_code == 403
    assert client.post("/api/v1/billing/cancel", headers=h).status_code == 403
    # üye, sahibin defterini başka bir LINE defterine yeniden bağlayamaz
    assert client.post("/api/v1/auth/link-line", headers=h, json={"code": "tk_x"}).status_code == 403


# ------------------------------------------------------------ yönetim
def test_members_list_and_role_change_takes_effect_immediately(client, team_setup):
    t = team_setup
    o = H(t["owner"]["token"])
    body = client.get("/api/v1/team/members", headers=o).json()
    assert [(m["email"], m["role"]) for m in body["members"]] == [
        ("owner@example.jp", "owner"), ("acc@example.jp", "accountant"), ("view@example.jp", "viewer")]
    assert body["invites"] == []
    acc_id = t["acc"]["account"]["id"]
    assert client.patch(f"/api/v1/team/members/{acc_id}", headers=o, json={"role": "viewer"}).status_code == 200
    # aynı (eski) token artık viewer
    assert client.post("/api/v1/entries", headers=H(t["acc_tok"]), json=ENTRY).status_code == 403
    assert client.patch("/api/v1/team/members/999999", headers=o, json={"role": "viewer"}).status_code == 404


def test_remove_member_revokes_access(client, team_setup):
    t = team_setup
    o = H(t["owner"]["token"])
    acc_id = t["acc"]["account"]["id"]
    assert client.delete(f"/api/v1/team/members/{acc_id}", headers=o).status_code == 204
    assert client.get("/api/v1/summary", headers=H(t["acc_tok"])).status_code == 401
    assert client.delete(f"/api/v1/team/members/{acc_id}", headers=o).status_code == 404
    # üyenin kendi defteri ve oturumu etkilenmez
    assert client.get("/api/v1/summary", headers=H(t["acc"]["token"])).status_code == 200


def test_revoke_invite(client):
    owner = signup(client, "owner@example.jp")
    o = H(owner["token"])
    code = invite(client, owner["token"], "accountant")
    inv = client.get("/api/v1/team/members", headers=o).json()["invites"]
    assert len(inv) == 1 and inv[0]["role"] == "accountant" and "code" not in inv[0]
    assert client.delete(f"/api/v1/team/invites/{inv[0]['id']}", headers=o).status_code == 204
    assert client.delete(f"/api/v1/team/invites/{inv[0]['id']}", headers=o).status_code == 404
    assert client.delete("/api/v1/team/invites/zzz%25", headers=o).status_code == 404
    other = signup(client, "x@example.jp")
    assert client.post("/api/v1/team/join", headers=H(other["token"]), json={"code": code}).status_code == 400


def test_owner_cannot_revoke_other_ledgers_invite(client):
    a = signup(client, "a@example.jp")
    b = signup(client, "b@example.jp")
    invite(client, a["token"], "viewer")
    inv_id = client.get("/api/v1/team/members", headers=H(a["token"])).json()["invites"][0]["id"]
    assert client.delete(f"/api/v1/team/invites/{inv_id}", headers=H(b["token"])).status_code == 404


# ------------------------------------------------------------ defter geçişi
def test_ledgers_and_switch(client, team_setup):
    t = team_setup
    owner_uid = t["owner"]["user_id"]
    client.put("/api/v1/profile", headers=H(t["owner"]["token"]), json={"business_name": "山田商店"})
    body = client.get("/api/v1/team/ledgers", headers=H(t["acc"]["token"])).json()
    assert body["current"] == t["acc"]["user_id"]
    assert [(l["user_id"], l["role"]) for l in body["ledgers"]] == [(t["acc"]["user_id"], "owner"),
                                                                    (owner_uid, "accountant")]
    assert body["ledgers"][1]["business_name"] == "山田商店"
    # kendi defterinden sahibin defterine geç
    r = client.post("/api/v1/team/switch", headers=H(t["acc"]["token"]), json={"user_id": owner_uid})
    assert r.status_code == 200 and r.json()["role"] == "accountant"
    assert client.get("/api/v1/auth/me", headers=H(r.json()["token"])).json()["user_id"] == owner_uid
    # üye oturumundan kendi defterine geri dön → owner
    back = client.post("/api/v1/team/switch", headers=H(r.json()["token"]), json={"user_id": t["acc"]["user_id"]})
    assert back.status_code == 200 and back.json()["role"] == "owner"
    # yetkisiz defter
    stranger = signup(client, "s@example.jp")
    assert client.post("/api/v1/team/switch", headers=H(stranger["token"]),
                       json={"user_id": owner_uid}).status_code == 403


# ------------------------------------------------------------ token ve hesap etkileşimleri
def test_member_sessions_do_not_evict_owner_tokens(client, team_setup):
    import store
    t = team_setup
    for _ in range(store.MAX_TOKENS_PER_USER + 2):
        client.post("/api/v1/team/switch", headers=H(t["acc"]["token"]), json={"user_id": t["owner"]["user_id"]})
    assert client.get("/api/v1/summary", headers=H(t["owner"]["token"])).status_code == 200
    assert client.get("/api/v1/summary", headers=H(t["view_tok"])).status_code == 200


def test_password_reset_closes_member_sessions(client, team_setup):
    import accounts
    t = team_setup
    token = accounts.request_password_reset("acc@example.jp")
    accounts.confirm_password_reset(token, "new-password-123")
    assert client.get("/api/v1/summary", headers=H(t["acc_tok"])).status_code == 401
    assert client.get("/api/v1/summary", headers=H(t["view_tok"])).status_code == 200


def test_link_line_blocked_when_ledger_has_members(client, team_setup):
    import store
    t = team_setup
    line_code = store.issue_token("U_line_owner", "line-panel")
    r = client.post("/api/v1/auth/link-line", headers=H(t["owner"]["token"]), json={"code": line_code})
    assert r.status_code == 409
    assert client.get("/api/v1/summary", headers=H(t["acc_tok"])).status_code == 200


def test_legacy_line_token_is_owner(client, bot):
    import store
    tok = store.issue_token("U_line", "line-panel")
    me = client.get("/api/v1/auth/me", headers=H(tok)).json()
    assert me == {"user_id": "U_line", "role": "owner", "account": None}
    assert client.post("/api/v1/entries", headers=H(tok), json=ENTRY).status_code == 201
    # hesapsız LINE sahibi de davet üretebilir
    assert client.post("/api/v1/team/invites", headers=H(tok), json={"role": "viewer"}).status_code == 201


def test_init_db_adds_account_id_column_to_old_tokens_table(tmp_path, monkeypatch):
    import os
    if os.environ.get("DATABASE_URL"):
        pytest.skip("SQLite migration testi")
    import sqlite3
    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE api_tokens(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, label TEXT DEFAULT '',"
                " created_at TEXT NOT NULL)")
    con.execute("INSERT INTO api_tokens VALUES('h','U1','old','2026-01-01T00:00:00+09:00')")
    con.commit()
    con.close()
    monkeypatch.setenv("DB_PATH", str(db))
    import store
    store.init_db()
    with store.tx() as c:
        row = c.execute("SELECT user_id, account_id FROM api_tokens WHERE token_hash='h'").fetchone()
    assert row["user_id"] == "U1" and row["account_id"] == 0
