"""仕切書（スクラップ等の買取伝票）の確認キューと一覧 PDF（T-060）。

流れ: LINE で写真 → 確認待ち（pending）→ パネルで確認・修正 → 承認で 売上 として帳簿に記録。
- 手書きの数字は Tesseract では読めないため、仕切書に限り AI（Claude）で読み取る（ANTHROPIC_API_KEY が
  あるときのみ。2026-11-07 ürün sahibi kararı）。キーがなければ空の明細で受け付け、パネルで手入力する。
- 金額はすべて税込・整数円。数量・単価は小数可（例: 51.5 円/kg）。
"""
from __future__ import annotations

import base64
import io
import json
import re
import time
from datetime import date, datetime, timedelta, timezone

import store

JST = timezone(timedelta(hours=9))
STATUSES = ("pending", "approved", "rejected")
SLIP_MODE_SECONDS = 30 * 60
_mode: dict[str, float] = {}   # user_id → 「仕切書」モードの有効期限（メモリ内、再起動で消える）

# Tablo tanımı: store.SCHEMA ("slips")

# ---------------------------------------------------------------- LINE yönlendirme
SLIP_WORDS = ("仕切", "仕入伝票", "計算書", "盗難品", "買取", "スクラップ")


def start_mode(user_id: str) -> None:
    _mode[user_id] = time.time() + SLIP_MODE_SECONDS


def mode_active(user_id: str) -> bool:
    return _mode.get(user_id, 0) > time.time()


def looks_like_slip(raw_text: str) -> bool:
    """レシートとして読めなかった画像が仕切書らしいか（印刷部分のキーワード）。"""
    t = re.sub(r"\s", "", raw_text or "")
    if any(w in t for w in SLIP_WORDS):
        return True
    return "様" in t and any(w in t for w in ("数量", "単価", "品名", "申し上げます", "合計金額"))


# ---------------------------------------------------------------- doğrulama
def _num(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("¥", "").replace("円", "").replace("kg", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def clean_lines(lines: list[dict]) -> list[dict]:
    out = []
    for ln in lines or []:
        item = str(ln.get("item") or "").strip()[:40]
        qty, price, amount = _num(ln.get("qty")), _num(ln.get("unit_price")), _num(ln.get("amount"))
        if qty is None and amount is None:   # 印刷済みの品名だけの空行（仕入伝票の定型欄）は除外
            continue
        if amount is None and qty is not None and price is not None:
            amount = round_half_up(qty * price)
        out.append({"item": item, "qty": qty, "unit_price": price,
                    "amount": int(round(amount)) if amount is not None else None})
    return out[:30]


def round_half_up(x: float) -> int:
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def issues(slip: dict) -> list[str]:
    """承認前のチェック。空リスト = 問題なし。"""
    out = []
    lines = slip.get("lines") or []
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", slip.get("d") or ""):
        out.append("日付がありません")
    if not (slip.get("issuer") or "").strip():
        out.append("発行元がありません")
    if not lines:
        out.append("明細がありません")
    for i, ln in enumerate(lines, 1):
        if ln.get("amount") is None:
            out.append(f"{i}行目: 金額がありません")
        elif ln.get("qty") is not None and ln.get("unit_price") is not None:
            if abs(ln["qty"] * ln["unit_price"] - ln["amount"]) > 1:
                out.append(f"{i}行目: 数量×単価（{ln['qty'] * ln['unit_price']:,.1f}）と金額（{ln['amount']:,}）が一致しません")
    s = sum(ln["amount"] for ln in lines if ln.get("amount") is not None)
    if lines and int(slip.get("total") or 0) != s:
        out.append(f"明細の合計（{s:,}）と伝票合計（{int(slip.get('total') or 0):,}）が一致しません")
    reg = slip.get("registration_no") or ""
    if reg and not re.fullmatch(r"T\d{13}", reg):
        out.append("登録番号は T + 13桁 です")
    return out


# ---------------------------------------------------------------- AI okuma (yalnızca 仕切書)
AI_PROMPT = """これは日本のスクラップ買取の仕切書（または仕入伝票・計算書）の写真です。数字は手書きです。
次の JSON だけを返してください（説明文なし）:
{"date":"YYYY-MM-DD","issuer":"伝票を発行した会社名（印刷された会社名。『様』の宛名ではない）",
 "registration_no":"T+13桁（印刷されていれば。なければ空文字）",
 "lines":[{"item":"品名","qty":数量(kg、数値),"unit_price":単価(数値、小数可),"amount":金額(整数円)}],
 "total":税込合計(整数円)}
規則: 和暦は西暦に変換（令和8年・R8 = 2026年）。取り消し線で消された数字は無視し、書き直された数字を使う。
金額が空欄の行は出力しない。読めない値は null。品名が印刷済みの行は印刷の品名を使う。"""


async def ai_extract(img: bytes, api_key: str, model: str) -> dict:
    import httpx

    import ai_usage
    img = ai_usage.shrink(img, "slip")
    media = "image/png" if img[:8].startswith(b"\x89PNG") else "image/jpeg"
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 1500, "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(img).decode()}},
                {"type": "text", "text": AI_PROMPT}]}]},
        )
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
        ai_usage.record("slip", r.json().get("usage"))
    return parse_ai(text)


