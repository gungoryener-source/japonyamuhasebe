import csv
import io

import pytest
from fastapi.testclient import TestClient

ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "U1"}, headers=ADMIN)
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['token']}"}


def entry(client, auth, **kw):
    body = {"date": "2026-10-05", "kind": "exp", "store": "JR東日本", "amount": 11000,
            "category": "旅費交通費", "rate": 10, "invoice_no": "T7011001666666"}
    body.update(kw)
    return client.post("/api/v1/entries", json=body, headers=auth)


def test_requires_token(client):
    assert client.get("/api/v1/summary").status_code == 401
    assert client.get("/api/v1/summary", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_admin_token_requires_key(client):
    assert client.post("/api/v1/admin/tokens", json={"user_id": "U1"}).status_code == 401


def test_entry_validation(client, auth):
    assert entry(client, auth).status_code == 201
    assert entry(client, auth, rate=5).status_code == 400
    assert entry(client, auth, category="謎").status_code == 400
    assert entry(client, auth, invoice_no="T123").status_code == 400
    assert entry(client, auth, date="2026-13-01").status_code == 400
    assert entry(client, auth, amount=0).status_code == 422


def test_summary_and_cashflow(client, auth):
    entry(client, auth, date="2026-09-10", kind="inc", store="A社", amount=1_000_000, category="売上高", invoice_no="")
    entry(client, auth, date="2026-10-10", kind="inc", store="A社", amount=1_200_000, category="売上高", invoice_no="")
    entry(client, auth, date="2026-10-11", amount=200_000, invoice_no="")
    s = client.get("/api/v1/summary?month=2026-10", headers=auth).json()
    assert s["revenue"] == 1_200_000 and s["expenses"] == 200_000 and s["profit"] == 1_000_000
    assert s["revenue_change_pct"] == 20.0 and s["expenses_change_pct"] is None
    assert s["expenses_without_invoice_no"] == 1
    cf = client.get("/api/v1/cashflow?months=3&end=2026-10", headers=auth).json()
    assert [c["month"] for c in cf] == ["2026-08", "2026-09", "2026-10"]
    assert cf[2]["net"] == 1_000_000
    assert client.get("/api/v1/summary?month=2026-1", headers=auth).status_code == 400


def test_users_isolated(client, auth):
    entry(client, auth)
    other = client.post("/api/v1/admin/tokens", json={"user_id": "U2"}, headers=ADMIN).json()["token"]
    rows = client.get("/api/v1/entries", headers={"Authorization": f"Bearer {other}"}).json()
    assert rows == []


def test_entries_search(client, auth):
    entry(client, auth, store="JR東日本", amount=11000, date="2026-10-01")
    entry(client, auth, store="ローソン", amount=540, rate=8, date="2026-10-02")
    entry(client, auth, store="100%_shop", amount=999, date="2026-10-03")
    q = lambda p: client.get("/api/v1/entries" + p, headers=auth).json()  # noqa: E731
    assert [r["store"] for r in q("?q=ローソン")] == ["ローソン"]
    assert len(q("?amount_min=1000")) == 1
    assert len(q("?date_from=2026-10-02&date_to=2026-10-02")) == 1
    assert [r["store"] for r in q("?q=%25")] == ["100%_shop"]   # LIKE wildcard escaped
    assert len(q("?q=_")) == 1


def test_consumption_tax_endpoint(client, auth):
    entry(client, auth, date="2026-10-10", kind="inc", store="A社", amount=1_100_000, category="売上高", invoice_no="")
    entry(client, auth, date="2026-10-15", amount=110_000, invoice_no="")                # 10,000 × 70%
    entry(client, auth, date="2026-10-15", amount=330_000)                               # 30,000
    r = client.get("/api/v1/tax/consumption?year=2026", headers=auth).json()
    assert r["output_tax"] == 100_000 and r["input_tax"] == 37_000 and r["payable"] == 63_000
    assert r["unqualified"] == [{"ratio": 70, "gross": 110_000, "tax": 10_000, "credited": 7_000}]
    n = client.get("/api/v1/tax/consumption?year=2026&method=niwari", headers=auth).json()
    assert n["payable"] == 20_000
    assert client.get("/api/v1/tax/consumption?year=2027&method=niwari", headers=auth).status_code == 400


def test_invoice_flow(client, auth):
    client.put("/api/v1/profile", json={"business_name": "合同会社ミナト", "registration_no": "T3010001222222"}, headers=auth)
    body = {"client": "株式会社サクラ", "issued": "2026-11-01", "due": "2026-11-30",
            "items": [{"name": "保守", "qty": 1, "unit_price": 100_000, "rate": 10},
                      {"name": "弁当", "qty": 3, "unit_price": 1_001, "rate": 8}]}
    r = client.post("/api/v1/invoices", json=body, headers=auth)
    assert r.status_code == 201
    inv = r.json()
    assert inv["no"] == "INV-2026-0001"
    assert (inv["subtotal10"], inv["tax10"], inv["subtotal8"], inv["tax8"]) == (100_000, 10_000, 3_003, 240)
    assert inv["total"] == 113_243
    assert client.post("/api/v1/invoices", json=body, headers=auth).json()["no"] == "INV-2026-0002"
    pdf = client.get("/api/v1/invoices/INV-2026-0001/pdf", headers=auth)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    paid = client.post("/api/v1/invoices/INV-2026-0001/paid?paid_on=2026-11-20", headers=auth).json()
    assert paid["status"] == "paid"
    inc = client.get("/api/v1/entries?kind=inc", headers=auth).json()
    assert sorted((e["rate"], e["amount"]) for e in inc) == [(8, 3_243), (10, 110_000)]
    # 二重消込しない
    client.post("/api/v1/invoices/INV-2026-0001/paid", headers=auth)
    assert len(client.get("/api/v1/entries?kind=inc", headers=auth).json()) == 2
    assert client.get("/api/v1/invoices/NOPE/pdf", headers=auth).status_code == 404


def test_invoice_validation(client, auth):
    bad = {"client": "X", "issued": "2026-11-10", "due": "2026-11-01", "items": [{"name": "a", "unit_price": 1}]}
    assert client.post("/api/v1/invoices", json=bad, headers=auth).status_code == 400
    bad2 = {"client": "X", "due": "2099-01-01", "items": [{"name": "a", "unit_price": 1, "rate": 5}]}
    assert client.post("/api/v1/invoices", json=bad2, headers=auth).status_code == 400
    bad3 = {"client": "X", "due": "2099-01-01", "items": []}
    assert client.post("/api/v1/invoices", json=bad3, headers=auth).status_code == 400


@pytest.mark.parametrize("fmt", ["freee", "mf", "yayoi"])
def test_export_csv(client, auth, fmt):
    entry(client, auth, date="2026-10-15", invoice_no="")
    entry(client, auth, date="2026-10-16", kind="inc", store="A社", amount=5500, category="売上高", invoice_no="")
    r = client.get(f"/api/v1/export.csv?format={fmt}&year=2026", headers=auth)
    assert r.status_code == 200
    rows = list(csv.reader(io.StringIO(r.content.decode("cp932"))))
    assert len(rows) == 3
    assert any("A社" in c for c in rows[2])
    if fmt == "freee":
        assert rows[1][4] == "課対仕入10%（控70）"


def test_export_bad_format(client, auth):
    assert client.get("/api/v1/export.csv?format=xls&year=2026", headers=auth).status_code == 400


def test_demo_seed(client):
    r = client.post("/api/v1/admin/demo-seed", headers=ADMIN)
    tok = {"Authorization": f"Bearer {r.json()['token']}"}
    s = client.get("/api/v1/summary?month=2026-10", headers=tok).json()
    assert s["revenue"] == 4_250_000 and s["expenses"] == 1_820_000
    invs = client.get("/api/v1/invoices", headers=tok).json()
    assert len(invs) == 4 and sum(1 for i in invs if i["status"] == "paid") == 1


def test_token_revoke_and_limit(client, auth):
    import store
    assert client.delete("/api/v1/tokens/current", headers=auth).status_code == 204
    assert client.get("/api/v1/profile", headers=auth).status_code == 401
    toks = [store.issue_token("LIM") for _ in range(7)]
    assert store.user_for_token(toks[0]) is None and store.user_for_token(toks[1]) is None
    assert all(store.user_for_token(t) == "LIM" for t in toks[2:])


def test_pl_and_income_tax(client, auth):
    entry(client, auth, date="2025-03-01", kind="inc", store="A社", amount=8_000_000, category="売上高", invoice_no="")
    entry(client, auth, date="2025-04-01", amount=2_000_000, category="外注工賃")
    entry(client, auth, date="2025-05-01", amount=1_000_000, category="地代家賃")
    pl = client.get("/api/v1/pl?year=2025", headers=auth).json()
    assert pl["revenue"] == 8_000_000 and pl["expenses_total"] == 3_000_000
    assert pl["expenses"][0] == {"category": "外注工賃", "amount": 2_000_000}
    r = client.get("/api/v1/tax/income?year=2025&social_insurance=600000", headers=auth).json()
    assert r["taxable"] == 3_070_000 and r["total"] == 213_800
    assert client.get("/api/v1/tax/income?year=2026", headers=auth).status_code == 409
    assert client.get("/api/v1/tax/income?year=2025&blue=1", headers=auth).status_code == 400
