"""Reviewer (T-040 / T-042 incelemesi): parola sıfırlama, log gizliliği, bağlama + abonelik, webhook dayanıklılığı."""
import json
import logging

import pytest
from fastapi.testclient import TestClient

PW = "correct-horse-1"
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


def bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


def signup(client, email="taro@example.jp"):
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": PW})
    assert r.status_code == 201, r.text
    return r.json()


def webhook(client, event):
    import billing
    body = json.dumps(event).encode()
    return client.post("/api/v1/billing/webhook", content=body,
                       headers={"Stripe-Signature": billing.sign(body, WH), "Content-Type": "application/json"})


def sub_event(eid, uid, status="active", price="price_personal"):
    return {"id": eid, "type": "customer.subscription.updated", "data": {"object": {
        "id": "sub_" + uid, "object": "subscription", "customer": "cus_1", "status": status,
        "cancel_at_period_end": False, "current_period_end": 1798729200, "metadata": {"user_id": uid},
        "items": {"data": [{"price": {"id": price}}]}}}}


# ------------------------------------------------------------ parola sıfırlama
def test_reset_invalidates_other_outstanding_links(client):
    import accounts
    signup(client)
    first = accounts.request_password_reset("taro@example.jp")
    second = accounts.request_password_reset("taro@example.jp")
    r = client.post("/api/v1/auth/password-reset/confirm", json={"token": second, "password": "new-password-99"})
    assert r.status_code == 200
    # Eski e-postadaki bağlantı artık parolayı değiştiremez
    r = client.post("/api/v1/auth/password-reset/confirm", json={"token": first, "password": "attacker-pass-1"})
    assert r.status_code == 400
    assert client.post("/api/v1/auth/login", json={"email": "taro@example.jp",
                                                   "password": "new-password-99"}).status_code == 200


def test_reset_link_not_in_info_logs(client, caplog, monkeypatch):
    import accounts
    monkeypatch.delenv("MAIL_PROVIDER", raising=False)
    signup(client)
    with caplog.at_level(logging.INFO, logger="accounts"):
        token = accounts.request_password_reset("taro@example.jp")
    assert "MAIL_PROVIDER not set" in caplog.text
    assert token not in caplog.text            # sıfırlama bağlantısı = hesabı ele geçirme anahtarı
    assert "taro@example.jp" not in caplog.text  # kişisel veri log'a tam yazılmaz
    assert "t***@example.jp" in caplog.text


def test_mask_email():
    import accounts
    assert accounts.mask_email("taro@example.jp") == "t***@example.jp"
    assert accounts.mask_email("") == "***"
    assert accounts.mask_email("no-at-sign") == "***"


def test_unknown_reset_token_and_wrong_prefix(client):
    signup(client)
    for t in ("rs_nope", "", "tk_x"):
        r = client.post("/api/v1/auth/password-reset/confirm", json={"token": t or " ", "password": "new-password-99"})
        assert r.status_code == 400


def test_login_email_is_case_insensitive_and_trimmed(client):
    signup(client, "Taro@Example.jp")
    r = client.post("/api/v1/auth/login", json={"email": "  TARO@example.JP ", "password": PW})
    assert r.status_code == 200 and r.json()["account"]["email"] == "taro@example.jp"
    assert client.post("/api/v1/auth/signup", json={"email": "taro@EXAMPLE.jp", "password": PW}).status_code == 409


# ------------------------------------------------------------ bağlama + abonelik
def test_link_refused_when_web_ledger_has_subscription(bot, client, stripe_on):
    acc = signup(client)
    assert webhook(client, sub_event("evt_r1", acc["user_id"])).json()["result"] == "ok"
    code = bot.issue_token("Uline-sub", "line-panel")
    r = client.post("/api/v1/auth/link-line", json={"code": code}, headers=bearer(acc["token"]))
    assert r.status_code == 409  # ücretli abonelik sahipsiz kalmasın
    assert client.get("/api/v1/billing/status", headers=bearer(acc["token"])).json()["plan"] == "personal"


# ------------------------------------------------------------ abonelik durum sınırları
@pytest.mark.parametrize("status,plan", [("active", "personal"), ("trialing", "personal"), ("past_due", "personal"),
                                         ("unpaid", "free"), ("canceled", "free"), ("incomplete", "free"),
                                         ("incomplete_expired", "free")])
def test_subscription_status_boundaries(client, stripe_on, status, plan):
    import billing
    webhook(client, sub_event("evt_s_" + status, "U-st", status=status))
    assert billing.current_plan("U-st") == plan


def test_unknown_price_without_plan_metadata_stays_free(client, stripe_on):
    import billing
    webhook(client, sub_event("evt_p1", "U-pr", price="price_other"))
    assert billing.current_plan("U-pr") == "free"


def test_failed_event_processing_is_retryable(client, stripe_on, monkeypatch):
    import billing
    calls = {"n": 0}
    real = billing._upsert

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("db down")
        return real(*a, **k)

    monkeypatch.setattr(billing, "_upsert", flaky)
    ev = sub_event("evt_retry", "U-rt")
    with pytest.raises(RuntimeError):
        billing.handle_event(ev)
    # Stripe yeniden dener → 'duplicate' değil, işlenir
    assert billing.handle_event(ev) == "ok"
    assert billing.current_plan("U-rt") == "personal"
    assert billing.handle_event(ev) == "duplicate"
