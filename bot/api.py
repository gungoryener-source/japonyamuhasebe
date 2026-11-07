"""REST API v1 — web paneli (dashboard-next) ve dış entegrasyonlar için. Belgeler: docs/API.md

Kimlik: `Authorization: Bearer tk_...` (LINE'da「パネル」komutu veya admin uç noktasıyla üretilir).
"""
from __future__ import annotations

import hmac
import os
import re
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

import accounts
import archive
import bank_csv
import billing
import export
import invoices as inv_mod
import ratelimit
import reports
import store
import team
from store import MAX_ENTRY_AMOUNT
from tax import consumption as ct
from tax import income as it

router = APIRouter(prefix="/api/v1", tags=["api"])

YM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CATEGORIES = ["売上高", "旅費交通費", "消耗品費", "会議費", "接待交際費", "通信費", "地代家賃", "水道光熱費",
              "外注工賃", "新聞図書費", "広告宣伝費", "支払手数料", "雑費"]


def _admin_ok(key: str) -> bool:
    admin = os.environ.get("ADMIN_KEY", "")
    return bool(admin) and hmac.compare_digest((key or "").encode(), admin.encode())


def current_principal(authorization: str = Header(default="")) -> dict:
    """{user_id, role, account_id} — rol her istekte çözülür (T-041)."""
    token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    p = team.resolve(token)
    if not p:
        raise HTTPException(401, "invalid or missing bearer token")
    return p


def current_user(p: dict = Depends(current_principal)) -> str:
    """Okuma: tüm roller (owner / accountant / viewer)."""
    return p["user_id"]


def writer_user(p: dict = Depends(current_principal)) -> str:
    """Muhasebe verisi yazma: owner / accountant."""
    if p["role"] not in team.WRITE_ROLES:
        raise HTTPException(403, "閲覧専用のメンバーは編集できません。")
    return p["user_id"]


def owner_user(p: dict = Depends(current_principal)) -> str:
    """Abonelik, LINE 連携, ekip yönetimi: yalnızca sahip."""
    if p["role"] != "owner":
        raise HTTPException(403, "この操作は帳簿のオーナーのみ行えます。")
    return p["user_id"]


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
    amount: int = Field(gt=0, lt=MAX_ENTRY_AMOUNT)
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
def create_entry(body: EntryIn, uid: str = Depends(writer_user)):
    _valid_date(body.date, "date")
    if body.rate not in (10, 8, 0):
        raise HTTPException(400, "rate must be 10, 8 or 0")
    if body.category not in CATEGORIES:
        raise HTTPException(400, f"category must be one of {CATEGORIES}")
    if body.invoice_no and not re.fullmatch(r"T\d{13}", body.invoice_no):
        raise HTTPException(400, "invoice_no must be T + 13 digits")
    e = body.model_dump()
    if e["kind"] == "exp":
        _billing_call(billing.check_limit, uid, "receipts")
    eid = store.add_entry(uid, e, source="WEB")
    return {"id": eid, **e}


class EntryPatch(BaseModel):
    date: str | None = None
    store: str | None = Field(default=None, min_length=1, max_length=100)
    amount: int | None = Field(default=None, gt=0, lt=MAX_ENTRY_AMOUNT)
    category: str | None = None
    rate: int | None = None
    invoice_no: str | None = None


@router.patch("/entries/{entry_id}")
def patch_entry(entry_id: int, body: EntryPatch, uid: str = Depends(writer_user)):
    if not store.get_entry(uid, entry_id):
        raise HTTPException(404, "entry not found")
    f = body.model_dump(exclude_none=True)
    if not f:
        raise HTTPException(400, "no fields to update")
    if "date" in f:
        f["d"] = _valid_date(f.pop("date"), "date")
    if "rate" in f and f["rate"] not in (10, 8, 0):
        raise HTTPException(400, "rate must be 10, 8 or 0")
    if "category" in f and f["category"] not in CATEGORIES:
        raise HTTPException(400, "unknown category")
    if f.get("invoice_no") and not re.fullmatch(r"T\d{13}", f["invoice_no"]):
        raise HTTPException(400, "invoice_no must be T + 13 digits")
    return store.update_entry(uid, entry_id, **f)


@router.delete("/entries/{entry_id}", status_code=204)
def remove_entry(entry_id: int, uid: str = Depends(writer_user)):
    if not store.delete_entry(uid, entry_id):
        raise HTTPException(404, "entry not found")
    return Response(status_code=204)


