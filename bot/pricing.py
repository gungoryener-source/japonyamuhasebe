"""Fiyatlandırma ayarları (Q-16, ürün sahibi 2026-11-08): kural kodda sabit değil, yönetici ekranından değişir.

Şimdilik **ücretsiz**: `enabled=False` → ek şirket ücretsiz ve plan başına sınır yok
(yalnızca kötüye kullanım koruması MAX_COMPANIES_PER_ACCOUNT).
`enabled=True` iken:
- `included[plan]`: plana dahil şirket sayısı (ana şirket dahil).
- `extra_price_jpy`: dahil sayının üstündeki her şirket için aylık ek ücret (vergi hariç).
  0 ise dahil sayının üstünde şirket **eklenemez** (sınır); >0 ise eklenir ve ücret gösterilir.
  Not: ek ücretin Stripe'ta tahsili henüz otomatik değil (T-064c) — ekran ve uyarı tutarı gösterir.
"""
from __future__ import annotations

import json

import store
from store import tx

KEY = "companies"
PLANS = ("free", "personal", "business")
DEFAULT = {"enabled": False, "included": {"free": 1, "personal": 1, "business": 3}, "extra_price_jpy": 0}


def get() -> dict:
    try:
        with tx() as con:
            row = con.execute("SELECT value FROM pricing_settings WHERE key=?", (KEY,)).fetchone()
    except Exception:  # noqa: BLE001
        row = None
    if not row:
        return json.loads(json.dumps(DEFAULT))
    data = json.loads(row["value"])
    return {"enabled": bool(data.get("enabled")),
            "included": {p: int(data.get("included", {}).get(p, DEFAULT["included"][p])) for p in PLANS},
            "extra_price_jpy": int(data.get("extra_price_jpy", 0))}


def put(data: dict) -> dict:
    inc = data.get("included") or {}
    clean = {"enabled": bool(data.get("enabled")),
             "included": {p: int(inc.get(p, DEFAULT["included"][p])) for p in PLANS},
             "extra_price_jpy": int(data.get("extra_price_jpy", 0))}
    if any(not 1 <= v <= 1000 for v in clean["included"].values()):
        raise ValueError("included must be 1..1000")
    if not 0 <= clean["extra_price_jpy"] <= 1_000_000:
        raise ValueError("extra_price_jpy must be 0..1000000")
    with tx() as con:
        con.execute("DELETE FROM pricing_settings WHERE key=?", (KEY,))
        con.execute("INSERT INTO pricing_settings(key,value,updated_at) VALUES(?,?,?)",
                    (KEY, json.dumps(clean), store.now()))
    return clean


def company_status(plan: str, company_count: int) -> dict:
    """Hesabın şirket durumu: dahil sayı, ek şirket, aylık ek ücret, yeni şirket eklenebilir mi."""
    cfg = get()
    if not cfg["enabled"]:
        return {"enabled": False, "companies": company_count, "included": None, "extra": 0,
                "monthly_extra_jpy": 0, "can_add": True, "next_price_jpy": 0}
    inc = cfg["included"].get(plan, 1)
    extra = max(0, company_count - inc)
    price = cfg["extra_price_jpy"]
    can_add = company_count < inc or price > 0
    return {"enabled": True, "companies": company_count, "included": inc, "extra": extra,
            "monthly_extra_jpy": extra * price, "can_add": can_add,
            "next_price_jpy": 0 if company_count < inc else price}
