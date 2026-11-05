"""REST API v1 — web paneli (dashboard-next) ve dış entegrasyonlar için. Belgeler: docs/API.md

Kimlik: `Authorization: Bearer tk_...` (LINE'da「パネル」komutu veya admin uç noktasıyla üretilir).
"""
from __future__ import annotations

import hmac
import os
import re
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

import export
import invoices as inv_mod
import store
from tax import consumption as ct

router = APIRouter(prefix="/api/v1", tags=["api"])

YM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CATEGORIES = ["売上高", "旅費交通費", "消耗品費", "会議費", "接待交際費", "通信費", "地代家賃", "水道光熱費",
              "外注工賃", "新聞図書費", "広告宣伝費", "支払手数料", "雑費"]


def _admin_ok(key: str) -> bool:
    admin = os.environ.get("ADMIN_KEY", "")
    return bool(admin) and hmac.compare_digest(key or "", admin)


def current_user(authorization: str = Header(default="")) -> str:
    token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    uid = store.user_for_token(token)
    if not uid:
        raise HTTPException(401, "invalid or missing bearer token")
    return uid


def _valid_date(s: str, name: str) -> str:
    if not DATE.match(s):
        raise HTTPException(400, f"{name} must be YYYY-MM-DD")
    try:
        date.fromisoformat(s)
    except ValueError:
        raise HTTPException(400, f"{name} is not a valid date")
    return s


def _shift_month(ym: str, delta: int) -> str:
    y, m = map(int, ym.split("-"))
    i = y * 12 + (m - 1) + delta
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def _pct(cur: int, prev: int) -> float | None:
    return None if prev == 0 else round((cur - prev) / abs(prev) * 100, 1)


# ---------------------------------------------------------------- summary / cashflow
@router.get("/summary")
def summary(month: str | None = None, uid: str = Depends(current_user)):
    month = month or store.today().strftime("%Y-%m")
    if not YM.match(month):
        raise HTTPException(400, "month must be YYYY-MM")
    inc, exp = store.month_summary(uid, month)
    pinc, pexp = store.month_summary(uid, _shift_month(month, -1))
    rows = store.search_entries(uid, date_from=f"{month}-01", date_to=f"{month}-31", kind="exp")
    unpaid = [i for i in store.list_invoices(uid, "unpaid")]
    return {
        "month": month,
        "revenue": inc, "expenses": exp, "profit": inc - exp,
        "revenue_change_pct": _pct(inc, pinc), "expenses_change_pct": _pct(exp, pexp),
        "profit_change_pct": _pct(inc - exp, pinc - pexp),
        "expenses_without_invoice_no": sum(1 for r in rows if not r["invoice_no"] and r["rate"]),
        "receivables": sum(i["total"] for i in unpaid), "unpaid_invoices": len(unpaid),
    }


@router.get("/cashflow")
def cashflow(months: int = Query(6, ge=1, le=24), end: str | None = None, uid: str = Depends(current_user)):
    end = end or store.today().strftime("%Y-%m")
    if not YM.match(end):
        raise HTTPException(400, "end must be YYYY-MM")
    out = []
    for k in range(months - 1, -1, -1):
        ym = _shift_month(end, -k)
        inc, exp = store.month_summary(uid, ym)
        out.append({"month": ym, "income": inc, "expense": exp, "net": inc - exp})
    return out


# ---------------------------------------------------------------- entries (電帳法 search)
class EntryIn(BaseModel):
    date: str
    kind: str = Field(pattern="^(inc|exp)$")
    store: str = Field(min_length=1, max_length=100)
    amount: int = Field(gt=0, lt=10**11)
    category: str
    rate: int = 10
    invoice_no: str = ""


@router.get("/entries")
def list_entries(date_from: str | None = None, date_to: str | None = None, q: str | None = None,
                 amount_min: int | None = None, amount_max: int | None = None, kind: str | None = None,
                 limit: int = Query(500, ge=1, le=5000), uid: str = Depends(current_user)):
    if date_from:
        _valid_date(date_from, "date_from")
    if date_to:
        _valid_date(date_to, "date_to")
    return store.search_entries(uid, date_from=date_from, date_to=date_to, q=q, amount_min=amount_min,
                                amount_max=amount_max, kind=kind, limit=limit)


@router.post("/entries", status_code=201)
def create_entry(body: EntryIn, uid: str = Depends(current_user)):
    _valid_date(body.date, "date")
    if body.rate not in (10, 8, 0):
        raise HTTPException(400, "rate must be 10, 8 or 0")
    if body.category not in CATEGORIES:
        raise HTTPException(400, f"category must be one of {CATEGORIES}")
    if body.invoice_no and not re.fullmatch(r"T\d{13}", body.invoice_no):
        raise HTTPException(400, "invoice_no must be T + 13 digits")
    e = body.model_dump()
    eid = store.add_entry(uid, e, source="WEB")
    return {"id": eid, **e}


