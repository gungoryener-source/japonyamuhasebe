"""T-046b hesap silme talebi: yalnızca owner, idempotent, veri silinmez, 解約 uyarısı bayrağı, admin listesi."""
import pytest
from fastapi.testclient import TestClient

PW = "correct-horse-1"
URL = "/api/v1/account/delete-request"
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


def test_requires_auth(client):
    assert client.post(URL).status_code == 401
    assert client.get(URL).status_code == 401


def test_owner_request_is_202_and_idempotent(client):
    owner = signup(client, "owner@example.jp")
    g = client.get(URL, headers=H(owner["token"])).json()
    assert g == {"request": None, "billing_active": False}
    r1 = client.post(URL, headers=H(owner["token"]))
    assert r1.status_code == 202
    b1 = r1.json()
    assert b1["created"] is True and b1["request"]["status"] == "pending" and b1["request"]["requested_at"]
    r2 = client.post(URL, headers=H(owner["token"]))
    assert r2.status_code == 202
    b2 = r2.json()
    assert b2["created"] is False and b2["request"] == b1["request"]
    assert client.get(URL, headers=H(owner["token"])).json()["request"] == b1["request"]
    import store
    with store.tx() as con:
        n = con.execute("SELECT COUNT(*) AS n FROM deletion_requests").fetchone()["n"]
    assert n == 1


def test_members_forbidden(client):
    owner = signup(client, "owner@example.jp")
    acc, view = signup(client, "acc@example.jp"), signup(client, "view@example.jp")
    acc_tok = join(client, owner["token"], acc["token"], "accountant")
    view_tok = join(client, owner["token"], view["token"], "viewer")
    for tok in (acc_tok, view_tok):
        assert client.post(URL, headers=H(tok)).status_code == 403
        assert client.get(URL, headers=H(tok)).status_code == 403
    assert client.get(URL, headers=H(owner["token"])).json()["request"] is None
    # Üye kendi defteri için talep edebilir (orada owner)
    assert client.post(URL, headers=H(acc["token"])).status_code == 202


def test_data_is_not_deleted_and_access_continues(client):
    owner = signup(client, "owner@example.jp")
    assert client.post("/api/v1/entries", headers=H(owner["token"]), json=ENTRY).status_code == 201
    assert client.post(URL, headers=H(owner["token"])).status_code == 202
    rows = client.get("/api/v1/entries", headers=H(owner["token"])).json()
    rows = rows["entries"] if isinstance(rows, dict) else rows
    assert len(rows) == 1


def test_line_only_owner_token(client, bot):
    import store
    tok = store.issue_token("U-line-only", "panel")
    r = client.post(URL, headers=H(tok))
    assert r.status_code == 202 and r.json()["created"] is True


def test_billing_active_flag(client, bot):
    import billing
    owner = signup(client, "owner@example.jp")
    uid = owner["user_id"]
    billing._upsert(uid, plan="personal", status="active", stripe_subscription="sub_1")
    assert client.get(URL, headers=H(owner["token"])).json()["billing_active"] is True
    # 解約予約済み → もう更新されない
    billing._upsert(uid, cancel_at_period_end=1)
    assert client.get(URL, headers=H(owner["token"])).json()["billing_active"] is False
    billing._upsert(uid, cancel_at_period_end=0, status="canceled")
    assert client.get(URL, headers=H(owner["token"])).json()["billing_active"] is False


def test_cancelled_request_can_be_renewed(client, bot):
    import store
    owner = signup(client, "owner@example.jp")
    client.post(URL, headers=H(owner["token"]))
    with store.tx() as con:
        con.execute("UPDATE deletion_requests SET status='cancelled' WHERE user_id=?", (owner["user_id"],))
    r = client.post(URL, headers=H(owner["token"])).json()
    assert r["created"] is True and r["request"]["status"] == "pending"


def test_admin_list(client):
    owner = signup(client, "owner@example.jp")
    client.post(URL, headers=H(owner["token"]))
    assert client.get("/api/v1/admin/deletion-requests").status_code == 401
    assert client.get("/api/v1/admin/deletion-requests", headers={"X-Admin-Key": "wrong"}).status_code == 401
    r = client.get("/api/v1/admin/deletion-requests", headers={"X-Admin-Key": "test-admin"})
    assert r.status_code == 200
    reqs = r.json()["requests"]
    assert len(reqs) == 1 and reqs[0]["email"] == "owner@example.jp" and reqs[0]["user_id"] == owner["user_id"]
