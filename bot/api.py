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
import ai_usage
import archive
import bank_csv
import billing
import companies
import counterparties as cpmod
import deletion
import export
import invoices as inv_mod
import passbook
import ratelimit
import reports
import slips
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


def writer_principal(p: dict = Depends(current_principal)) -> dict:
    """Muhasebe verisi yazma: owner / accountant (principal döner; audit için kim yaptı)."""
    if p["role"] not in team.WRITE_ROLES:
        raise HTTPException(403, "閲覧専用のメンバーは編集できません。")
    return p


def writer_user(p: dict = Depends(writer_principal)) -> str:
    """Muhasebe verisi yazma: owner / accountant."""
    return p["user_id"]


def actor_of(p: dict) -> str:
    """audit_log.actor: `WEB:<rol>:<hesap id>` (0 = hesapsız sahip token'ı, ör. LINE 「パネル」)."""
    return f"WEB:{p.get('role', '')}:{int(p.get('account_id') or 0)}"


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
    image_path: str = Field("", max_length=120)   # T-034: /receipts/ocr が返した画像（同じ帳簿のもののみ）


def _img_tag(uid: str) -> str:
    """パネルで読み取った画像のキーに入れる帳簿ごとの印（他の帳簿の画像を紐付けられないように）。"""
    import hashlib
    return hashlib.sha256(("img:" + uid).encode()).hexdigest()[:12]


def _new_image_key(uid: str) -> str:
    import secrets
    import time
    return f"receipts/w{_img_tag(uid)}_{int(time.time() * 1000)}_{secrets.token_hex(3)}.jpg"


def _image_key_ok(uid: str, key: str) -> bool:
    return bool(re.fullmatch(rf"receipts/w{_img_tag(uid)}_\d+_[0-9a-f]{{6}}\.jpg", key))


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
def create_entry(body: EntryIn, p: dict = Depends(writer_principal)):
    uid = p["user_id"]
    _valid_date(body.date, "date")
    if body.rate not in (10, 8, 0):
        raise HTTPException(400, "rate must be 10, 8 or 0")
    if body.category not in CATEGORIES:
        raise HTTPException(400, f"category must be one of {CATEGORIES}")
    if body.invoice_no and not re.fullmatch(r"T\d{13}", body.invoice_no):
        raise HTTPException(400, "invoice_no must be T + 13 digits")
    e = body.model_dump()
    image_path = e.pop("image_path", "")
    if image_path and not _image_key_ok(uid, image_path):
        raise HTTPException(400, "invalid image_path")
    if e["kind"] == "exp":
        _billing_call(billing.check_limit, uid, "receipts")
    eid = store.add_entry(uid, e, image_path=image_path, source="WEB", actor=actor_of(p))
    return {"id": eid, **e}


class EntryPatch(BaseModel):
    date: str | None = None
    store: str | None = Field(default=None, min_length=1, max_length=100)
    amount: int | None = Field(default=None, gt=0, lt=MAX_ENTRY_AMOUNT)
    category: str | None = None
    rate: int | None = None
    invoice_no: str | None = None


@router.patch("/entries/{entry_id}")
def patch_entry(entry_id: int, body: EntryPatch, p: dict = Depends(writer_principal)):
    uid = p["user_id"]
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
    return store.update_entry(uid, entry_id, actor=actor_of(p), **f)


@router.delete("/entries/{entry_id}", status_code=204)
def remove_entry(entry_id: int, p: dict = Depends(writer_principal)):
    if not store.delete_entry(p["user_id"], entry_id, actor=actor_of(p)):
        raise HTTPException(404, "entry not found")
    return Response(status_code=204)