MAX_UPLOAD = 10 * 1024 * 1024


async def _body(request: Request) -> bytes:
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "empty body")
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "file too large (max 10MB)")
    return raw


@router.post("/receipts/ocr", dependencies=[Depends(ratelimit.limiter("ocr"))])
async def receipt_ocr(request: Request, uid: str = Depends(writer_user)):
    """Fiş görseli (ham gövde, image/*) → okunan kayıt önerileri. Kaydetmez; kullanıcı onaylayınca POST /entries."""
    raw = await _body(request)
    import app as app_mod  # OCR motoru seçimi app.py'de
    result = await app_mod.ocr_receipt(raw)
    if isinstance(result, dict):
        return {"ok": False, "error": result.get("error"), "partial": result.get("partial", {}), "entries": []}
    return {"ok": True, "entries": result}


# ---------------------------------------------------------------- bank (CSV)
@router.post("/bank/import")
async def bank_import(request: Request, account: str = "", uid: str = Depends(writer_user)):
    raw = await _body(request)
    try:
        rows = bank_csv.parse(raw)
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    added, dup = store.insert_bank_rows(uid, rows, account)
    return {"parsed": len(rows), "imported": added, "duplicates": dup, "suggestions": bank_suggestions(uid)}


@router.get("/bank/transactions")
def bank_transactions(uid: str = Depends(current_user)):
    return {"transactions": store.list_bank_tx(uid), "suggestions": bank_suggestions(uid)}


def bank_suggestions(uid: str) -> list[dict]:
    """入金 = 未入金請求書の税込合計 ve tarih ≥ fatura tarihi → 消込 önerisi (her fatura en fazla bir harekete)."""
    unpaid = store.list_invoices(uid, "unpaid")
    used: set[str] = set()
    out = []
    for t in sorted(store.list_bank_tx(uid), key=lambda x: x["d"]):
        if t["amount"] <= 0 or t["invoice_no"]:
            continue
        for inv in unpaid:
            if inv["no"] in used or inv["total"] != t["amount"] or t["d"] < inv["issued"]:
                continue
            out.append({"tx_id": t["id"], "invoice_no": inv["no"], "client": inv["client"], "amount": t["amount"], "date": t["d"]})
            used.add(inv["no"])
            break
    return out


class MatchIn(BaseModel):
    tx_id: int
    invoice_no: str


@router.post("/bank/match")
def bank_match(body: MatchIn, uid: str = Depends(writer_user)):
    t = store.get_bank_tx(uid, body.tx_id)
    inv = store.get_invoice(uid, body.invoice_no)
    if not t or not inv:
        raise HTTPException(404, "transaction or invoice not found")
    if t["invoice_no"] or inv["status"] == "paid":
        raise HTTPException(409, "already matched")
    if t["amount"] != inv["total"]:
        raise HTTPException(400, "amount does not match invoice total")
    paid = store.mark_invoice_paid(uid, inv["no"], t["d"])
    store.link_bank_tx(uid, t["id"], invoice_no=inv["no"])
    return paid


class ToEntryIn(BaseModel):
    category: str
    rate: int = 10
    invoice_no: str = ""


@router.post("/bank/{tx_id}/entry", status_code=201)
def bank_to_entry(tx_id: int, body: ToEntryIn, uid: str = Depends(writer_user)):
    """出金 hareketini 経費 olarak kaydet (口座振替: 家賃, 通信費 vb.)."""
    t = store.get_bank_tx(uid, tx_id)
    if not t:
        raise HTTPException(404, "transaction not found")
    if t["entry_id"] or t["invoice_no"]:
        raise HTTPException(409, "already recorded")
    if t["amount"] >= 0:
        raise HTTPException(400, "only withdrawals can be recorded as expenses")
    if body.category not in CATEGORIES or body.category == "売上高":
        raise HTTPException(400, "unknown expense category")
    if body.rate not in (10, 8, 0):
        raise HTTPException(400, "rate must be 10, 8 or 0")
    if body.invoice_no and not re.fullmatch(r"T\d{13}", body.invoice_no):
        raise HTTPException(400, "invoice_no must be T + 13 digits")
    e = {"date": t["d"], "kind": "exp", "store": t["description"][:100], "amount": -t["amount"],
         "category": body.category, "rate": body.rate, "invoice_no": body.invoice_no}
    if -t["amount"] >= store.MAX_ENTRY_AMOUNT:
        raise HTTPException(400, f"amount must be < {store.MAX_ENTRY_AMOUNT}")
    eid = store.add_entry(uid, e, source="BANK")
    store.link_bank_tx(uid, tx_id, entry_id=eid)
    return {"id": eid, **e}


