"""T-029: fatura kalemi tutar üst sınırları — BIGINT taşması 500 değil 400 olmalı."""
import pytest
from fastapi.testclient import TestClient

import invoices as inv_mod
from invoices import MAX_AMOUNT, MAX_ITEMS, MAX_QTY

ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def api(bot):
    c = TestClient(bot.app)
    r = c.post("/api/v1/admin/tokens", json={"user_id": "U1"}, headers=ADMIN)
    return c, {"Authorization": f"Bearer {r.json()['token']}"}


def _post(api, items):
    c, auth = api
    return c.post("/api/v1/invoices", json={"client": "X社", "due": "2099-01-01", "items": items}, headers=auth)


def test_qty_boundary():
    assert inv_mod.validate_items([{"name": "a", "qty": MAX_QTY, "unit_price": 1}])[0]["amount"] == MAX_QTY
    with pytest.raises(ValueError):
        inv_mod.validate_items([{"name": "a", "qty": MAX_QTY + 1, "unit_price": 1}])


def test_unit_price_boundary():
    assert inv_mod.validate_items([{"name": "a", "unit_price": MAX_AMOUNT - 1}])[0]["amount"] == MAX_AMOUNT - 1
    with pytest.raises(ValueError):
        inv_mod.validate_items([{"name": "a", "unit_price": MAX_AMOUNT}])


def test_line_amount_boundary():
    # 1e5 × (1e4 − 1) < 1e9 → geçer; 1e5 × 1e4 = 1e9 → reddedilir
    assert inv_mod.validate_items([{"name": "a", "qty": 100_000, "unit_price": 9_999}])
    with pytest.raises(ValueError):
        inv_mod.validate_items([{"name": "a", "qty": 100_000, "unit_price": 10_000}])


def test_subtotal_boundary():
    half = MAX_AMOUNT // 2
    assert inv_mod.validate_items([{"name": "a", "unit_price": half}, {"name": "b", "unit_price": half - 1}])
    with pytest.raises(ValueError):
        inv_mod.validate_items([{"name": "a", "unit_price": half}, {"name": "b", "unit_price": half}])


def test_item_count_boundary():
    assert len(inv_mod.validate_items([{"name": "a", "unit_price": 1}] * MAX_ITEMS)) == MAX_ITEMS
    with pytest.raises(ValueError):
        inv_mod.validate_items([{"name": "a", "unit_price": 1}] * (MAX_ITEMS + 1))


def test_max_invoice_total_fits_and_tax_is_floor(api):
    r = _post(api, [{"name": "大型案件", "unit_price": MAX_AMOUNT - 1, "rate": 10}])
    assert r.status_code == 201
    inv = r.json()
    assert inv["subtotal10"] == MAX_AMOUNT - 1
    assert inv["tax10"] == (MAX_AMOUNT - 1) * 10 // 100
    assert inv["total"] == inv["subtotal10"] + inv["tax10"] < 2**31  # PostgreSQL int4 sütunu


def test_max_invoice_total_reduced_rate(api):
    r = _post(api, [{"name": "a", "unit_price": MAX_AMOUNT // 2, "rate": 10},
                    {"name": "b", "unit_price": MAX_AMOUNT // 2 - 1, "rate": 8}])
    assert r.status_code == 201
    assert r.json()["total"] < 2**31


@pytest.mark.parametrize("items", [
    [{"name": "a", "qty": 10**12, "unit_price": 1}],
    [{"name": "a", "unit_price": 10**19}],
    [{"name": "a", "qty": 10**6, "unit_price": 10**4}],
    [{"name": "a", "unit_price": 3 * 10**9}],
    [{"name": "a", "unit_price": 6 * 10**8}, {"name": "b", "unit_price": 6 * 10**8, "rate": 8}],
    [{"name": "a", "unit_price": 1}] * (MAX_ITEMS + 1),
])
def test_api_rejects_oversized_with_400(api, items):
    assert _post(api, items).status_code == 400