def with_actors(p: dict, rows: list[dict]) -> list[dict]:
    """audit satırlarına kim yaptı bilgisi (T-065b).

    actor_kind: web / line / bank / whatsapp …; actor_role: owner / accountant / viewer (web);
    actor_email: yalnızca sahip (üye listesini zaten görür) veya kişinin kendisi için, ve hesap hâlâ
    bu defterdeyse; actor_former: hesap artık defterde değil. Üye e-postaları owner dışına açılmaz
    (`/team/members` owner'a özel olduğu için)."""
    emails = {m["account_id"]: m["email"] for m in team.list_members(p["user_id"])}
    me = int(p.get("account_id") or 0)
    out = []
    for r in rows:
        actor = r.get("actor") or ""
        parts = actor.split(":")
        info = {"actor_kind": (parts[0] or "unknown").lower(), "actor_role": "", "actor_email": None,
                "actor_is_me": False, "actor_former": False}
        if parts[0] == "WEB" and len(parts) == 3:
            acc = int(parts[2]) if parts[2].isdigit() else 0
            info["actor_role"] = parts[1]
            info["actor_is_me"] = bool(acc) and acc == me
            if acc and acc not in emails:
                info["actor_former"] = True
            elif acc and (p["role"] == "owner" or info["actor_is_me"]):
                info["actor_email"] = emails[acc]
        out.append({**r, **info})
    return out


@router.get("/entries/{entry_id}/history")
def entry_history(entry_id: int, p: dict = Depends(current_principal)):
    """訂正・削除の履歴 (T-065): oluşturma/düzeltme/silme, önce/sonra görüntüsüyle (eskiden yeniye).
    Silinmiş kayıtlar için de döner; geçmişi olmayan kayıt 404. Kim yaptı: `with_actors` (T-065b)."""
    uid = p["user_id"]
    h = store.audit_history(uid, "entry", entry_id)
    if not h and not store.get_entry(uid, entry_id):
        raise HTTPException(404, "entry not found")
    return with_actors(p, h)


@router.get("/bank/{tx_id}/history")
def bank_tx_history(tx_id: int, p: dict = Depends(current_principal)):
    """銀行明細の修正・確認の履歴 (T-065b). Hareket yoksa 404; düzeltilmemiş hareket → []."""
    if not store.get_bank_tx(p["user_id"], tx_id):
        raise HTTPException(404, "transaction not found")
    return with_actors(p, store.audit_history(p["user_id"], "bank_tx", tx_id))


@router.get("/audit")
def audit_list(entity: str | None = None, action: str | None = None,
               limit: int = Query(100, ge=1, le=1000), p: dict = Depends(current_principal)):
    """Defterin son değişiklikleri (yeniden eskiye). entity ∈ entry / invoice / bank_tx, action ∈ create / update / delete."""
    uid = p["user_id"]
    if entity and entity not in store.AUDIT_ENTITIES:
        raise HTTPException(400, f"entity must be one of {store.AUDIT_ENTITIES}")
    if action and action not in ("create", "update", "delete"):
        raise HTTPException(400, "action must be create, update or delete")
    return with_actors(p, store.audit_recent(uid, entity=entity, action=action, limit=limit))


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
    ai_usage.current_user.set(uid)
    reader = store.get_receipt_reader(uid)
    result = await (app_mod.ocr_receipt(raw, reader) if reader else app_mod.ocr_receipt(raw))
    # T-034: 画像を保存（電帳法: 領収書の画像を記録と紐付けて保存）。保存失敗は読み取り結果を妨げない
    import storage
    image_path = _new_image_key(uid)
    try:
        await storage.put(image_path, raw, "image/jpeg")
    except Exception as ex:  # noqa: BLE001
        print("receipt image store error", type(ex).__name__)
        image_path = ""
    if isinstance(result, dict):
        return {"ok": False, "error": result.get("error"), "partial": result.get("partial", {}), "entries": [],
                "image_path": image_path}
    return {"ok": True, "entries": result, "image_path": image_path}


