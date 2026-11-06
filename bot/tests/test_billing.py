"""T-042 abonelik: planlar, sınırlar (sınır değerleri), Stripe Checkout (mock), webhook imzası ve olay işleme."""
import json
import time

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
    monkeypatch.setenv("PANEL_URL", "https://panel.example")
    monkeypatch.delenv("BILLING_ENFORCE_LIMITS", raising=False)


@pytest.fixture()
def no_stripe(monkeypatch):
    for k in ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_PERSONAL", "STRIPE_PRICE_BUSINESS"):
        monkeypatch.delenv(k, raising=False)


def bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


def token(uid="U1"):
    import store
    return store.issue_token(uid, "t")


def add_exp(client, tok, i=0):
    return client.post("/api/v1/entries", headers=bearer(tok), json={
        "date": "2026-10-05", "kind": "exp", "store": f"店{i}", "amount": 1100, "category": "消耗品費", "rate": 10})


def add_inv(client, tok):
    return client.post("/api/v1/invoices", headers=bearer(tok), json={
        "client": "株式会社テスト", "due": "2099-12-31",
        "items": [{"name": "作業", "qty": 1, "unit_price": 10000, "rate": 10}]})


def webhook(client, event, secret=WH, ts=None):
    body = json.dumps(event).encode()
    import billing
    return client.post("/api/v1/billing/webhook", content=body,
                       headers={"Stripe-Signature": billing.sign(body, secret, ts), "Content-Type": "application/json"})


def sub_event(eid, uid="U1", status="active", price="price_personal", sub_id="sub_1", cancel=False, etype=None):
    return {"id": eid, "type": etype or "customer.subscription.updated", "data": {"object": {
        "id": sub_id, "object": "subscription", "customer": "cus_1", "status": status,
        "cancel_at_period_end": cancel, "current_period_end": 1798729200, "metadata": {"user_id": uid},
        "items": {"data": [{"price": {"id": price}}]}}}}


# ------------------------------------------------------------ planlar / ödeme kapalı
def test_plans_public_and_placeholder(client, no_stripe):
    r = client.get("/api/v1/billing/plans").json()
    ids = [p["id"] for p in r["plans"]]
    assert ids == ["free", "personal", "business"]
    assert r["payments_enabled"] is False
    free = r["plans"][0]
    assert free["receipts_per_month"] == 30 and free["invoices_per_month"] == 3 and free["placeholder"] is True
    assert [p["available"] for p in r["plans"]] == [True, False, False]


def test_payments_disabled_returns_503_and_limits_not_enforced(client, no_stripe):
    tok = token()
    assert client.post("/api/v1/billing/checkout", headers=bearer(tok), json={"plan": "personal"}).status_code == 503
    assert client.post("/api/v1/billing/cancel", headers=bearer(tok)).status_code == 503
    assert webhook(client, sub_event("evt_x")).status_code == 503
    for i in range(31):
        assert add_exp(client, tok, i).status_code == 201
    st = client.get("/api/v1/billing/status", headers=bearer(tok)).json()
    assert st["plan"] == "free" and st["limits_enforced"] is False and st["usage"]["receipts"] == 31


def test_status_requires_auth(client):
    assert client.get("/api/v1/billing/status").status_code == 401
    assert client.post("/api/v1/billing/checkout", json={"plan": "personal"}).status_code == 401


# ------------------------------------------------------------ sınırlar (sınır değerleri)
def test_free_receipt_limit_boundary(client, stripe_on):
    tok = token()
    for i in range(30):
        assert add_exp(client, tok, i).status_code == 201
    r = add_exp(client, tok, 30)
    assert r.status_code == 402 and "上限" in r.json()["detail"]
    # 売上 (inc) fiş sayılmaz, sınırdan etkilenmez
    r = client.post("/api/v1/entries", headers=bearer(tok), json={
        "date": "2026-10-05", "kind": "inc", "store": "顧客", "amount": 5000, "category": "売上高", "rate": 10})
    assert r.status_code == 201
    # başka kullanıcı etkilenmez
    assert add_exp(client, token("U2")).status_code == 201