def parse_ai(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        data = {}
    d = str(data.get("date") or "")
    reg = re.sub(r"[^T0-9]", "", str(data.get("registration_no") or "").upper())
    lines = clean_lines(data.get("lines") or [])
    total = _num(data.get("total"))
    if total is None:
        total = sum(ln["amount"] or 0 for ln in lines)
    return {"d": d if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) else "",
            "issuer": str(data.get("issuer") or "").strip()[:60],
            "registration_no": reg if re.fullmatch(r"T\d{13}", reg) else "",
            "lines": lines, "total": int(round(total))}


# ---------------------------------------------------------------- veri
def _now() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _row(r) -> dict:
    s = dict(r)
    s["lines"] = json.loads(s.get("lines") or "[]")
    s["issues"] = issues(s)
    return s


def _snap(con, user_id: str, sid: int) -> dict | None:
    """audit_log 用の行の写し（lines は JSON 文字列のまま）。"""
    r = con.execute("SELECT * FROM slips WHERE id=? AND user_id=?", (sid, user_id)).fetchone()
    return dict(r) if r else None


def history(user_id: str, sid: int) -> list[dict]:
    """仕切書の作成・修正・承認・却下の履歴 (T-065c)。"""
    return store.audit_history(user_id, "slip", sid)


def create(user_id: str, data: dict, image_path: str = "", source: str = "LINE", reader: str = "manual",
           actor: str = "") -> dict:
    lines = clean_lines(data.get("lines") or [])
    with store.tx() as con:
        cur = con.execute(
            """INSERT INTO slips(user_id,status,kind,d,issuer,registration_no,total,lines,image_path,source,reader,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id""",
            (user_id, "pending", data.get("kind") or "inc", data.get("d") or "", data.get("issuer") or "",
             data.get("registration_no") or "", int(data.get("total") or 0), json.dumps(lines, ensure_ascii=False),
             image_path, source, reader, _now(), _now()))
        sid = cur.fetchone()["id"]
        store._audit(con, user_id, "slip", sid, "create", None, _snap(con, user_id, sid), actor)
    return get(user_id, sid)


def get(user_id: str, sid: int) -> dict | None:
    with store.tx() as con:
        r = con.execute("SELECT * FROM slips WHERE id=? AND user_id=?", (sid, user_id)).fetchone()
    return _row(r) if r else None


def list_(user_id: str, status: str = "", date_from: str = "", date_to: str = "") -> list[dict]:
    q, args = "SELECT * FROM slips WHERE user_id=?", [user_id]
    if status:
        q += " AND status=?"
        args.append(status)
    if date_from:
        q += " AND d>=?"
        args.append(date_from)
    if date_to:
        q += " AND d<=?"
        args.append(date_to)
    q += " ORDER BY d, id"
    with store.tx() as con:
        rows = con.execute(q, tuple(args)).fetchall()
    out = [_row(r) for r in rows]
    for s in out:
        s["duplicate_of"] = duplicate_of(user_id, s)
    return out


def duplicate_of(user_id: str, s: dict) -> int | None:
    """同じ発行元・日付・合計の伝票（却下以外）があれば、その id。二重取込の防止。"""
    if not s.get("d") or not s.get("total"):
        return None
    with store.tx() as con:
        r = con.execute(
            "SELECT id FROM slips WHERE user_id=? AND id<>? AND d=? AND issuer=? AND total=? AND status<>'rejected' ORDER BY id LIMIT 1",
            (user_id, s["id"], s["d"], s.get("issuer") or "", int(s["total"]))).fetchone()
    return r["id"] if r else None


