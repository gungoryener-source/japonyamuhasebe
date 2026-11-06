"""T-029b: entries.amount int4 (PostgreSQL) taşması — 500 yerine 4xx / Japonca uyarı."""
import pytest
from fastapi.testclient import TestClient

import store
from store import MAX_ENTRY_AMOUNT

ADMIN = {"X-Admin-Key": "test-admin"}
INT4_MAX = 2**31 - 1


@pytest.fixture()
def api(bot):
    c = TestClient(bot.app)
    r = c.post("/api/v1/admin/tokens", json={"user_id": "L1"}, headers=ADMIN)
    return c, {"Authorization": f"Bearer {r.json()['token']}"}


def _entry(amount):
    return {"date": "2026-11-01", "kind": "exp", "store": "テスト商店", "amount": amount, "category": "消耗品費", "rate": 10}


def test_limit_fits_int4_and_invoice_totals():
    from invoices import MAX_AMOUNT
    assert MAX_ENTRY_AMOUNT - 1 <= INT4_MAX
    # en büyük fatura (税抜 < 1e9, 10%) ödendi → 売上 kaydı sınırın altında kalmalı
    assert (MAX_AMOUNT - 1) + (MAX_AMOUNT - 1) * 10 // 100 < MAX_ENTRY_AMOUNT


def test_store_check_amount_boundaries():
    assert store.check_amount(1) == 1
    assert store.check_amount(MAX_ENTRY_AMOUNT - 1) == MAX_ENTRY_AMOUNT - 1
    for bad in (0, -1, MAX_ENTRY_AMOUNT, 3_000_000_000):
        with pytest.raises(store.AmountOutOfRange):
            store.check_amount(bad)


def test_api_create_boundary(api):
    c, auth = api
    r = c.post("/api/v1/entries", json=_entry(MAX_ENTRY_AMOUNT - 1), headers=auth)
    assert r.status_code == 201
    assert c.get("/api/v1/entries", headers=auth).json()[0]["amount"] == MAX_ENTRY_AMOUNT - 1
    assert c.post("/api/v1/entries", json=_entry(MAX_ENTRY_AMOUNT), headers=auth).status_code == 422
    assert c.post("/api/v1/entries", json=_entry(3_000_000_000), headers=auth).status_code == 422


def test_api_patch_boundary(api):
    c, auth = api
    eid = c.post("/api/v1/entries", json=_entry(1000), headers=auth).json()["id"]
    assert c.patch(f"/api/v1/entries/{eid}", json={"amount": MAX_ENTRY_AMOUNT - 1}, headers=auth).status_code == 200
    assert c.patch(f"/api/v1/entries/{eid}", json={"amount": MAX_ENTRY_AMOUNT}, headers=auth).status_code == 422


def test_bank_withdrawal_too_large_is_400(api):
    c, auth = api
    store.insert_bank_rows("L1", [
        {"d": "2026-11-01", "description": "大口振込", "amount": -MAX_ENTRY_AMOUNT, "balance": None},
        {"d": "2026-11-02", "description": "通常振込", "amount": -(MAX_ENTRY_AMOUNT - 1), "balance": None},
    ])
    ids = {t["description"]: t["id"] for t in store.list_bank_tx("L1")}
    r = c.post(f"/api/v1/bank/{ids['大口振込']}/entry", json={"category": "支払手数料", "rate": 10}, headers=auth)
    assert r.status_code == 400
    r = c.post(f"/api/v1/bank/{ids['通常振込']}/entry", json={"category": "支払手数料", "rate": 10}, headers=auth)
    assert r.status_code == 201, r.text


def test_line_text_too_large_is_rejected(bot):
    msg, _ = bot.respond("L2", f"ビル {MAX_ENTRY_AMOUNT}")
    assert "20億円未満" in msg
    assert store.last_entry("L2") is None
    msg, _ = bot.respond("L2", f"ビル {MAX_ENTRY_AMOUNT - 1}")
    assert store.last_entry("L2")["amount"] == MAX_ENTRY_AMOUNT - 1


@pytest.mark.asyncio
async def test_line_image_too_large_is_rejected(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    async def fake_ocr(img):
        return [{**_entry(MAX_ENTRY_AMOUNT), "date": "2026-11-01"}]

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)
    msg, _ = await bot.process_image("L3", b"jpg", "m1", "LINE")
    assert "20億円未満" in msg
    assert store.last_entry("L3") is None