def test_bank_and_demo_entries_do_not_count(client, stripe_on):
    import store
    tok = token()
    for i in range(5):
        store.add_entry("U1", {"date": "2026-10-01", "kind": "exp", "store": "銀行", "amount": 100,
                               "category": "支払手数料", "rate": 10}, source="BANK")
    import billing
    assert billing.usage("U1")["receipts"] == 0
    assert add_exp(client, tok).status_code == 201
    assert billing.usage("U1")["receipts"] == 1


def test_previous_month_does_not_count(client, stripe_on):
    import billing
    import store
    tok = token()
    for i in range(30):
        add_exp(client, tok, i)
    with store.tx() as con:
        con.execute("UPDATE entries SET created_at='2020-01-15T10:00:00+09:00' WHERE user_id='U1'")
    assert billing.usage("U1")["receipts"] == 0
    assert add_exp(client, tok).status_code == 201


def test_free_invoice_limit_boundary(client, stripe_on):
    tok = token()
    for _ in range(3):
        assert add_inv(client, tok).status_code == 201
    r = add_inv(client, tok)
    assert r.status_code == 402 and "請求書3件" in r.json()["detail"]


def test_enforcement_can_be_disabled(client, stripe_on, monkeypatch):
    monkeypatch.setenv("BILLING_ENFORCE_LIMITS", "0")
    tok = token()
    for _ in range(4):
        assert add_inv(client, tok).status_code == 201


def test_paid_plan_lifts_limits_and_cancellation_restores(client, stripe_on):
    tok = token()
    for _ in range(3):
        add_inv(client, tok)
    assert webhook(client, sub_event("evt_1")).json()["result"] == "ok"
    st = client.get("/api/v1/billing/status", headers=bearer(tok)).json()
    assert st["plan"] == "personal" and st["limits"]["invoices_per_month"] is None
    assert st["subscription"]["current_period_end"].startswith("2027-01-01")
    assert add_inv(client, tok).status_code == 201
    # past_due hâlâ ücretli; deleted → free
    webhook(client, sub_event("evt_2", status="past_due"))
    assert client.get("/api/v1/billing/status", headers=bearer(tok)).json()["plan"] == "personal"
    webhook(client, sub_event("evt_3", status="canceled", etype="customer.subscription.deleted"))
    assert client.get("/api/v1/billing/status", headers=bearer(tok)).json()["plan"] == "free"
    assert add_inv(client, tok).status_code == 402


# ------------------------------------------------------------ webhook
def test_signature_verification_unit():
    import billing
    body = b'{"id":"evt"}'
    now = 1_800_000_000
    h = billing.sign(body, WH, now)
    assert billing.verify_signature(body, h, WH, now=now)
    assert billing.verify_signature(body, h, WH, now=now + 300)          # tolerans sınırı
    assert not billing.verify_signature(body, h, WH, now=now + 301)
    assert not billing.verify_signature(body + b" ", h, WH, now=now)     # gövde değişti
    assert not billing.verify_signature(body, h, "whsec_other", now=now)
    assert not billing.verify_signature(body, "", WH, now=now)
    assert not billing.verify_signature(body, "t=abc,v1=00", WH, now=now)
    # birden çok v1 (anahtar rotasyonu) — biri doğruysa geçer
    assert billing.verify_signature(body, h + ",v1=deadbeef", WH, now=now)


def test_webhook_rejects_bad_signature_and_old_timestamp(client, stripe_on):
    assert webhook(client, sub_event("evt_a"), secret="whsec_wrong").status_code == 400
    assert webhook(client, sub_event("evt_b"), ts=int(time.time()) - 3600).status_code == 400
    r = client.post("/api/v1/billing/webhook", content=b"{}")
    assert r.status_code == 400
    import billing
    assert billing.current_plan("U1") == "free"


def test_webhook_idempotent_and_unknown_events(client, stripe_on):
    assert webhook(client, sub_event("evt_d")).json()["result"] == "ok"
    assert webhook(client, sub_event("evt_d", status="canceled")).json()["result"] == "duplicate"
    import billing
    assert billing.current_plan("U1") == "personal"
    assert webhook(client, {"id": "evt_e", "type": "invoice.paid", "data": {"object": {}}}).json()["result"] == "ignored"
    # kullanıcı bilinmeyen abonelik
    ev = sub_event("evt_f", sub_id="sub_unknown")
    ev["data"]["object"]["metadata"] = {}
    assert webhook(client, ev).json()["result"] == "ignored"