def update(user_id: str, sid: int, data: dict, actor: str = "") -> dict:
    s = get(user_id, sid)
    if not s:
        raise KeyError(sid)
    if s["status"] != "pending":
        raise ValueError("承認済み・却下済みの伝票は変更できません")
    fields = {k: data[k] for k in ("d", "issuer", "registration_no", "kind", "note") if k in data}
    if "kind" in fields and fields["kind"] not in ("inc", "exp"):
        raise ValueError("kind")
    if "lines" in data:
        fields["lines"] = json.dumps(clean_lines(data["lines"]), ensure_ascii=False)
    if "total" in data:
        fields["total"] = int(_num(data["total"]) or 0)
    if not fields:
        return s
    sets = ",".join(f"{k}=?" for k in fields) + ",updated_at=?"
    with store.tx() as con:
        before = _snap(con, user_id, sid)
        con.execute(f"UPDATE slips SET {sets} WHERE id=? AND user_id=?", (*fields.values(), _now(), sid, user_id))
        after = _snap(con, user_id, sid)
        before.pop("updated_at", None), after.pop("updated_at", None)       # 時刻だけの差は履歴にしない
        store._audit(con, user_id, "slip", sid, "update", before, after, actor)
    return get(user_id, sid)


def approve(user_id: str, sid: int, actor: str = "") -> dict:
    """確認済みの伝票を帳簿に記録（売上: 売上高 / 仕入: 仕入高）。税込・10%。"""
    s = get(user_id, sid)
    if not s:
        raise KeyError(sid)
    if s["status"] != "pending":
        raise ValueError("この伝票はすでに処理済みです")
    if s["issues"]:
        raise ValueError(" / ".join(s["issues"]))
    items = "・".join(ln["item"] for ln in s["lines"] if ln["item"])[:60]
    entry_id = store.add_entry(user_id, {
        "date": s["d"], "kind": s["kind"], "store": s["issuer"], "amount": int(s["total"]),
        "category": "売上高" if s["kind"] == "inc" else "仕入高", "rate": 10,
        "invoice_no": s["registration_no"],
    }, image_path=s["image_path"], source=f"仕切書:{items}" if items else "仕切書", actor=actor)
    with store.tx() as con:
        before = _snap(con, user_id, sid)
        con.execute("UPDATE slips SET status='approved', entry_id=?, updated_at=? WHERE id=? AND user_id=?",
                    (entry_id, _now(), sid, user_id))
        after = _snap(con, user_id, sid)
        before.pop("updated_at", None), after.pop("updated_at", None)
        store._audit(con, user_id, "slip", sid, "update", before, after, actor)
    return get(user_id, sid)


def reject(user_id: str, sid: int, actor: str = "") -> dict:
    s = get(user_id, sid)
    if not s:
        raise KeyError(sid)
    if s["status"] != "pending":
        raise ValueError("この伝票はすでに処理済みです")
    with store.tx() as con:
        before = _snap(con, user_id, sid)
        con.execute("UPDATE slips SET status='rejected', updated_at=? WHERE id=? AND user_id=?", (_now(), sid, user_id))
        after = _snap(con, user_id, sid)
        before.pop("updated_at", None), after.pop("updated_at", None)
        store._audit(con, user_id, "slip", sid, "update", before, after, actor)
    return get(user_id, sid)


def line_reply(s: dict) -> str:
    """LINE への受付メッセージ（日本語。i18n が翻訳）。"""
    head = f"仕切書を受け付けました（確認待ち）\n{s['issuer'] or '発行元未読取'}・{s['d'] or '日付未読取'}"
    if s["lines"]:
        body = "\n".join(f"・{ln['item'] or '品名'} {_fmt_q(ln['qty'])}kg × {_fmt_p(ln['unit_price'])} = ¥{(ln['amount'] or 0):,}"
                         for ln in s["lines"][:8])
        head += f"\n{body}\n合計 ¥{int(s['total']):,}"
    else:
        head += "\n金額はパネルで入力してください"
    warn = "\n⚠️ " + s["issues"][0] if s["issues"] and s["lines"] else ""
    return head + warn + "\n\n「パネル」と送ると確認画面のリンクが届きます。承認すると売上として記録されます"