@router.get("/entries/{entry_id}/image")
async def entry_image(entry_id: int, uid: str = Depends(current_user)):
    """記録に紐付いた領収書の画像（LINE・パネルで読み取ったもの）。"""
    import storage
    e = store.get_entry(uid, entry_id)
    if not e or not e.get("image_path"):
        raise HTTPException(404, "image not found")
    data = await storage.get(e["image_path"])
    if not data:
        raise HTTPException(404, "image not found（保存期間外または移行前の画像）")
    media = "image/png" if data[:8].startswith(b"\x89PNG") else "image/jpeg"
    return Response(data, media_type=media, headers={"Cache-Control": "private, max-age=300"})



# ---------------------------------------------------------------- 仕切書 (T-060)
class SlipLine(BaseModel):
    item: str = Field("", max_length=40)
    qty: float | None = Field(None, ge=0, le=10_000_000)
    unit_price: float | None = Field(None, ge=0, le=100_000_000)
    amount: int | None = Field(None, ge=0, lt=MAX_ENTRY_AMOUNT)


class SlipPatch(BaseModel):
    d: str | None = None
    issuer: str | None = Field(None, max_length=60)
    registration_no: str | None = Field(None, max_length=14)
    kind: str | None = Field(None, pattern="^(inc|exp)$")
    total: int | None = Field(None, ge=0, lt=MAX_ENTRY_AMOUNT)
    note: str | None = Field(None, max_length=200)
    lines: list[SlipLine] | None = Field(None, max_length=30)


def _slip_or_404(uid: str, sid: int) -> dict:
    s = slips.get(uid, sid)
    if not s:
        raise HTTPException(404, "slip not found")
    s["duplicate_of"] = slips.duplicate_of(uid, s)
    return s


@router.get("/slips")
def slip_list(status: str = Query("", pattern="^(|pending|approved|rejected)$"),
              date_from: str = "", date_to: str = "", uid: str = Depends(current_user)):
    rows = slips.list_(uid, status, date_from and _valid_date(date_from, "date_from"),
                       date_to and _valid_date(date_to, "date_to"))
    counts = {st: 0 for st in slips.STATUSES}
    for r in slips.list_(uid):
        counts[r["status"]] += 1
    return {"slips": rows, "counts": counts, "ai_enabled": bool(os.environ.get("ANTHROPIC_API_KEY"))}


@router.get("/slips/{sid}")
def slip_get(sid: int, uid: str = Depends(current_user)):
    return _slip_or_404(uid, sid)


@router.get("/slips/{sid}/image")
async def slip_image(sid: int, uid: str = Depends(current_user)):
    import storage
    s = _slip_or_404(uid, sid)
    data = await storage.get(s["image_path"]) if s["image_path"] else None
    if not data:
        raise HTTPException(404, "image not found")
    media = "image/png" if data[:8].startswith(b"\x89PNG") else "image/jpeg"
    return Response(data, media_type=media, headers={"Cache-Control": "private, max-age=300"})


@router.patch("/slips/{sid}")
def slip_patch(sid: int, body: SlipPatch, uid: str = Depends(writer_user)):
    _slip_or_404(uid, sid)
    data = body.model_dump(exclude_none=True)
    if "d" in data:
        _valid_date(data["d"], "d")
    if "lines" in data:
        data["lines"] = [ln for ln in data["lines"]]
    try:
        return slips.update(uid, sid, data)
    except ValueError as ex:
        raise HTTPException(409, str(ex))


@router.post("/slips/{sid}/approve")
def slip_approve(sid: int, uid: str = Depends(writer_user)):
    _slip_or_404(uid, sid)
    try:
        return slips.approve(uid, sid)
    except ValueError as ex:
        raise HTTPException(409, str(ex))


@router.post("/slips/{sid}/reject")
def slip_reject(sid: int, uid: str = Depends(writer_user)):
    _slip_or_404(uid, sid)
    try:
        return slips.reject(uid, sid)
    except ValueError as ex:
        raise HTTPException(409, str(ex))