def test_checkout_completed_then_subscription_update_by_id(client, stripe_on):
    import billing
    ev = {"id": "evt_c1", "type": "checkout.session.completed", "data": {"object": {
        "mode": "subscription", "client_reference_id": "U1", "payment_status": "paid", "customer": "cus_9",
        "subscription": "sub_9", "metadata": {"user_id": "U1", "plan": "business"}}}}
    assert webhook(client, ev).json()["result"] == "ok"
    assert billing.current_plan("U1") == "business"
    # metadata olmadan da abonelik kimliğinden kullanıcı bulunur; fiyat kimliği planı belirler
    up = sub_event("evt_c2", sub_id="sub_9", price="price_personal", cancel=True)
    up["data"]["object"]["metadata"] = {}
    assert webhook(client, up).json()["result"] == "ok"
    sub = billing.get_subscription("U1")
    assert sub["plan"] == "personal" and sub["cancel_at_period_end"] == 1 and sub["stripe_customer"] == "cus_1"


# ------------------------------------------------------------ checkout / iptal (Stripe mock)
def test_checkout_creates_session(client, stripe_on, monkeypatch):
    import billing
    calls = []

    async def fake_post(path, data):
        calls.append((path, data))
        return {"url": "https://checkout.stripe.com/c/pay/cs_test_1"}

    monkeypatch.setattr(billing, "stripe_post", fake_post)
    r = client.post("/api/v1/auth/signup", json={"email": "hana@example.jp", "password": "correct-horse-1"})
    tok, uid = r.json()["token"], r.json()["user_id"]
    r = client.post("/api/v1/billing/checkout", headers=bearer(tok), json={"plan": "personal"})
    assert r.status_code == 200 and r.json()["url"].startswith("https://checkout.stripe.com/")
    path, data = calls[0]
    assert path == "/checkout/sessions"
    assert data["mode"] == "subscription" and data["client_reference_id"] == uid
    assert data["line_items"] == [{"price": "price_personal", "quantity": 1}]
    assert data["customer_email"] == "hana@example.jp"
    assert data["success_url"].startswith("https://panel.example/")
    assert client.post("/api/v1/billing/checkout", headers=bearer(tok), json={"plan": "gold"}).status_code == 422


def test_checkout_price_missing_and_already_on_plan(client, stripe_on, monkeypatch):
    tok = token()
    monkeypatch.delenv("STRIPE_PRICE_BUSINESS")
    assert client.post("/api/v1/billing/checkout", headers=bearer(tok), json={"plan": "business"}).status_code == 503
    webhook(client, sub_event("evt_p"))
    assert client.post("/api/v1/billing/checkout", headers=bearer(tok), json={"plan": "personal"}).status_code == 409


def test_cancel_sets_period_end_flag(client, stripe_on, monkeypatch):
    import billing
    tok = token()
    assert client.post("/api/v1/billing/cancel", headers=bearer(tok)).status_code == 404
    webhook(client, sub_event("evt_k"))

    async def fake_post(path, data):
        assert path == "/subscriptions/sub_1" and data == {"cancel_at_period_end": True}
        return sub_event("x", cancel=True)["data"]["object"]

    monkeypatch.setattr(billing, "stripe_post", fake_post)
    r = client.post("/api/v1/billing/cancel", headers=bearer(tok))
    assert r.status_code == 200
    st = r.json()
    assert st["plan"] == "personal" and st["subscription"]["cancel_at_period_end"] is True


def test_stripe_error_maps_to_502(client, stripe_on, monkeypatch):
    import httpx

    import billing

    def handler(request):
        assert request.headers["Authorization"] == "Bearer sk_test_x"
        assert b"line_items%5B0%5D%5Bprice%5D=price_personal" in request.content
        return httpx.Response(400, json={"error": {"message": "bad"}})

    real = httpx.AsyncClient
    monkeypatch.setattr(billing.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    r = client.post("/api/v1/billing/checkout", headers=bearer(token()), json={"plan": "personal"})
    assert r.status_code == 502


def test_flatten_form_encoding():
    import billing
    out = billing._flatten({"a": {"b": 1}, "l": [{"x": "y"}], "t": True, "n": None})
    assert out == [("a[b]", "1"), ("l[0][x]", "y"), ("t", "true")]
