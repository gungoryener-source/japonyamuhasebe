"""T-076: 家事按分（事業割合）。"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def tok(client, uid):
    r = client.post("/api/v1/admin/tokens", json={"user_id": uid}, headers={"X-Admin-Key": "test-admin"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def exp(client, h, amount, cat="地代家賃", rate=10, inv="T1234567890123"):
    r = client.post("/api/v1/entries", headers=h, json={"date": "2026-05-10", "kind": "exp", "store": "店", "amount": amount,
                                                          "category": cat, "rate": rate, "invoice_no": inv})
    assert r.status_code == 201, r.text


def pl(client, h):
    return client.get("/api/v1/pl?year=2026", headers=h).json()


def put(client, h, items):
    return client.put("/api/v1/settings/apportionment", headers=h, json={"items": items})


def test_default_unchanged_and_defaults_listed(client):
    h = tok(client, "A1")
    exp(client, h, 100_000)
    assert pl(client, h)["expenses_total"] == 100_000
    items = client.get("/api/v1/settings/apportionment", headers=h).json()["items"]
    assert {"category": "地代家賃", "pct": 100} in items


@pytest.mark.parametrize("pct,expected", [(0, 0), (100, 100_000), (33, 33_000), (50, 50_000)])
def test_pl_ratio(client, pct, expected):
    h = tok(client, "A2")
    exp(client, h, 100_000)
    assert put(client, h, [{"category": "地代家賃", "pct": pct}]).status_code == 200
    assert pl(client, h)["expenses_total"] == expected


def test_pl_floors_once_on_category_total(client):
    h = tok(client, "A3")
    for a in (101, 101, 101):
        exp(client, h, a)
    put(client, h, [{"category": "地代家賃", "pct": 33}])
    assert pl(client, h)["expenses_total"] == 303 * 33 // 100        # 99


def test_other_categories_untouched_and_raw_entries_unchanged(client):
    h = tok(client, "A4")
    exp(client, h, 100_000)
    exp(client, h, 30_000, cat="通信費")
    put(client, h, [{"category": "地代家賃", "pct": 40}])
    assert pl(client, h)["expenses_total"] == 40_000 + 30_000
    assert sorted(e["amount"] for e in client.get("/api/v1/entries", headers=h).json()) == [30_000, 100_000]


def test_consumption_honsoku_input_tax_uses_business_part(client):
    h = tok(client, "A5")
    exp(client, h, 110_000)
    base = client.get("/api/v1/tax/consumption?year=2026&method=honsoku", headers=h).json()["input_tax"]
    put(client, h, [{"category": "地代家賃", "pct": 50}])
    half = client.get("/api/v1/tax/consumption?year=2026&method=honsoku", headers=h).json()["input_tax"]
    ret = client.get("/api/v1/tax/consumption/return?year=2026&method=honsoku", headers=h)
    assert base == 10_000 and half == 5_000 and ret.status_code == 200


def test_validation_and_permissions(client):
    h = tok(client, "A6")
    assert put(client, h, [{"category": "売上高", "pct": 50}]).status_code == 400
    assert put(client, h, [{"category": "地代家賃", "pct": 101}]).status_code == 400
    assert put(client, h, [{"category": "地代家賃", "pct": -1}]).status_code == 400
    assert put(client, h, [{"category": "地代家賃", "pct": True}]).status_code == 400
    assert client.put("/api/v1/settings/apportionment", json={"items": []}).status_code == 401


def test_isolated_per_user_and_reset(client):
    a, b = tok(client, "A7"), tok(client, "A8")
    exp(client, a, 100_000)
    exp(client, b, 100_000)
    put(client, a, [{"category": "地代家賃", "pct": 10}])
    assert pl(client, a)["expenses_total"] == 10_000 and pl(client, b)["expenses_total"] == 100_000
    put(client, a, [{"category": "地代家賃", "pct": 100}])
    assert pl(client, a)["expenses_total"] == 100_000