# ---------------------------------------------------------------- consumption tax
@router.get("/tax/consumption")
def consumption_tax(year: int = Query(..., ge=2023, le=2035), method: str = "honsoku",
                    kani_type: int | None = None, uid: str = Depends(current_user)):
    rows = store.search_entries(uid, date_from=f"{year}-01-01", date_to=f"{year}-12-31", limit=5000)
    sales = [ct.Sale(r["amount"], r["rate"]) for r in rows if r["kind"] == "inc"]
    purchases = [ct.Purchase(r["amount"], r["rate"], date.fromisoformat(r["d"]), bool(r["invoice_no"]))
                 for r in rows if r["kind"] == "exp"]
    prof = store.get_profile(uid)
    try:
        res = ct.compute(sales, purchases, method, kani_type=kani_type,  # type: ignore[arg-type]
                         individual=bool(prof["individual"]), tax_year=year)
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    return {"year": year, "method": method, "output_tax": res.output_tax, "input_tax": res.input_tax,
            "payable": res.payable, "by_rate": res.by_rate}


# ---------------------------------------------------------------- profile
class ProfileIn(BaseModel):
    business_name: str = Field(default="", max_length=100)
    registration_no: str = ""
    individual: bool = True


@router.get("/profile")
def get_profile(uid: str = Depends(current_user)):
    return store.get_profile(uid)


@router.put("/profile")
def put_profile(body: ProfileIn, uid: str = Depends(current_user)):
    if body.registration_no and not re.fullmatch(r"T\d{13}", body.registration_no):
        raise HTTPException(400, "registration_no must be T + 13 digits")
    return store.save_profile(uid, business_name=body.business_name, registration_no=body.registration_no,
                              individual=int(body.individual))


# ---------------------------------------------------------------- invoices
class ItemIn(BaseModel):
    name: str
    qty: int = 1
    unit_price: int
    rate: int = 10


class InvoiceIn(BaseModel):
    client: str = Field(min_length=1, max_length=100)
    issued: str | None = None
    due: str
    items: list[ItemIn]


@router.get("/invoices")
def list_invoices(status: str | None = None, uid: str = Depends(current_user)):
    rows = store.list_invoices(uid, status)
    today = store.today().isoformat()
    for r in rows:
        r["overdue"] = r["status"] == "unpaid" and r["due"] < today
    return rows


@router.post("/invoices", status_code=201)
def create_invoice(body: InvoiceIn, uid: str = Depends(current_user)):
    issued = _valid_date(body.issued, "issued") if body.issued else store.today().isoformat()
    _valid_date(body.due, "due")
    if body.due < issued:
        raise HTTPException(400, "due must be on or after issued")
    try:
        items = inv_mod.validate_items([i.model_dump() for i in body.items])
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    t = inv_mod.compute_totals(items)
    inv = {"no": store.next_invoice_no(uid, issued), "client": body.client, "issued": issued, "due": body.due,
           "items": items, "subtotal10": t.subtotal10, "subtotal8": t.subtotal8, "tax10": t.tax10,
           "tax8": t.tax8, "total": t.total}
    return store.insert_invoice(uid, inv)


@router.post("/invoices/{no}/paid")
def pay_invoice(no: str, paid_on: str | None = None, uid: str = Depends(current_user)):
    paid_on = _valid_date(paid_on, "paid_on") if paid_on else store.today().isoformat()
    inv = store.mark_invoice_paid(uid, no, paid_on)
    if not inv:
        raise HTTPException(404, "invoice not found")
    return inv


@router.get("/invoices/{no}/pdf")
def invoice_pdf(no: str, uid: str = Depends(current_user)):
    inv = store.get_invoice(uid, no)
    if not inv:
        raise HTTPException(404, "invoice not found")
    pdf = inv_mod.render_pdf(inv, store.get_profile(uid))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{no}.pdf"'})


# ---------------------------------------------------------------- export
@router.get("/export.csv")
def export_csv(format: str = "freee", year: int = Query(..., ge=2023, le=2035), uid: str = Depends(current_user)):
    if format not in export.FORMATS:
        raise HTTPException(400, f"format must be one of {export.FORMATS}")
    rows = store.search_entries(uid, date_from=f"{year}-01-01", date_to=f"{year}-12-31", limit=5000)
    body = export.to_csv(rows, format)
    # 会計ソフトは Shift_JIS(CP932) 取込が一般的
    return Response(body.encode("cp932", errors="replace"), media_type="text/csv; charset=Shift_JIS",
                    headers={"Content-Disposition": f'attachment; filename="tegaru_{format}_{year}.csv"'})


# ---------------------------------------------------------------- admin
class TokenIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    label: str = ""


@router.post("/admin/tokens", status_code=201)
def admin_issue_token(body: TokenIn, x_admin_key: str = Header(default="")):
    if not _admin_ok(x_admin_key):
        raise HTTPException(401, "admin key required")
    return {"user_id": body.user_id, "token": store.issue_token(body.user_id, body.label)}


@router.post("/admin/demo-seed", status_code=201)
def admin_demo_seed(x_admin_key: str = Header(default="")):
    """Panel denemesi için 'demo' defterine örnek veri ekler ve token döner."""
    if not _admin_ok(x_admin_key):
        raise HTTPException(401, "admin key required")
    uid = "demo"
    if not store.search_entries(uid, limit=1):
        import demo_data
        demo_data.seed(uid)
    return {"user_id": uid, "token": store.issue_token(uid, "demo")}
