"""T-081: 申告前チェックリスト。"""
import pytest
from fastapi.testclient import TestClient

from tax import precheck as pc


def test_invoice_gaps():
    assert pc.invoice_gaps(["INV-2026-0001", "INV-2026-0002", "INV-2026-0005"]) == ["INV-2026-0003", "INV-2026-0004"]
    assert pc.invoice_gaps(["INV-2026-0001", "INV-2026-0002"]) == []
    assert pc.invoice_gaps([]) == [] and pc.invoice_gaps(["abc"]) == []
    assert pc.invoice_gaps(["A-01", "A-03", "B-07"]) == ["A-02"]


def kw(**o):
    base = dict(year=2026, entries=[], invoices=[], bank=[], profile={"business_name": "X", "registration_no": "T1"},
                transitional_over=[], apportioned={}, asset_warnings=[], unverified_keys=[], params_available=True)
    base.update(o)
    return base


def keys(items):
    return [i.key for i in items]


def test_clean_book_has_all_clear_and_disclaimer():
    e = [{"kind": "inc", "rate": 10, "category": "売上高", "invoice_no": ""},
         {"kind": "exp", "rate": 10, "category": "消耗品費", "invoice_no": "T1"}]
    k = keys(pc.run(**kw(entries=e)))
    assert k == ["all_clear", "disclaimer"]


def test_flags():
    e = [{"kind": "exp", "rate": 10, "category": "地代家賃", "invoice_no": ""}]
    inv = [{"no": "INV-2026-0001", "issued": "2026-02-01", "status": "unpaid"},
           {"no": "INV-2026-0003", "issued": "2026-03-01", "status": "paid"},
           {"no": "INV-2025-0009", "issued": "2025-12-01", "status": "unpaid"}]
    bank = [{"d": "2026-04-01", "invoice_no": "", "entry_id": None}, {"d": "2025-04-01", "invoice_no": "", "entry_id": None},
            {"d": "2026-04-02", "invoice_no": "X", "entry_id": None}]
    r = pc.run(**kw(entries=e, invoices=inv, bank=bank, profile={}, transitional_over=[1], asset_warnings=["A", "税理士・税務署に"],
                    unverified_keys=["a", "b"]))
    k = keys(r)
    for want in ("profile_name", "profile_reg", "no_income", "no_invoice_no", "transitional_cap", "invoice_gaps", "unpaid_invoices",
                 "bank_pending", "apportion_unset", "asset_warning", "unverified_params", "disclaimer"):
        assert want in k, want
    assert "all_clear" not in k
    by = {i.key: i for i in r}
    assert by["bank_pending"].count == 1 and by["unpaid_invoices"].count == 1 and by["invoice_gaps"].count == 1
    assert sum(i.key == "asset_warning" for i in r) == 1


def test_no_entries_and_params_missing():
    k = keys(pc.run(**kw(params_available=False)))
    assert "no_entries" in k and "params_missing" in k and "no_income" not in k


def test_apportion_set_silences():
    e = [{"kind": "exp", "rate": 10, "category": "通信費", "invoice_no": "T1"}]
    assert "apportion_unset" not in keys(pc.run(**kw(entries=e, apportioned={"通信費": 50})))


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def test_api(client):
    r0 = client.get("/api/v1/tax/precheck?year=2026")
    assert r0.status_code == 401
    t = client.post("/api/v1/admin/tokens", json={"user_id": "P1"}, headers={"X-Admin-Key": "test-admin"}).json()["token"]
    h = {"Authorization": f"Bearer {t}"}
    r = client.get("/api/v1/tax/precheck?year=2026", headers=h)
    assert r.status_code == 200
    j = r.json()
    assert j["warn_count"] >= 1 and j["items"][-1]["key"] == "disclaimer"
    assert {"no_entries", "profile_name"} <= {i["key"] for i in j["items"]}
    client.post("/api/v1/entries", headers=h, json={"date": "2026-05-10", "kind": "exp", "store": "店", "amount": 1100,
                                                      "category": "消耗品費", "rate": 10, "invoice_no": ""})
    j = client.get("/api/v1/tax/precheck?year=2026", headers=h).json()
    assert any(i["key"] == "no_invoice_no" and i["count"] == 1 for i in j["items"])
    assert client.get("/api/v1/tax/precheck?year=2019", headers=h).status_code == 422
