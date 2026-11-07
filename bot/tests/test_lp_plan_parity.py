"""Tanıtım sayfası (dashboard-next/app/lib/lp.ts) fiyat tablosu bot/billing.py PLANS ile aynı mı (T-044)."""
import re
from pathlib import Path

from billing import PLANS

TS = Path(__file__).resolve().parents[2] / "dashboard-next" / "app" / "lib" / "lp.ts"


def _ts_plans() -> list[dict]:
    src = TS.read_text(encoding="utf-8")
    m = re.search(r"export const LP_PLANS = \[(.*?)\] as const;", src, re.S)
    assert m, "LP_PLANS not found in lp.ts"
    rows = re.findall(r'id: "(\w+)", name: "([^"]+)", price_jpy: (\d+), receipts_per_month: (null|\d+), '
                      r'invoices_per_month: (null|\d+)', m.group(1))
    return [{"id": i, "name": n, "price_jpy": int(p),
             "receipts_per_month": None if r == "null" else int(r),
             "invoices_per_month": None if v == "null" else int(v)} for i, n, p, r, v in rows]


def test_lp_plans_match_billing():
    expected = [{"id": k, "name": v["name"], "price_jpy": v["price_jpy"],
                 "receipts_per_month": v["receipts_per_month"], "invoices_per_month": v["invoices_per_month"]}
                for k, v in PLANS.items()]
    assert _ts_plans() == expected


def test_lp_has_no_placeholder_prices():
    assert all(not v["placeholder"] for v in PLANS.values())
    assert "仮" not in TS.read_text(encoding="utf-8")
