"""Abonelik (T-042): planlar, plan bazlı sınırlar, Stripe Checkout + webhook (test modu).

- Abonelik defter (`user_id`) bazındadır; LINE/WhatsApp/web hepsi aynı defteri paylaşır.
- Fiyatlar Q-11 cevaplanana kadar **yer tutucu** (`PLANS[...]["price_jpy"]`, `placeholder=True`).
  Stripe'ta tahsil edilen gerçek tutar Stripe Price nesnesindedir (`STRIPE_PRICE_PERSONAL` / `_BUSINESS`).
- `STRIPE_SECRET_KEY` yoksa ödeme kapalıdır: ödeme uçları 503, sınırlar **uygulanmaz** (yükseltme yolu
  olmadan kullanıcıyı engellememek için). `BILLING_ENFORCE_LIMITS=0` ile anahtar varken de kapatılabilir.
- Stripe REST'i httpx ile çağrılır (SDK yok). Webhook imzası `Stripe-Signature` (t=…,v1=…) HMAC-SHA256.
- Şema yalnızca ekleyici: `subscriptions`, `billing_events` (store.SCHEMA).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from urllib.parse import urlencode

import httpx

import store
from store import tx

STRIPE_API = "https://api.stripe.com/v1"
SIGNATURE_TOLERANCE = 300  # saniye

# Fiyatlar yer tutucu (Q-11). Sınır None = sınırsız.
PLANS: dict[str, dict] = {
    "free": {"name": "フリー", "price_jpy": 0, "receipts_per_month": 30, "invoices_per_month": 3},
    "personal": {"name": "個人", "price_jpy": 980, "receipts_per_month": None, "invoices_per_month": None},
    "business": {"name": "法人", "price_jpy": 2980, "receipts_per_month": None, "invoices_per_month": None},
}
PAID_PLANS = ("personal", "business")
# Stripe aboneliğinin bu durumlarında ücretli plan geçerlidir
ACTIVE_STATUSES = ("active", "trialing", "past_due")
# 「fiş」 sayılmayan kayıt kaynakları (banka hareketi, fatura ödemesi, demo)
NON_RECEIPT_SOURCES = ("BANK", "INVOICE", "DEMO")

LIMIT_MESSAGES = {
    "receipts": "今月のフリープランの上限（経費{limit}件）に達しました。有料プランにアップグレードしてください。",
    "invoices": "今月のフリープランの上限（請求書{limit}件）に達しました。有料プランにアップグレードしてください。",
}


class BillingError(Exception):
    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


class LimitExceeded(BillingError):
    def __init__(self, kind: str, limit: int):
        super().__init__(LIMIT_MESSAGES[kind].format(limit=limit), 402)
        self.kind, self.limit = kind, limit


# ---------------------------------------------------------------- yapılandırma
def secret_key() -> str:
    return os.environ.get("STRIPE_SECRET_KEY", "")


def webhook_secret() -> str:
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def price_id(plan: str) -> str:
    return os.environ.get(f"STRIPE_PRICE_{plan.upper()}", "")


def payments_enabled() -> bool:
    return bool(secret_key())


def limits_enforced() -> bool:
    return payments_enabled() and os.environ.get("BILLING_ENFORCE_LIMITS", "1") != "0"


def plan_for_price(pid: str) -> str | None:
    for p in PAID_PLANS:
        if pid and price_id(p) == pid:
            return p
    return None


def public_plans() -> list[dict]:
    return [{"id": k, **v, "placeholder": True, "available": k == "free" or bool(payments_enabled() and price_id(k))}
            for k, v in PLANS.items()]


# ---------------------------------------------------------------- abonelik durumu
def get_subscription(user_id: str) -> dict | None:
    with tx() as con:
        row = con.execute("SELECT * FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def current_plan(user_id: str) -> str:
    sub = get_subscription(user_id)
    if sub and sub["plan"] in PAID_PLANS and sub["status"] in ACTIVE_STATUSES:
        return sub["plan"]
    return "free"


def _month_prefix() -> str:
    return store.today().strftime("%Y-%m")


def usage(user_id: str) -> dict:
    """Bu ay (JST, oluşturulma zamanına göre) eklenen fiş/経費 ve fatura sayısı."""
    ym = _month_prefix()
    ph = ",".join("?" * len(NON_RECEIPT_SOURCES))
    with tx() as con:
        r = con.execute(
            f"""SELECT COUNT(*) n FROM entries WHERE user_id=? AND kind='exp'
                AND substr(created_at,1,7)=? AND source NOT IN ({ph})""",
            (user_id, ym, *NON_RECEIPT_SOURCES)).fetchone()
        i = con.execute("SELECT COUNT(*) n FROM invoices WHERE user_id=? AND substr(created_at,1,7)=?",
                        (user_id, ym)).fetchone()
    return {"month": ym, "receipts": int(r["n"]), "invoices": int(i["n"])}


def check_limit(user_id: str, kind: str) -> None:
    """Yeni bir `receipts` / `invoices` eklenmeden önce çağrılır. Sınır aşılacaksa LimitExceeded."""
    if not limits_enforced():
        return
    limit = PLANS[current_plan(user_id)][f"{kind}_per_month"]
    if limit is not None and usage(user_id)[kind] >= limit:
        raise LimitExceeded(kind, limit)


def status(user_id: str) -> dict:
    plan = current_plan(user_id)
    sub = get_subscription(user_id)
    p = PLANS[plan]
    return {
        "plan": plan, "plan_name": p["name"],
        "limits": {"receipts_per_month": p["receipts_per_month"], "invoices_per_month": p["invoices_per_month"]},
        "usage": usage(user_id),
        "payments_enabled": payments_enabled(), "limits_enforced": limits_enforced(),
        "subscription": {"plan": sub["plan"], "status": sub["status"], "current_period_end": sub["current_period_end"],
                         "cancel_at_period_end": bool(sub["cancel_at_period_end"])} if sub else None,
    }


def _upsert(user_id: str, **f) -> None:
    cols = ["plan", "status", "stripe_customer", "stripe_subscription", "current_period_end", "cancel_at_period_end"]
    with tx() as con:
        cur = con.execute("SELECT * FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()
        if cur:
            sets = {k: v for k, v in f.items() if k in cols and v is not None}
            if sets:
                con.execute(f"UPDATE subscriptions SET {', '.join(k + '=?' for k in sets)}, updated_at=? WHERE user_id=?",
                            (*sets.values(), store.now(), user_id))
        else:
            vals = {"plan": "free", "status": "incomplete", "stripe_customer": "", "stripe_subscription": "",
                    "current_period_end": "", "cancel_at_period_end": 0}
            vals.update({k: v for k, v in f.items() if k in cols and v is not None})
            con.execute(f"INSERT INTO subscriptions(user_id,{','.join(cols)},updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        (user_id, *(vals[c] for c in cols), store.now()))


# ---------------------------------------------------------------- Stripe REST
def _flatten(data: dict, prefix: str = "") -> list[tuple[str, str]]:
    """Stripe form kodlaması: {"a": {"b": 1}, "l": [{"x": 1}]} → a[b]=1, l[0][x]=1."""
    out: list[tuple[str, str]] = []
    for k, v in data.items():
        key = f"{prefix}[{k}]" if prefix else str(k)
        if isinstance(v, dict):
            out += _flatten(v, key)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                out += _flatten(item, f"{key}[{i}]") if isinstance(item, dict) else [(f"{key}[{i}]", str(item))]
        elif isinstance(v, bool):
            out.append((key, "true" if v else "false"))
        elif v is not None:
            out.append((key, str(v)))
    return out


async def stripe_post(path: str, data: dict) -> dict:
    if not payments_enabled():
        raise BillingError("お支払い機能は準備中です。", 503)
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{STRIPE_API}{path}", content=urlencode(_flatten(data)),
                              headers={"Authorization": f"Bearer {secret_key()}",
                                       "Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code >= 400:
        raise BillingError("決済サービスでエラーが発生しました。時間をおいて再度お試しください。", 502)
    return r.json()


async def create_checkout(user_id: str, plan: str, email: str = "") -> str:
    if not payments_enabled():
        raise BillingError("お支払い機能は準備中です。", 503)
    if plan not in PAID_PLANS:
        raise BillingError("プランが正しくありません。", 400)
    pid = price_id(plan)
    if not pid:
        raise BillingError("このプランは準備中です。", 503)
    if current_plan(user_id) == plan:
        raise BillingError("すでにこのプランをご利用中です。", 409)
    panel = os.environ.get("PANEL_URL", "").rstrip("/")
    data = {
        "mode": "subscription",
        "line_items": [{"price": pid, "quantity": 1}],
        "client_reference_id": user_id,
        "metadata": {"user_id": user_id, "plan": plan},
        "subscription_data": {"metadata": {"user_id": user_id, "plan": plan}},
        "success_url": f"{panel}/billing/?billing=success",
        "cancel_url": f"{panel}/billing/?billing=cancel",
        "locale": "ja",
    }
    sub = get_subscription(user_id)
    if sub and sub["stripe_customer"]:
        data["customer"] = sub["stripe_customer"]
    elif email:
        data["customer_email"] = email
    session = await stripe_post("/checkout/sessions", data)
    return session["url"]


async def cancel(user_id: str) -> dict:
    """Dönem sonunda iptal (cancel_at_period_end). Kalan süre kullanılabilir; veri silinmez."""
    if not payments_enabled():
        raise BillingError("お支払い機能は準備中です。", 503)
    sub = get_subscription(user_id)
    if not sub or not sub["stripe_subscription"] or current_plan(user_id) == "free":
        raise BillingError("解約できる有料プランがありません。", 404)
    obj = await stripe_post(f"/subscriptions/{sub['stripe_subscription']}", {"cancel_at_period_end": True})
    _apply_subscription_object(obj, fallback_user=user_id)
    return status(user_id)


# ---------------------------------------------------------------- webhook
def verify_signature(payload: bytes, header: str, secret: str, now: float | None = None) -> bool:
    if not secret or not header:
        return False
    parts: dict[str, list[str]] = {}
    for item in header.split(","):
        k, _, v = item.strip().partition("=")
        parts.setdefault(k, []).append(v)
    try:
        ts = int(parts.get("t", [""])[0])
    except ValueError:
        return False
    if abs((now if now is not None else time.time()) - ts) > SIGNATURE_TOLERANCE:
        return False
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", []))


def sign(payload: bytes, secret: str, ts: int | None = None) -> str:
    """Test yardımcısı: Stripe ile aynı biçimde imza başlığı üretir."""
    ts = int(time.time()) if ts is None else ts
    return f"t={ts},v1=" + hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()


def _user_for_subscription(sub_id: str) -> str | None:
    with tx() as con:
        row = con.execute("SELECT user_id FROM subscriptions WHERE stripe_subscription=?", (sub_id,)).fetchone()
    return row["user_id"] if row else None


def _period_end(obj: dict) -> str:
    ts = obj.get("current_period_end")
    if ts is None:  # yeni API sürümlerinde öğe düzeyinde
        items = (obj.get("items") or {}).get("data") or []
        ts = items[0].get("current_period_end") if items else None
    if not ts:
        return ""
    return datetime.fromtimestamp(int(ts), store.JST).isoformat(timespec="seconds")


def _apply_subscription_object(obj: dict, fallback_user: str | None = None) -> str | None:
    user_id = (obj.get("metadata") or {}).get("user_id") or _user_for_subscription(obj.get("id", "")) or fallback_user
    if not user_id:
        return None
    items = (obj.get("items") or {}).get("data") or []
    pid = ((items[0].get("price") or {}).get("id") if items else "") or ""
    plan = plan_for_price(pid) or (obj.get("metadata") or {}).get("plan")
    _upsert(user_id, plan=plan if plan in PAID_PLANS else None, status=obj.get("status"),
            stripe_customer=obj.get("customer") or None, stripe_subscription=obj.get("id") or None,
            current_period_end=_period_end(obj),
            cancel_at_period_end=int(bool(obj.get("cancel_at_period_end"))))
    return user_id


def handle_event(event: dict) -> str:
    """İmzası doğrulanmış olayı işler. Aynı olay iki kez gelirse 'duplicate' (idempotent)."""
    eid, etype = event.get("id", ""), event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    with tx() as con:
        if con.execute("SELECT 1 FROM billing_events WHERE event_id=?", (eid,)).fetchone():
            return "duplicate"
        con.execute("INSERT INTO billing_events(event_id,type,received_at) VALUES(?,?,?)", (eid, etype, store.now()))
    try:
        return _process_event(etype, obj)
    except Exception:
        # İşlenemeyen olay kaydı geri alınır → Stripe'ın yeniden denemesi 'duplicate' sayılmaz
        with tx() as con:
            con.execute("DELETE FROM billing_events WHERE event_id=?", (eid,))
        raise


def _process_event(etype: str, obj: dict) -> str:
    if etype == "checkout.session.completed" and obj.get("mode") == "subscription":
        user_id = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("user_id")
        plan = (obj.get("metadata") or {}).get("plan")
        if not user_id:
            return "ignored"
        _upsert(user_id, plan=plan if plan in PAID_PLANS else None,
                status="active" if obj.get("payment_status") in ("paid", "no_payment_required") else "incomplete",
                stripe_customer=obj.get("customer") or None, stripe_subscription=obj.get("subscription") or None)
        return "ok"
    if etype in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        return "ok" if _apply_subscription_object(obj) else "ignored"
    return "ignored"


def parse_event(payload: bytes, signature: str) -> dict:
    if not webhook_secret():
        raise BillingError("webhook not configured", 503)
    if not verify_signature(payload, signature, webhook_secret()):
        raise BillingError("invalid signature", 400)
    try:
        return json.loads(payload)
    except ValueError:
        raise BillingError("invalid payload", 400)
