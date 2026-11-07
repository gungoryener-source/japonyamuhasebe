"""Bir hesapta birden çok şirket: oluşturma, geçiş, veri ayrımı, LINE kayıt yeri, güvenlik."""
import pytest
from fastapi.testclient import TestClient

import companies
import store

ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def signup(client, email):
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": "Passw0rd!x"})
    assert r.status_code in (200, 201), r.text
    j = r.json()
    return {"Authorization": f"Bearer {j['token']}"}, j


def entry(client, h, store_name, amount=1100):
    body = {"date": "2026-11-01", "kind": "exp", "store": store_name, "amount": amount, "category": "消耗品費", "rate": 10, "invoice_no": ""}
    assert client.post("/api/v1/entries", json=body, headers=h).status_code == 201


def test_create_switch_and_isolation(client):
    h, _ = signup(client, "multi@example.com")
    entry(client, h, "本店の文具")
    r = client.post("/api/v1/companies", json={"business_name": "合同会社ツー"}, headers=h)
    assert r.status_code == 201
    c2 = r.json()
    h2 = {"Authorization": f"Bearer {c2['token']}"}
    assert c2["role"] == "owner" and c2["user_id"].startswith("web:")
    # 新しい事業所は空、データは分かれる
    assert client.get("/api/v1/entries", headers=h2).json() == []
    entry(client, h2, "支店の文具", 2200)
    assert [e["store"] for e in client.get("/api/v1/entries", headers=h).json()] == ["本店の文具"]
    assert client.get("/api/v1/profile", headers=h2).json()["business_name"] == "合同会社ツー"
    # 一覧と切替（3社目も）
    client.post("/api/v1/companies", json={"business_name": "株式会社スリー"}, headers=h2)
    led = client.get("/api/v1/team/ledgers", headers=h).json()["ledgers"]
    assert [l["role"] for l in led] == ["owner", "owner", "owner"]
    assert [l["business_name"] for l in led][1:] == ["合同会社ツー", "株式会社スリー"]
    sw = client.post("/api/v1/team/switch", json={"user_id": c2["user_id"]}, headers=h)
    assert sw.status_code == 200 and sw.json()["role"] == "owner"
    hs = {"Authorization": f"Bearer {sw.json()['token']}"}
    assert [e["store"] for e in client.get("/api/v1/entries", headers=hs).json()] == ["支店の文具"]
    # 追加した事業所ではオーナー権限（招待を作れる）
    assert client.post("/api/v1/team/invites", json={"role": "viewer"}, headers=hs).status_code in (200, 201)


def test_other_account_cannot_switch(client):
    h, _ = signup(client, "a1@example.com")
    c = client.post("/api/v1/companies", json={"business_name": "A社"}, headers=h).json()
    hb, _ = signup(client, "b1@example.com")
    assert client.post("/api/v1/team/switch", json={"user_id": c["user_id"]}, headers=hb).status_code == 403


def test_requires_account_and_limits(client, monkeypatch, bot):
    tok = client.post("/api/v1/admin/tokens", json={"user_id": "Uline"}, headers=ADMIN).json()["token"]
    hl = {"Authorization": f"Bearer {tok}"}
    assert client.post("/api/v1/companies", json={"business_name": "X"}, headers=hl).status_code == 403
    h, _ = signup(client, "lim@example.com")
    assert client.post("/api/v1/companies", json={"business_name": " "}, headers=h).status_code == 400
    monkeypatch.setenv("MAX_COMPANIES_PER_ACCOUNT", "2")
    assert client.post("/api/v1/companies", json={"business_name": "2社目"}, headers=h).status_code == 201
    assert client.post("/api/v1/companies", json={"business_name": "3社目"}, headers=h).status_code == 409


def test_extra_company_token_cannot_be_used_as_line_code(client):
    h, _ = signup(client, "link@example.com")
    c = client.post("/api/v1/companies", json={"business_name": "B社"}, headers=h).json()
    r = client.post("/api/v1/auth/link-line", json={"code": c["token"]}, headers=h)
    assert r.status_code == 409


def test_line_target_selection(bot, client):
    # LINE の帳簿 Uline2 をアカウントに連携した状態を作る
    h, acc = signup(client, "line@example.com")
    with store.tx() as con:
        con.execute("UPDATE account_ledgers SET user_id=? WHERE account_id=?", ("Uline2", acc["account"]["id"] if "account" in acc else acc["id"]))
    tok = store.issue_token("Uline2", "web-login")
    hl = {"Authorization": f"Bearer {tok}"}
    client.post("/api/v1/companies", json={"business_name": "合同会社ツー"}, headers=hl)
    msg, opts = bot.respond("Uline2", "会社")
    assert "記録先の事業所を選んでください" in msg and "2. 合同会社ツー" in msg and [s for _, s in opts] == ["会社:1", "会社:2"]
    msg, _ = bot.respond("Uline2", "会社:2")
    assert "合同会社ツー" in msg
    msg, _ = bot.respond("Uline2", "タクシー 2300")
    assert msg.startswith("［合同会社ツー］") and "登録しました" in msg
    target = companies.line_target("Uline2")
    assert target.startswith("web:")
    assert [e["store"] for e in store.search_entries(target)] == ["タクシー"]
    assert store.search_entries("Uline2") == []
    msg, _ = bot.respond("Uline2", "会社:9")
    assert "ありません" in msg
    bot.respond("Uline2", "会社:1")
    msg, _ = bot.respond("Uline2", "タクシー 1000")
    assert not msg.startswith("［") and len(store.search_entries("Uline2")) == 1
    bot.respond("Uline2", "Türkçe")
    msg, _ = bot.respond("Uline2", "şirket")
    assert "Kayıtların gideceği şirketi seçin" in msg


def test_line_without_account_has_single_company(bot):
    msg, _ = bot.respond("Ulonely", "会社")
    assert "事業所は1つです" in msg
    assert companies.line_target("Ulonely") == "Ulonely"