@router.post("/slips/upload", status_code=201, dependencies=[Depends(ratelimit.limiter("ocr"))])
async def slip_upload(request: Request, uid: str = Depends(writer_user)):
    """パネルから仕切書の画像をアップロード → 確認待ちに追加（AI キーがあれば読み取り）。"""
    raw = await _body(request)
    import app as app_mod
    ai_usage.current_user.set(uid)
    return await app_mod.receive_slip(uid, raw, f"web{int(__import__('time').time())}", "web")


@router.get("/reports/slips.pdf")
def slips_pdf(date_from: str = Query(...), date_to: str = Query(...),
              status: str = Query("approved", pattern="^(approved|pending|all)$"), uid: str = Depends(current_user)):
    _valid_date(date_from, "date_from")
    _valid_date(date_to, "date_to")
    rows = slips.list_(uid, "" if status == "all" else status, date_from, date_to)
    rows = [r for r in rows if r["status"] != "rejected"]
    label = date_from[:4] + "年" if date_from[:4] == date_to[:4] and date_from[5:] == "01-01" and date_to[5:] == "12-31" \
        else f"{date_from}〜{date_to}"
    pdf = slips.render_list_pdf(rows, label, store.get_profile(uid).get("business_name") or "")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="slips-{date_from}-{date_to}.pdf"'})

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
def bank_match(body: MatchIn, p: dict = Depends(writer_principal)):
    uid = p["user_id"]
    t = store.get_bank_tx(uid, body.tx_id)
    inv = store.get_invoice(uid, body.invoice_no)
    if not t or not inv:
        raise HTTPException(404, "transaction or invoice not found")
    if t["invoice_no"] or inv["status"] == "paid":
        raise HTTPException(409, "already matched")
    if t["amount"] != inv["total"]:
        raise HTTPException(400, "amount does not match invoice total")
    paid = store.mark_invoice_paid(uid, inv["no"], t["d"], actor=actor_of(p))
    store.link_bank_tx(uid, t["id"], invoice_no=inv["no"], actor=actor_of(p))
    return paid


class ToEntryIn(BaseModel):
    category: str
    rate: int = 10
    invoice_no: str = ""


@router.post("/bank/{tx_id}/entry", status_code=201)
def bank_to_entry(tx_id: int, body: ToEntryIn, p: dict = Depends(writer_principal)):
    """出金 hareketini 経費 olarak kaydet (口座振替: 家賃, 通信費 vb.)."""
    uid = p["user_id"]
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
    eid = store.add_entry(uid, e, source="BANK", actor=actor_of(p))
    store.link_bank_tx(uid, tx_id, entry_id=eid, actor=actor_of(p))
    return {"id": eid, **e}



# ---------------------------------------------------------------- 通帳取込・取引先照合 (T-061/T-062)
@router.post("/bank/passbook", dependencies=[Depends(ratelimit.limiter("ocr"))])
async def bank_passbook(request: Request, account: str = "", uid: str = Depends(writer_user)):
    """通帳のスキャン（PDF / 写真）→ AI で明細を読み取り bank_tx に取込（重複は除外）。"""
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "empty body")
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(413, "25MB以下のファイルにしてください")
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise HTTPException(503, "通帳の読み取りには AI の設定（ANTHROPIC_API_KEY）が必要です")
    ai_usage.current_user.set(uid)
    parsed = await passbook.ai_read(raw, key, os.environ.get("OCR_MODEL", "claude-sonnet-5-5"))
    return passbook.import_rows(uid, parsed, account)