def _fmt_q(v) -> str:
    return "—" if v is None else (f"{v:,.0f}" if float(v).is_integer() else f"{v:,.1f}")


def _fmt_p(v) -> str:
    return "—" if v is None else (f"{v:,.0f}" if float(v).is_integer() else f"{v:,.1f}")


# ---------------------------------------------------------------- 一覧 PDF
def render_list_pdf(slips_: list[dict], title_year: str, business_name: str = "") -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    from invoices import _register_font

    font = _register_font(pdfmetrics, UnicodeCIDFont)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"仕切書一覧 {title_year}")
    W, H = A4
    L, R = 14 * mm, W - 14 * mm
    cols = [L, L + 11 * mm, L + 35 * mm, L + 62 * mm, None, None, None, None]
    right = {"qty": L + 120 * mm, "price": L + 140 * mm, "amount": L + 162 * mm, "total": R}
    dup_free = not any(s.get("duplicate_of") for s in slips_)

    def t(x, y, s, size=9, r=False, bold=False):
        c.setFont(font, size + (0.5 if bold else 0))
        (c.drawRightString if r else c.drawString)(x, y, s)

    def header(y):
        c.setFillGray(0.92)
        c.rect(L, y - 2.2 * mm, R - L, 7 * mm, stroke=0, fill=1)
        c.setFillGray(0)
        for x, s in ((cols[0], "No"), (cols[1], "日付"), (cols[2], "発行元"), (cols[3], "品名")):
            t(x + 1 * mm, y, s, 9)
        t(right["qty"], y, "数量(kg)", 9, r=True)
        t(right["price"], y, "単価", 9, r=True)
        t(right["amount"], y, "金額", 9, r=True)
        t(right["total"], y, "伝票合計", 9, r=True)
        return y - 7.5 * mm

    y = H - 20 * mm
    t(L, y, f"仕切書一覧（{title_year}）", 15, bold=True)
    if business_name:
        t(R, y, business_name, 9, r=True)
    y -= 7 * mm
    t(L, y, f"伝票 {len(slips_)} 件・{'重複なし' if dup_free else '重複の可能性あり（※）'}・金額は税込", 9)
    y -= 9 * mm
    y = header(y)
    qty_sum = amt_sum = 0
    for no, s in enumerate(slips_, 1):
        lines = s["lines"] or [{"item": "", "qty": None, "unit_price": None, "amount": None}]
        need = 6 * mm * len(lines) + 2 * mm
        if y - need < 22 * mm:
            c.showPage()
            y = header(H - 20 * mm)
        top = y
        for i, ln in enumerate(lines):
            if i == 0:
                t(cols[0] + 1 * mm, y, str(no) + ("※" if s.get("duplicate_of") else ""))
                t(cols[1] + 1 * mm, y, s["d"])
                t(cols[2] + 1 * mm, y, (s["issuer"] or "").replace("株式会社", "").replace("(株)", "").replace("㈱", "").strip()[:9])
                t(right["total"], y, f"{int(s['total']):,}", r=True)
            t(cols[3] + 1 * mm, y, (ln["item"] or "")[:10])
            if ln["qty"] is not None:
                t(right["qty"], y, _fmt_q(ln["qty"]), r=True)
                qty_sum += ln["qty"]
            if ln["unit_price"] is not None:
                t(right["price"], y, _fmt_p(ln["unit_price"]), r=True)
            if ln["amount"] is not None:
                t(right["amount"], y, f"{ln['amount']:,}", r=True)
            y -= 6 * mm
        amt_sum += int(s["total"])
        c.setStrokeGray(0.8)
        c.line(L, y + 3.6 * mm, R, y + 3.6 * mm)
        del top
    y -= 2 * mm
    c.setStrokeGray(0)
    c.line(L, y + 4.5 * mm, R, y + 4.5 * mm)
    t(cols[3] + 1 * mm, y, "合計", 10, bold=True)
    t(right["qty"], y, _fmt_q(qty_sum), 10, r=True, bold=True)
    t(right["total"], y, f"{amt_sum:,}", 10, r=True, bold=True)
    y -= 9 * mm
    if not dup_free:
        t(L, y, "※ 同じ発行元・日付・合計の伝票があります。二重計上でないか確認してください。", 8)
        y -= 5 * mm
    t(L, y, f"作成: てがる会計 {date.today().isoformat()}", 7.5)
    c.save()
    return buf.getvalue()