# ---------------------------------------------------------------- settings
@router.get("/channels")
def channels(uid: str = Depends(current_user)):
    """Kanal ve OCR durumu (sırlar döndürülmez)."""
    import receipt_ocr
    env = os.environ.get
    return {
        "line": {"configured": bool(env("LINE_CHANNEL_SECRET") and env("LINE_CHANNEL_ACCESS_TOKEN")),
                 "webhook": "/callback", "linked": not uid.startswith(("wa:", "demo"))},
        "whatsapp": {"configured": bool(env("WHATSAPP_TOKEN") and env("WHATSAPP_PHONE_ID")), "webhook": "/whatsapp"},
        "ocr": {"engine": env("OCR_ENGINE", "tesseract"), "tesseract": receipt_ocr.available(),
                "ai_fallback": bool(env("ANTHROPIC_API_KEY"))},
        "categories": CATEGORIES,
    }


# ---------------------------------------------------------------- consumption tax
@router.get("/tax/consumption")
def consumption_tax(year: int = Query(..., ge=2023, le=2035), method: str = "honsoku",
                    kani_type: int | None = None, uid: str = Depends(current_user)):
    rows = store.entries_in_range(uid, f"{year}-01-01", f"{year}-12-31")
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
            "payable": res.payable, "by_rate": res.by_rate,
            "unqualified": ct.transitional_breakdown(purchases)}


# ---------------------------------------------------------------- 確定申告 (individual)
@router.get("/pl")
def profit_and_loss(year: int = Query(..., ge=2023, le=2035), uid: str = Depends(current_user)):
    """青色申告決算書（損益計算書）の簡易版: 売上・勘定科目別経費・所得金額。"""
    rows = store.entries_in_range(uid, f"{year}-01-01", f"{year}-12-31")
    revenue = sum(r["amount"] for r in rows if r["kind"] == "inc")
    by_cat: dict[str, int] = {}
    for r in rows:
        if r["kind"] == "exp":
            by_cat[r["category"]] = by_cat.get(r["category"], 0) + r["amount"]
    expenses = sum(by_cat.values())
    return {"year": year, "revenue": revenue,
            "expenses": [{"category": k, "amount": v} for k, v in sorted(by_cat.items(), key=lambda x: -x[1])],
            "expenses_total": expenses, "income_before_blue": revenue - expenses,
            "note": "税込経理（消費税込みの金額）で集計しています。"}


@router.get("/tax/income")
def income_tax(year: int = Query(..., ge=2023, le=2035), blue: int = 650_000,
               social_insurance: int = Query(0, ge=0), other_deductions: int = Query(0, ge=0),
               uid: str = Depends(current_user)):
    pl = profit_and_loss(year, uid)
    try:
        r = it.compute(pl["revenue"], pl["expenses_total"], year=year, blue=blue,
                       social_insurance=social_insurance, other_deductions=other_deductions)
    except NotImplementedError as ex:
        raise HTTPException(409, str(ex))
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    return {"year": year, "revenue": pl["revenue"], "expenses": pl["expenses_total"], **r.__dict__,
            "disclaimer": "概算です。源泉徴収税額・予定納税・他の所得控除は含みません。"}


# ---------------------------------------------------------------- profile
class ProfileIn(BaseModel):
    business_name: str = Field(default="", max_length=100)
    registration_no: str = ""
    individual: bool = True


@router.get("/profile")
def get_profile(uid: str = Depends(current_user)):
    return store.get_profile(uid)