def _review_rows(uid: str, date_from: str = "", date_to: str = "") -> list[dict]:
    cps, aliases = cpmod.all_(uid), cpmod.alias_map(uid)
    by_id = {c["id"]: c for c in cps}
    out = []
    for t in sorted(store.list_bank_tx(uid, 5000), key=lambda r: (r["d"], r["id"])):
        if (date_from and t["d"] < date_from) or (date_to and t["d"] > date_to):
            continue
        m = cpmod.match(uid, t["description"], cps, aliases)
        cp = by_id.get(t.get("counterparty_id")) if t.get("counterparty_id") else m["counterparty"]
        done = t.get("status") in ("confirmed", "excluded") or bool(t["entry_id"]) or bool(t["invoice_no"])
        out.append({
            "id": t["id"], "d": t["d"], "description": t["description"], "amount": t["amount"], "balance": t["balance"],
            "account": t.get("account") or "", "src": t.get("src") or "csv", "balance_ok": t.get("balance_ok"),
            "status": t.get("status") or ("confirmed" if done else ""), "entry_id": t["entry_id"],
            "category": t.get("category") or (cp or {}).get("category") or m["category"],
            "counterparty": {k: cp.get(k, "") for k in ("id", "name", "registration_no", "corporate_number", "invoice_status", "invoice_name")} if cp else None,
            "match": m["how"], "book": m["book"] if not cp else True,
            "candidates": [{"id": c["id"], "name": c["name"]} for c in m.get("candidates", [])],
        })
    return out


@router.get("/bank/review")
def bank_review(date_from: str = "", date_to: str = "", uid: str = Depends(current_user)):
    rows = _review_rows(uid, date_from and _valid_date(date_from, "date_from"), date_to and _valid_date(date_to, "date_to"))
    return {"rows": rows, "counts": {
        "total": len(rows), "open": sum(1 for r in rows if not r["status"]),
        "unknown": sum(1 for r in rows if not r["status"] and not r["counterparty"] and r["match"] == ""),
        "balance_errors": sum(1 for r in rows if r["balance_ok"] == 0)},
        "nta_enabled": bool(os.environ.get("NTA_APP_ID")), "ai_enabled": bool(os.environ.get("ANTHROPIC_API_KEY"))}


class ConfirmIn(BaseModel):
    book: bool = True
    category: str = Field("", max_length=20)
    counterparty_name: str = Field("", max_length=80)
    registration_no: str = Field("", max_length=14)
    rate: int | None = None


@router.post("/bank/{tx_id}/confirm")
def bank_confirm(tx_id: int, body: ConfirmIn, p: dict = Depends(writer_principal)):
    """確認: 記帳する（売上/経費として entries へ）か、記帳しない（現金引出・振替など）。取引先は覚える。"""
    uid = p["user_id"]
    t = store.get_bank_tx(uid, tx_id)
    if not t:
        raise HTTPException(404, "transaction not found")
    if t.get("status") in ("confirmed", "excluded") or t["entry_id"] or t["invoice_no"]:
        raise HTTPException(409, "already recorded")
    category = cpmod.normalize_category(body.category)
    cp = None
    if body.counterparty_name.strip():
        try:
            cp = cpmod.upsert(uid, name=body.counterparty_name, registration_no=body.registration_no, category=category)
        except ValueError as ex:
            raise HTTPException(400, str(ex))
        cpmod.learn_alias(uid, cp["id"], cpmod.key_from_description(t["description"]))
    entry_id = None
    if body.book and category not in cpmod.TRANSFER_CATEGORIES:
        if not category:
            raise HTTPException(400, "勘定科目を選んでください")
        rate = body.rate if body.rate is not None else (0 if category == "受取利息" else 10)
        if rate not in (10, 8, 0):
            raise HTTPException(400, "rate must be 10, 8 or 0")
        amount = abs(int(t["amount"]))
        if amount >= store.MAX_ENTRY_AMOUNT:
            raise HTTPException(400, f"amount must be < {store.MAX_ENTRY_AMOUNT}")
        entry_id = store.add_entry(uid, {
            "date": t["d"], "kind": "inc" if t["amount"] > 0 else "exp",
            "store": (cp["name"] if cp else t["description"])[:100], "amount": amount, "category": category,
            "rate": rate, "invoice_no": (cp or {}).get("registration_no") or "",
        }, source="BANK", actor=actor_of(p))
    fix = {"status": "confirmed" if entry_id else "excluded", "category": category,
           "counterparty_id": cp["id"] if cp else None}
    if entry_id:
        fix["entry_id"] = entry_id
    store.update_bank_tx(uid, tx_id, actor=actor_of(p), **fix)
    return {"id": tx_id, "status": "confirmed" if entry_id else "excluded", "entry_id": entry_id}


