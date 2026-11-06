"""T-040 hesap sistemi: kayıt, giriş, kullanıcı ayrımı, LINE defteri bağlama, parola sıfırlama."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

PW = "correct-horse-1"


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def signup(client, email="taro@example.jp", password=PW):
    return client.post("/api/v1/auth/signup", json={"email": email, "password": password})


def bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


def add_entry(client, tok, amount=1100):
    return client.post("/api/v1/entries", headers=bearer(tok), json={
        "date": "2026-10-05", "kind": "exp", "store": "コンビニ", "amount": amount,
        "category": "消耗品費", "rate": 10})


# ------------------------------------------------------------ parola yardımcıları
def test_password_hash_roundtrip():
    import accounts
    h = accounts.hash_password(PW)
    assert h.startswith("scrypt$") and PW not in h
    assert accounts.verify_password(PW, h)
    assert not accounts.verify_password(PW + "x", h)
    assert not accounts.verify_password(PW, "garbage")
    assert accounts.hash_password(PW) != h  # tuzlu


def test_password_policy_boundaries():
    import accounts
    accounts.check_password_policy("a" * 10)
    accounts.check_password_policy("a" * 128)
    with pytest.raises(accounts.AccountError):
        accounts.check_password_policy("a" * 9)
    with pytest.raises(accounts.AccountError):
        accounts.check_password_policy("a" * 129)


# ------------------------------------------------------------ kayıt / giriş
def test_signup_returns_working_token(client):
    r = signup(client)
    assert r.status_code == 201
    body = r.json()
    assert body["account"]["email"] == "taro@example.jp"
    assert body["user_id"].startswith("web:")
    assert client.get("/api/v1/summary", headers=bearer(body["token"])).status_code == 200
    me = client.get("/api/v1/auth/me", headers=bearer(body["token"])).json()
    assert me["account"]["email"] == "taro@example.jp" and me["account"]["email_verified"] is False


def test_signup_validation(client):
    assert signup(client, password="short").status_code == 400
    assert signup(client, email="not-an-email").status_code == 400
    assert signup(client).status_code == 201
    # aynı e-posta (büyük/küçük harf ve boşluk normalize)
    r = signup(client, email="  Taro@Example.JP ")
    assert r.status_code == 409


def test_login_ok_and_wrong_password(client):
    signup(client)
    r = client.post("/api/v1/auth/login", json={"email": "TARO@example.jp", "password": PW})
    assert r.status_code == 200
    assert client.get("/api/v1/summary", headers=bearer(r.json()["token"])).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "taro@example.jp", "password": PW + "x"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "nobody@example.jp", "password": PW}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "bad", "password": PW}).status_code == 401


def test_users_are_isolated(client):
    a = signup(client, "a@example.jp").json()
    b = signup(client, "b@example.jp").json()
    assert a["user_id"] != b["user_id"]
    assert add_entry(client, a["token"]).status_code == 201
    rows_b = client.get("/api/v1/entries", headers=bearer(b["token"])).json()
    rows_a = client.get("/api/v1/entries", headers=bearer(a["token"])).json()
    items = lambda x: x["items"] if isinstance(x, dict) else x  # noqa: E731
    assert len(items(rows_a)) == 1 and len(items(rows_b)) == 0


def test_me_without_account(client):
    tok = client.post("/api/v1/admin/tokens", json={"user_id": "U-line"}, headers={"X-Admin-Key": "test-admin"}).json()["token"]
    assert client.get("/api/v1/auth/me", headers=bearer(tok)).json() == {"user_id": "U-line", "account": None}
    assert client.get("/api/v1/auth/me").status_code == 401


# ------------------------------------------------------------ LINE defteri bağlama
def line_code(bot, user_id="Uline1"):
    return bot.issue_token(user_id, "line-panel")


def test_link_line_ledger(bot, client):
    import store
    store.add_entry("Uline1", {"date": "2026-10-01", "kind": "exp", "store": "JR", "amount": 500,
                               "category": "旅費交通費", "rate": 10})
    acc = signup(client).json()
    code = line_code(bot)
    r = client.post("/api/v1/auth/link-line", json={"code": code}, headers=bearer(acc["token"]))
    assert r.status_code == 200, r.text
    new = r.json()
    assert new["user_id"] == "Uline1"
    # yeni token LINE defterini görür; eski web token'ı ve paylaşılmış kod iptal
    assert client.get("/api/v1/summary?month=2026-10", headers=bearer(new["token"])).json()["expenses"] == 500
    assert client.get("/api/v1/summary", headers=bearer(acc["token"])).status_code == 401
    assert client.get("/api/v1/summary", headers=bearer(code)).status_code == 401
    # sonraki girişte LINE defteri açılır
    r = client.post("/api/v1/auth/login", json={"email": "taro@example.jp", "password": PW})
    assert r.json()["user_id"] == "Uline1"


def test_link_line_invalid_code(client):
    acc = signup(client).json()
    r = client.post("/api/v1/auth/link-line", json={"code": "tk_nope"}, headers=bearer(acc["token"]))
    assert r.status_code == 400
    assert client.post("/api/v1/auth/link-line", json={"code": "tk_nope"}).status_code == 401


def test_link_line_requires_account(bot, client):
    # Hesapsız (yalnızca LINE kodu) oturum bağlama yapamaz
    r = client.post("/api/v1/auth/link-line", json={"code": line_code(bot, "U2")},
                    headers=bearer(line_code(bot, "U3")))
    assert r.status_code == 403


def test_link_line_refuses_when_web_ledger_has_data(bot, client):
    acc = signup(client).json()
    assert add_entry(client, acc["token"]).status_code == 201
    r = client.post("/api/v1/auth/link-line", json={"code": line_code(bot)}, headers=bearer(acc["token"]))
    assert r.status_code == 409
    # hiçbir şey değişmedi
    assert client.get("/api/v1/summary", headers=bearer(acc["token"])).status_code == 200


def test_link_line_refuses_ledger_of_other_account(bot, client):
    a = signup(client, "a@example.jp").json()
    b = signup(client, "b@example.jp").json()
    assert client.post("/api/v1/auth/link-line", json={"code": line_code(bot)}, headers=bearer(a["token"])).status_code == 200
    r = client.post("/api/v1/auth/link-line", json={"code": line_code(bot)}, headers=bearer(b["token"]))
    assert r.status_code == 409


# ------------------------------------------------------------ parola sıfırlama
def test_password_reset_flow(client, caplog):
    import accounts
    signup(client)
    # bilinmeyen e-posta da aynı yanıtı alır
    assert client.post("/api/v1/auth/password-reset/request", json={"email": "x@example.jp"}).status_code == 202
    token = accounts.request_password_reset("taro@example.jp")
    assert token and token.startswith("rs_")
    old = client.post("/api/v1/auth/login", json={"email": "taro@example.jp", "password": PW}).json()["token"]
    assert client.post("/api/v1/auth/password-reset/confirm",
                       json={"token": token, "password": "short"}).status_code == 400
    r = client.post("/api/v1/auth/password-reset/confirm", json={"token": token, "password": "new-password-99"})
    assert r.status_code == 200
    # eski oturumlar kapandı, eski parola geçmez, yeni parola geçer, token tek kullanımlık
    assert client.get("/api/v1/summary", headers=bearer(old)).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "taro@example.jp", "password": PW}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "taro@example.jp",
                                                   "password": "new-password-99"}).status_code == 200
    assert client.post("/api/v1/auth/password-reset/confirm",
                       json={"token": token, "password": "another-pass-1"}).status_code == 400


def test_password_reset_expired(client, monkeypatch):
    import accounts
    signup(client)
    token = accounts.request_password_reset("taro@example.jp")
    monkeypatch.setattr(accounts, "datetime", type("D", (), {
        "now": staticmethod(lambda tz=None: datetime.now(tz) + timedelta(hours=1, seconds=1)),
        "fromisoformat": staticmethod(datetime.fromisoformat)}))
    r = client.post("/api/v1/auth/password-reset/confirm", json={"token": token, "password": "new-password-99"})
    assert r.status_code == 400


def test_reset_mail_logged_without_provider(client, caplog, monkeypatch):
    import accounts
    monkeypatch.delenv("MAIL_PROVIDER", raising=False)
    signup(client)
    with caplog.at_level("INFO", logger="accounts"):
        accounts.request_password_reset("taro@example.jp")
    assert "MAIL_PROVIDER not set" in caplog.text
