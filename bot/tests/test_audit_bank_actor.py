"""T-065b: geçmişte 'kim yaptı' (actor → üye e-postası) ve bank_tx düzeltme/durum geçmişi."""
import pytest
from fastapi.testclient import TestClient

PW = "correct-horse-1"
ENTRY = {"date": "2026-10-05", "kind": "exp", "store": "コンビニ", "amount": 1100, "category": "消耗品費", "rate": 10}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def signup(client, email):
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": PW})
    assert r.status_code == 201, r.text
    return r.json()


def join(client, owner_tok, member_tok, role):
    code = client.post("/api/v1/team/invites", headers=H(owner_tok), json={"role": role}).json()["code"]
    r = client.post("/api/v1/team/join", headers=H(member_tok), json={"code": code})
    assert r.status_code == 201, r.text
    return r.json()["token"]


@pytest.fixture()
def team(client):
    owner, acc, view = signup(client, "owner@example.jp"), signup(client, "acc@example.jp"), signup(client, "view@example.jp")
    return {"owner": owner["token"], "acc": join(client, owner["token"], acc["token"], "accountant"),
            "view": join(client, owner["token"], view["token"], "viewer"), "uid": owner["user_id"]}


def _history(client, tok, eid):
    r = client.get(f"/api/v1/entries/{eid}/history", headers=H(tok))
    assert r.status_code == 200, r.text
    return r.json()


def test_actor_email_visible_to_owner_and_self_only(client, team):
    eid = client.post("/api/v1/entries", headers=H(team["owner"]), json=ENTRY).json()["id"]
    assert client.patch(f"/api/v1/entries/{eid}", headers=H(team["acc"]), json={"amount": 1210}).status_code == 200

    by_owner = _history(client, team["owner"], eid)
    assert [(x["action"], x["actor_kind"], x["actor_role"]) for x in by_owner] == [
        ("create", "web", "owner"), ("update", "web", "accountant")]
    assert by_owner[0]["actor_email"] == "owner@example.jp" and by_owner[0]["actor_is_me"]
    assert by_owner[1]["actor_email"] == "acc@example.jp" and not by_owner[1]["actor_is_me"]

    by_acc = _history(client, team["acc"], eid)
    assert by_acc[0]["actor_email"] is None                     # sahibin e-postası üyeye açılmaz
    assert by_acc[1]["actor_email"] == "acc@example.jp" and by_acc[1]["actor_is_me"]

    by_view = _history(client, team["view"], eid)               # viewer okur ama e-posta görmez
    assert [x["actor_email"] for x in by_view] == [None, None]
    assert not any(x["actor_former"] for x in by_view)


def test_removed_member_shown_as_former(client, team):
    eid = client.post("/api/v1/entries", headers=H(team["acc"]), json=ENTRY).json()["id"]
    members = client.get("/api/v1/team/members", headers=H(team["owner"])).json()["members"]
    acc_id = next(m["account_id"] for m in members if m["email"] == "acc@example.jp")
    assert client.delete(f"/api/v1/team/members/{acc_id}", headers=H(team["owner"])).status_code == 204
    row = _history(client, team["owner"], eid)[0]
    assert row["actor_former"] and row["actor_email"] is None and row["actor_role"] == "accountant"


def test_line_actor_kind(client, bot):
    import store
    eid = store.add_entry("L1", {**ENTRY, "date": ENTRY["date"]}, source="LINE")
    tok = store.issue_token("L1", "test")
    row = _history(client, tok, eid)[0]
    assert row["actor_kind"] == "line" and row["actor_email"] is None and row["actor_role"] == ""


def _bank_rows(uid):
    import store
    store.insert_bank_rows(uid, [
        {"d": "2026-10-01", "description": "ﾃﾞﾝﾘｮｸ", "amount": -5500, "balance": 94500},
        {"d": "2026-10-02", "description": "ATM", "amount": -10000, "balance": 84500},
    ])
    return {t["description"]: t["id"] for t in store.list_bank_tx(uid)}


def test_bank_fix_and_confirm_are_audited(client, team):
    ids = _bank_rows(team["uid"])
    tid = ids["ﾃﾞﾝﾘｮｸ"]
    assert client.get(f"/api/v1/bank/{tid}/history", headers=H(team["owner"])).json() == []

    r = client.patch(f"/api/v1/bank/{tid}", headers=H(team["acc"]), json={"amount": -5600})
    assert r.status_code == 200 and r.json()["amount"] == -5600
    r = client.post(f"/api/v1/bank/{tid}/confirm", headers=H(team["owner"]), json={"book": True, "category": "水道光熱費"})
    assert r.status_code == 200, r.text
    entry_id = r.json()["entry_id"]

    h = client.get(f"/api/v1/bank/{tid}/history", headers=H(team["owner"])).json()
    assert [(x["action"], x["actor_role"]) for x in h] == [("update", "accountant"), ("update", "owner")]
    assert h[0]["changed"] == ["amount"] and h[0]["before"]["amount"] == -5500 and h[0]["after"]["amount"] == -5600
    assert {"status", "category", "entry_id"} <= set(h[1]["changed"]) and h[1]["after"]["status"] == "confirmed"
    assert h[0]["actor_email"] == "acc@example.jp"

    # Banka hareketinden oluşan kayıt artık kimin onayladığını taşır (BANK değil WEB:owner)
    assert _history(client, team["owner"], entry_id)[0]["actor_role"] == "owner"

    # Kaydı silmek bank_tx bağını çözer → bank_tx geçmişine de yazılır
    assert client.delete(f"/api/v1/entries/{entry_id}", headers=H(team["owner"])).status_code == 204
    h = client.get(f"/api/v1/bank/{tid}/history", headers=H(team["owner"])).json()
    assert h[-1]["changed"] == ["entry_id"] and h[-1]["after"]["entry_id"] is None

    excl = client.post(f"/api/v1/bank/{ids['ATM']}/confirm", headers=H(team["owner"]), json={"book": False})
    assert excl.status_code == 200 and excl.json()["status"] == "excluded"
    recent = client.get("/api/v1/audit?entity=bank_tx", headers=H(team["owner"])).json()
    assert recent[0]["entity_id"] == str(ids["ATM"]) and recent[0]["after"]["status"] == "excluded"


def test_bank_to_entry_audits_link(client, team):
    tid = _bank_rows(team["uid"])["ﾃﾞﾝﾘｮｸ"]
    r = client.post(f"/api/v1/bank/{tid}/entry", headers=H(team["acc"]), json={"category": "水道光熱費"})
    assert r.status_code == 201, r.text
    h = client.get(f"/api/v1/bank/{tid}/history", headers=H(team["owner"])).json()
    assert len(h) == 1 and h[0]["changed"] == ["entry_id"] and h[0]["actor_role"] == "accountant"


def test_bank_history_scoped_to_ledger(client, team):
    tid = _bank_rows(team["uid"])["ATM"]
    other = signup(client, "other@example.jp")
    assert client.get(f"/api/v1/bank/{tid}/history", headers=H(other["token"])).status_code == 404
    assert client.get("/api/v1/bank/999999/history", headers=H(team["owner"])).status_code == 404
    # viewer okur ama düzeltemez
    assert client.get(f"/api/v1/bank/{tid}/history", headers=H(team["view"])).status_code == 200
    assert client.patch(f"/api/v1/bank/{tid}", headers=H(team["view"]), json={"amount": -1}).status_code == 403