class TxFix(BaseModel):
    amount: int = Field(..., gt=-10_000_000_000, lt=10_000_000_000)
    balance: int | None = None


@router.patch("/bank/{tx_id}")
def bank_fix(tx_id: int, body: TxFix, p: dict = Depends(writer_principal)):
    """通帳の読み取り誤りを修正（未確認の行のみ）。修正後に同じ口座の残高チェックをやり直す。修正は履歴に残る (T-065b)。"""
    uid = p["user_id"]
    t = store.get_bank_tx(uid, tx_id)
    if not t:
        raise HTTPException(404, "transaction not found")
    if t.get("status") or t["entry_id"] or t["invoice_no"]:
        raise HTTPException(409, "already recorded")
    fix = {"amount": body.amount} | ({"balance": body.balance} if body.balance is not None else {})
    store.update_bank_tx(uid, tx_id, actor=actor_of(p), **fix)
    _recheck_balances(uid, t.get("account") or "")
    return store.get_bank_tx(uid, tx_id)


def _recheck_balances(uid: str, account: str) -> None:
    rows = [r for r in sorted(store.list_bank_tx(uid, 5000), key=lambda r: (r["d"], r["id"]))
            if (r.get("account") or "") == account and r.get("src") == "passbook"]
    prev = None
    with store.tx() as con:
        for r in rows:
            ok = None if prev is None or r["balance"] is None else int(prev + r["amount"] == r["balance"])
            con.execute("UPDATE bank_tx SET balance_ok=? WHERE id=?", (ok if ok is not None else r.get("balance_ok"), r["id"]))
            if r["balance"] is not None:
                prev = r["balance"]


class BulkIn(BaseModel):
    ids: list[int] = Field(..., max_length=2000)


@router.post("/bank/confirm-matched")
def bank_confirm_matched(body: BulkIn, p: dict = Depends(writer_principal)):
    """自動で取引先・科目が決まった行をまとめて確定（残高チェック NG の行は除く）。"""
    uid = p["user_id"]
    rows = {r["id"]: r for r in _review_rows(uid)}
    done, skipped = 0, 0
    for i in body.ids:
        r = rows.get(i)
        if not r or r["status"] or r["balance_ok"] == 0 or not r["category"] or (r["match"] == "" and not r["counterparty"]):
            skipped += 1
            continue
        cp = r["counterparty"] or {}
        bank_confirm(i, ConfirmIn(book=r["book"], category=r["category"], counterparty_name=cp.get("name", ""),
                                  registration_no=cp.get("registration_no", "")), p)
        done += 1
    return {"confirmed": done, "skipped": skipped}


@router.get("/counterparties")
def cp_list(uid: str = Depends(current_user)):
    return {"counterparties": cpmod.all_(uid), "nta_enabled": bool(os.environ.get("NTA_APP_ID"))}


class CpIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    furigana: str = Field("", max_length=120)
    registration_no: str = Field("", max_length=14)
    category: str = Field("", max_length=20)


@router.post("/counterparties", status_code=201)
def cp_upsert(body: CpIn, uid: str = Depends(writer_user)):
    try:
        return cpmod.upsert(uid, name=body.name, furigana=body.furigana, registration_no=body.registration_no,
                            category=body.category)
    except ValueError as ex:
        raise HTTPException(400, str(ex))


@router.post("/counterparties/import")
async def cp_import(request: Request, uid: str = Depends(writer_user)):
    """既存の通帳整理表（Excel）から取引先・登録番号・科目を取り込む。"""
    raw = await _body(request)
    try:
        return cpmod.import_excel(uid, raw)
    except Exception as ex:  # noqa: BLE001  壊れた / 別形式のファイル
        raise HTTPException(400, f"Excel を読み込めませんでした（{type(ex).__name__}）")


