"""T-052: Stripe webhook olay sırası — eski (geç gelen) olay yeni durumu ezmez."""
import json

import pytest
from fastapi.testclient import TestClient

WH = "whsec_test"


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def stripe_on(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WH)
    monkeypatch.setenv("STRIPE_PRICE_PERSONAL", "price_personal")
    monkeypatch.setenv("STRIPE_PRICE_BUSINESS", "price_business")
    monkeypatch.delenv("BILLING_ENFORCE_LIMITS", raising=False)


def webhook(client, event):
    import billing
    body = json.dumps(event).encode()
    r = client.post("/api/v1/billing/webhook", content=body,
                    headers={"Stripe-Signature": billing.sign(body, WH), "Content-Type": "application/json"})
    assert r.status_code == 200, r.text
    return r.json()["result"]


def sub_ev(eid, created, uid="U-ord", etype="customer.subscription.updated", status="active",
           price="price_personal", cancel_at_period_end=False):
    return {"id": eid, "type": etype, "created": created, "data": {"object": {
        "id": "sub_" + uid, "object": "subscription", "customer": "cus_1", "status": status,
        "cancel_at_period_end": cancel_at_period_end, "current_period_end": 1798729200,
        "metadata": {"user_id": uid}, "items": {"data": [{"price": {"id": price}}]}}}}


def checkout_ev(eid, created, uid="U-ord"):
    return {"id": eid, "type": "checkout.session.completed", "created": created, "data": {"object": {
        "mode": "subscription", "client_reference_id": uid, "metadata": {"plan": "personal"},
        "payment_status": "paid", "customer": "cus_1", "subscription": "sub_" + uid}}}


def test_late_updated_after_deleted_is_ignored(client, stripe_on):
    import billing
    assert webhook(client, sub_ev("e1", 50)) == "ok"
    assert billing.current_plan("U-ord") == "personal"
    assert webhook(client, sub_ev("e2", 200, etype="customer.subscription.deleted", status="canceled")) == "ok"
    assert billing.current_plan("U-ord") == "free"
    # Stripe'ın yeniden denediği eski 'updated' (active) geç gelir
    assert webhook(client, sub_ev("e3", 100)) == "ignored"
    assert billing.current_plan("U-ord") == "free"
    assert billing.get_subscription("U-ord")["status"] == "canceled"


@pytest.mark.parametrize("created,result,plan", [(199, "ignored", "free"), (200, "ok", "personal"),
                                                 (201, "ok", "personal")])
def test_event_time_boundary(client, stripe_on, created, result, plan):
    import billing
    webhook(client, sub_ev("d1", 200, etype="customer.subscription.deleted", status="canceled"))
    assert webhook(client, sub_ev("u1", created)) == result
    assert billing.current_plan("U-ord") == plan


def test_late_checkout_completed_after_deleted_is_ignored(client, stripe_on):
    import billing
    webhook(client, sub_ev("d1", 300, etype="customer.subscription.deleted", status="canceled"))
    assert webhook(client, checkout_ev("c1", 250)) == "ignored"
    assert billing.current_plan("U-ord") == "free"


def test_checkout_then_newer_subscription_update_applies(client, stripe_on):
    import billing
    assert webhook(client, checkout_ev("c1", 100)) == "ok"
    assert billing.current_plan("U-ord") == "personal"
    assert webhook(client, sub_ev("u1", 150, cancel_at_period_end=True)) == "ok"
    assert billing.get_subscription("U-ord")["cancel_at_period_end"] == 1
    assert billing.get_subscription("U-ord")["last_event_created"] == 150


def test_older_event_does_not_lower_stored_time(client, stripe_on):
    import billing
    webhook(client, sub_ev("u1", 500))
    webhook(client, sub_ev("u0", 400, status="past_due"))
    sub = billing.get_subscription("U-ord")
    assert sub["status"] == "active" and sub["last_event_created"] == 500


@pytest.mark.parametrize("raw,expected", [(None, 0), ("abc", 0), (-5, 0), ("123", 123), (1798729200, 1798729200)])
def test_event_created_parsing(raw, expected):
    import billing
    assert billing._event_created({"created": raw}) == expected


def test_api_write_keeps_event_time(client, stripe_on):
    """cancel() gibi API yanıtı yazımları zaman damgasını değiştirmez; sonraki yeni olay uygulanır."""
    import billing
    webhook(client, sub_ev("u1", 100))
    obj = sub_ev("x", 0, cancel_at_period_end=True)["data"]["object"]
    assert billing._apply_subscription_object(obj) == "U-ord"
    sub = billing.get_subscription("U-ord")
    assert sub["cancel_at_period_end"] == 1 and sub["last_event_created"] == 100
    assert webhook(client, sub_ev("u2", 101)) == "ok"
    assert billing.get_subscription("U-ord")["cancel_at_period_end"] == 0


def test_existing_db_without_column_is_migrated(tmp_path, monkeypatch):
    """T-052 öncesi oluşturulmuş subscriptions tablosuna sütun eklenir, veri korunur."""
    import os
    if os.environ.get("DATABASE_URL"):
        pytest.skip("SQLite'a özgü (PostgreSQL'de ADD COLUMN IF NOT EXISTS)")
    import sqlite3
    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE subscriptions(user_id TEXT PRIMARY KEY, plan TEXT NOT NULL DEFAULT 'free',
        status TEXT NOT NULL DEFAULT 'incomplete', stripe_customer TEXT DEFAULT '', stripe_subscription TEXT DEFAULT '',
        current_period_end TEXT DEFAULT '', cancel_at_period_end INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)""")
    con.execute("INSERT INTO subscriptions(user_id,plan,status,updated_at) VALUES('U-old','personal','active','x')")
    con.commit()
    con.close()
    monkeypatch.setenv("DB_PATH", str(db))
    import store
    store.init_db()
    store.init_db()  # ikinci çalıştırma da hatasız
    with store.tx() as c:
        row = dict(c.execute("SELECT * FROM subscriptions WHERE user_id='U-old'").fetchone())
    assert row["plan"] == "personal" and row["last_event_created"] == 0