@router.put("/profile")
def put_profile(body: ProfileIn, uid: str = Depends(writer_user)):
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
def create_invoice(body: InvoiceIn, uid: str = Depends(writer_user)):
    issued = _valid_date(body.issued, "issued") if body.issued else store.today().isoformat()
    _valid_date(body.due, "due")
    if body.due < issued:
        raise HTTPException(400, "due must be on or after issued")
    try:
        items = inv_mod.validate_items([i.model_dump() for i in body.items])
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    _billing_call(billing.check_limit, uid, "invoices")
    t = inv_mod.compute_totals(items)
    inv = {"no": store.next_invoice_no(uid, issued), "client": body.client, "issued": issued, "due": body.due,
           "items": items, "subtotal10": t.subtotal10, "subtotal8": t.subtotal8, "tax10": t.tax10,
           "tax8": t.tax8, "total": t.total}
    return store.insert_invoice(uid, inv)


@router.post("/invoices/{no}/paid")
def pay_invoice(no: str, paid_on: str | None = None, uid: str = Depends(writer_user)):
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


# ---------------------------------------------------------------- reports (T-045)
@router.get("/reports/blue-return.pdf")
def blue_return_pdf(year: int = Query(..., ge=2023, le=2035),
                    blue: int = Query(650_000), uid: str = Depends(current_user)):
    """青色申告決算書（損益計算書）への転記用 PDF（参考資料）。"""
    if blue not in (0, 100_000, 550_000, 650_000):
        raise HTTPException(400, "blue must be 0, 100000, 550000 or 650000")
    pl = profit_and_loss(year, uid)
    rows = store.entries_in_range(uid, f"{year}-01-01", f"{year}-12-31")
    pdf = reports.render_blue_return_pdf(year, pl, rows, store.get_profile(uid), blue)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="blue-return-{year}.pdf"'})


# ---------------------------------------------------------------- export
@router.get("/export.csv")
def export_csv(format: str = "freee", year: int = Query(..., ge=2023, le=2035), uid: str = Depends(current_user)):
    if format not in export.FORMATS:
        raise HTTPException(400, f"format must be one of {export.FORMATS}")
    rows = store.entries_in_range(uid, f"{year}-01-01", f"{year}-12-31")
    body = export.to_csv(rows, format)
    # 会計ソフトは Shift_JIS(CP932) 取込が一般的
    return Response(body.encode("cp932", errors="replace"), media_type="text/csv; charset=Shift_JIS",
                    headers={"Content-Disposition": f'attachment; filename="tegaru_{format}_{year}.csv"'})


@router.get("/export/all.zip")
def export_all_zip(uid: str = Depends(current_user)):
    """T-046: 全期間の仕訳・請求書（CSV + PDF）を ZIP で。閲覧メンバーも可。"""
    body = archive.build_zip(uid)
    stamp = store.today().strftime("%Y%m%d")
    return Response(body, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="tegaru_all_{stamp}.zip"'})


@router.delete("/tokens/current", status_code=204)
def revoke_current(authorization: str = Header(default=""), uid: str = Depends(current_user)):
    store.revoke_token(authorization.removeprefix("Bearer ").strip())
    return Response(status_code=204)


# ---------------------------------------------------------------- auth (T-040)
class SignupIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=accounts.PASSWORD_MAX)


class LinkIn(BaseModel):
    code: str = Field(min_length=1, max_length=200)


class ResetRequestIn(BaseModel):
    email: str = Field(min_length=1, max_length=254)


class ResetConfirmIn(BaseModel):
    token: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=accounts.PASSWORD_MAX)


def _auth_result(acc: dict, token: str) -> dict:
    return {"account": {"id": acc["id"], "email": acc["email"]}, "user_id": acc["user_id"], "token": token}


def _account_call(fn, *args):
    try:
        return fn(*args)
    except accounts.AccountError as e:
        raise HTTPException(e.code, str(e))


@router.post("/auth/signup", status_code=201, dependencies=[Depends(ratelimit.limiter("signup"))])
def auth_signup(body: SignupIn):
    return _auth_result(*_account_call(accounts.signup, body.email, body.password))


@router.post("/auth/login", dependencies=[Depends(ratelimit.limiter("login"))])
def auth_login(body: SignupIn):
    ratelimit.check("login_email", body.email.strip().lower())  # T-058
    return _auth_result(*_account_call(accounts.login, body.email, body.password))


@router.get("/auth/me")
def auth_me(p: dict = Depends(current_principal)):
    """İsteği yapan hesap (üye oturumunda üyenin kendi hesabı) + defter ve rol."""
    acc = accounts.account_by_id(p["account_id"]) if p["account_id"] else None
    return {"user_id": p["user_id"], "role": p["role"],
            "account": ({"id": acc["id"], "email": acc["email"],
                         "email_verified": bool(acc["email_verified"])} if acc else None)}