@router.post("/counterparties/verify")
async def cp_verify(uid: str = Depends(writer_user)):
    """登録番号の確認: 形式（チェックデジット）は常に、国税庁 公表サイトは NTA_INVOICE_APP_ID（なければ NTA_APP_ID）があるとき。"""
    cps = [c for c in cpmod.all_(uid) if c["registration_no"]]
    app_id = os.environ.get("NTA_INVOICE_APP_ID") or os.environ.get("NTA_APP_ID", "")
    online: dict[str, dict] = {}
    good = [c["registration_no"] for c in cps if not cpmod.format_status(c["registration_no"])]
    if app_id and good:
        try:
            online = await cpmod.invoice_lookup(app_id, sorted(set(good)))
        except Exception as ex:  # noqa: BLE001
            raise HTTPException(502, f"インボイス公表サイトに接続できませんでした（{type(ex).__name__}）")
    counts = {"valid": 0, "expired": 0, "notfound": 0, "format_ng": 0, "unchecked": 0}
    for c in cps:
        st = cpmod.format_status(c["registration_no"])
        name = ""
        if not st and c["registration_no"] in online:
            st, name = online[c["registration_no"]]["status"], online[c["registration_no"]]["name"]
        cpmod.save_invoice_status(uid, c["id"], st, name)
        counts[st or "unchecked"] += 1
    return {"checked": len(cps), "online": bool(app_id), **counts}


@router.get("/counterparties/lookup")
async def cp_lookup(desc: str = Query(..., min_length=1, max_length=120), uid: str = Depends(current_user)):
    """摘要のカナで国税庁 法人番号 Web-API を検索（NTA_APP_ID が設定されているとき）。"""
    app_id = os.environ.get("NTA_APP_ID", "")
    if not app_id:
        raise HTTPException(503, "国税庁 Web-API のアプリケーションID（NTA_APP_ID）が未設定です")
    try:
        found = await cpmod.nta_search(app_id, desc)
    except Exception as ex:  # noqa: BLE001
        raise HTTPException(502, f"国税庁 Web-API に接続できませんでした（{type(ex).__name__}）")
    for f in found:
        f["registration_no_guess"] = "T" + f["corporate_number"]   # 法人は 登録番号 = T + 法人番号（登録済みの場合）
    return {"results": found}