@router.post("/auth/link-line")
def auth_link_line(body: LinkIn, uid: str = Depends(owner_user)):
    return _auth_result(*_account_call(accounts.link_ledger, uid, body.code))


@router.post("/auth/password-reset/request", status_code=202,
             dependencies=[Depends(ratelimit.limiter("password_reset"))])
def auth_reset_request(body: ResetRequestIn):
    accounts.request_password_reset(body.email)  # hesap olsun olmasın aynı yanıt
    return {"ok": True}


@router.post("/auth/password-reset/confirm")
def auth_reset_confirm(body: ResetConfirmIn):
    _account_call(accounts.confirm_password_reset, body.token, body.password)
    return {"ok": True}


# ---------------------------------------------------------------- team (T-041)
def _team_call(fn, *args):
    try:
        return fn(*args)
    except team.TeamError as e:
        raise HTTPException(e.code, str(e))


class InviteIn(BaseModel):
    role: str = Field(pattern="^(accountant|viewer)$")


class JoinIn(BaseModel):
    code: str = Field(min_length=1, max_length=200)


class RoleIn(BaseModel):
    role: str = Field(pattern="^(accountant|viewer)$")


class SwitchIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)


@router.get("/team/members")
def team_members(uid: str = Depends(owner_user)):
    return {"members": team.list_members(uid), "invites": team.list_invites(uid)}


@router.post("/team/invites", status_code=201)
def team_invite(body: InviteIn, uid: str = Depends(owner_user)):
    return _team_call(team.create_invite, uid, body.role)


@router.delete("/team/invites/{invite_id}", status_code=204)
def team_revoke_invite(invite_id: str, uid: str = Depends(owner_user)):
    if not team.revoke_invite(uid, invite_id):
        raise HTTPException(404, "invite not found")
    return Response(status_code=204)


@router.patch("/team/members/{account_id}")
def team_set_role(account_id: int, body: RoleIn, uid: str = Depends(owner_user)):
    return _team_call(team.set_role, uid, account_id, body.role)


@router.delete("/team/members/{account_id}", status_code=204)
def team_remove(account_id: int, uid: str = Depends(owner_user)):
    _team_call(team.remove_member, uid, account_id)
    return Response(status_code=204)


@router.post("/team/join", status_code=201)
def team_join(body: JoinIn, p: dict = Depends(current_principal)):
    membership, token = _team_call(team.join, p["account_id"], body.code)
    return {**membership, "token": token}


@router.get("/team/ledgers")
def team_ledgers(p: dict = Depends(current_principal)):
    return {"current": p["user_id"], "ledgers": team.ledgers_for(p["account_id"])}


@router.post("/team/switch")
def team_switch(body: SwitchIn, p: dict = Depends(current_principal)):
    target, token = _team_call(team.switch, p["account_id"], body.user_id)
    return {**target, "token": token}


# ---------------------------------------------------------------- billing (T-042)
def _billing_call(fn, *args):
    try:
        return fn(*args)
    except billing.BillingError as e:
        raise HTTPException(e.code, str(e))


async def _billing_await(coro):
    try:
        return await coro
    except billing.BillingError as e:
        raise HTTPException(e.code, str(e))


class CheckoutIn(BaseModel):
    plan: str = Field(pattern="^(personal|business)$")


@router.get("/billing/plans")
def billing_plans():
    return {"plans": billing.public_plans(), "payments_enabled": billing.payments_enabled()}


@router.get("/billing/status")
def billing_status(uid: str = Depends(current_user)):
    return billing.status(uid)


@router.post("/billing/checkout")
async def billing_checkout(body: CheckoutIn, uid: str = Depends(owner_user)):
    acc = accounts.account_for_ledger(uid)
    url = await _billing_await(billing.create_checkout(uid, body.plan, acc["email"] if acc else ""))
    return {"url": url}


@router.post("/billing/cancel")
async def billing_cancel(uid: str = Depends(owner_user)):
    return await _billing_await(billing.cancel(uid))


@router.post("/billing/webhook")
async def billing_webhook(request: Request, stripe_signature: str = Header(default="")):
    payload = await request.body()
    event = _billing_call(billing.parse_event, payload, stripe_signature)
    return {"result": billing.handle_event(event)}


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