@router.get("/reports/bank.xlsx")
def bank_xlsx(date_from: str = Query(...), date_to: str = Query(...), uid: str = Depends(current_user)):
    """通帳整理表（Excel）: 日付・支出・入金・勘定科目・取引先・残高・登録番号・状態。"""
    import io as _io

    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    _valid_date(date_from, "date_from")
    _valid_date(date_to, "date_to")
    rows = _review_rows(uid, date_from, date_to)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "通帳"
    head = ["日付", "支出", "入金", "勘定科目", "取引先", "摘要（通帳）", "残高", "インボイス登録番号", "状態", "残高チェック", "口座"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(name="Arial", bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E293B")
        c.alignment = Alignment(horizontal="center")
    for r in rows:
        cp = r["counterparty"] or {}
        ws.append([date.fromisoformat(r["d"]), -r["amount"] if r["amount"] < 0 else None, r["amount"] if r["amount"] > 0 else None,
                   r["category"], cp.get("name", ""), r["description"], r["balance"], cp.get("registration_no", ""),
                   {"confirmed": "記帳済", "excluded": "記帳しない", "": "未確認"}[r["status"]],
                   {1: "OK", 0: "NG"}.get(r["balance_ok"], ""), r["account"]])
    n = ws.max_row
    ws.append(["合計", f"=SUM(B2:B{n})", f"=SUM(C2:C{n})"])
    for row in ws.iter_rows(min_row=2):
        row[0].number_format = "yyyy-mm-dd"
        for i in (1, 2, 6):
            row[i].number_format = "#,##0"
        for c in row:
            if c.font.name != "Arial":
                c.font = Font(name="Arial", bold=c.row == ws.max_row)
    for col, w in zip("ABCDEFGHIJK", (12, 12, 12, 12, 28, 24, 13, 18, 10, 10, 18)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    buf = _io.BytesIO()
    wb.save(buf)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="bank-{date_from}-{date_to}.xlsx"'})

# ---------------------------------------------------------------- AI 読み取りの設定と概算料金
class AiSettingsIn(BaseModel):
    receipt_reader: str = Field(..., pattern="^(|ocr|ai|auto)$")


def _ai_settings(uid: str) -> dict:
    return {"receipt_reader": store.get_receipt_reader(uid), "server_default": os.environ.get("OCR_ENGINE", "tesseract"),
            "ai_available": bool(os.environ.get("ANTHROPIC_API_KEY")), "per_unit": ai_usage.per_unit_jpy(uid),
            "month": ai_usage.month_summary(uid), "prices": ai_usage.prices()}


@router.get("/settings/ai")
def ai_settings(uid: str = Depends(current_user)):
    return _ai_settings(uid)


@router.put("/settings/ai")
def ai_settings_put(body: AiSettingsIn, uid: str = Depends(writer_user)):
    if body.receipt_reader in ("ai", "auto") and not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(409, "AI 読み取りはサーバーに ANTHROPIC_API_KEY が設定されてから選べます")
    store.set_receipt_reader(uid, body.receipt_reader)
    return _ai_settings(uid)


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
def create_invoice(body: InvoiceIn, p: dict = Depends(writer_principal)):
    uid = p["user_id"]
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
    return store.insert_invoice(uid, inv, actor=actor_of(p))


@router.post("/invoices/{no}/paid")
def pay_invoice(no: str, paid_on: str | None = None, p: dict = Depends(writer_principal)):
    paid_on = _valid_date(paid_on, "paid_on") if paid_on else store.today().isoformat()
    inv = store.mark_invoice_paid(p["user_id"], no, paid_on, actor=actor_of(p))
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
    if blue not in it.blue_options(year):
        raise HTTPException(400, f"blue must be one of {', '.join(map(str, it.blue_options(year)))} for {year}")
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


# ---------------------------------------------------------------- hesap silme talebi (T-046b)
def _deletion_view(uid: str) -> dict:
    return {"request": deletion.get(uid), "billing_active": deletion.billing_active(uid)}


@router.get("/account/delete-request")
def get_delete_request(uid: str = Depends(owner_user)):
    return _deletion_view(uid)


@router.post("/account/delete-request", status_code=202)
def post_delete_request(p: dict = Depends(current_principal), uid: str = Depends(owner_user)):
    """Talebi kaydeder (veri hemen silinmez). Tekrar çağrı idempotent: aynı talep, `created: false`."""
    _, created = deletion.request(uid, p["account_id"])
    return {**_deletion_view(uid), "created": created}


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


class CompanyIn(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=100)


@router.post("/companies", status_code=201)
def company_create(body: CompanyIn, p: dict = Depends(current_principal)):
    """Hesaba yeni şirket (事業所) ekler ve o şirkete geçiş token'ı döner. Fiyat kuralı: Q-16 (şimdilik sınırsız)."""
    try:
        c = companies.create(p["account_id"], body.business_name)
    except companies.CompanyError as e:
        raise HTTPException(e.code, str(e))
    target, token = _team_call(team.switch, p["account_id"], c["user_id"])
    return {**c, "token": token}


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


@router.get("/admin/deletion-requests")
def admin_deletion_requests(x_admin_key: str = Header(default="")):
    """T-046b: bekleyen hesap silme talepleri (operatör; docs/OPERATIONS.md)."""
    if not _admin_ok(x_admin_key):
        raise HTTPException(401, "admin key required")
    return {"requests": deletion.list_pending()}


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
