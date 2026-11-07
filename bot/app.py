"""
てがる会計 LINE Bot — LINE Messaging API webhook sunucusu.

Akış:
  LINE kullanıcısı mesaj / fiş fotoğrafı gönderir
  → /callback (imza doğrulanır, 200 hemen döner)
  → arka planda: metin ise parser, fotoğraf ise OCR ile fiş okuma
    (OCR LINE_REPLY_WAIT_SEC (8 sn) içinde bitmezse önce 「読み取り中」 reply, sonuç push)
  → SQLite'a kayıt → LINE'a hızlı yanıt butonlu cevap

Çalıştırma:  uvicorn app:app --host 0.0.0.0 --port 8000
"""
import base64
import hashlib
import hmac
import json
import os
import re
from datetime import date, datetime, timezone, timedelta

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from parser import parse_text
from tax.consumption import input_credit_ratio

CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OCR_MODEL = os.environ.get("OCR_MODEL", "claude-sonnet-5-5")
# Fiş okuma motoru: "tesseract" (varsayılan, yapay zekâsız) | "claude" | "auto" (tesseract, olmazsa claude)
OCR_ENGINE = os.environ.get("OCR_ENGINE", "tesseract").lower()

JST = timezone(timedelta(hours=9))
LINE_API = "https://api.line.me/v2/bot"
LINE_DATA_API = "https://api-data.line.me/v2/bot"

app = FastAPI(title="Tegaru Kaikei API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------------------------------------------------------------- DB (store.py)
from store import MAX_ENTRY_AMOUNT, add_entry, init_db, issue_token, last_entry, month_summary, undo_last, update_entry  # noqa: E402
from api import router as api_router  # noqa: E402

init_db()
app.include_router(api_router)


# ---------------------------------------------------------------- LINE helpers
def verify_signature(body: bytes, signature: str) -> bool:
    mac = hmac.new(CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(mac), (signature or "").encode())


def quick_reply(*labels: str) -> dict:
    items = []
    for lb in labels:
        if lb == "📷 レシート":
            items.append({"type": "action", "action": {"type": "camera", "label": lb}})
        else:
            items.append({"type": "action", "action": {"type": "message", "label": lb, "text": lb}})
    return {"items": items}


def text_msg(text: str, qr: dict | None = None) -> dict:
    m = {"type": "text", "text": text}
    if qr:
        m["quickReply"] = qr
    return m


async def reply(token: str, messages: list[dict]):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{LINE_API}/message/reply",
            headers={"Authorization": f"Bearer {CHANNEL_TOKEN}"},
            json={"replyToken": token, "messages": messages[:5]},
        )
        if r.status_code != 200:
            print("LINE reply error", r.status_code, r.text)


async def push(user_id: str, messages: list[dict]):
    """reply token kullanılamadığında (uzun OCR) sonucu push ile gönder."""
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{LINE_API}/message/push",
            headers={"Authorization": f"Bearer {CHANNEL_TOKEN}"},
            json={"to": user_id, "messages": messages[:5]},
        )
        if r.status_code != 200:
            print("LINE push error", r.status_code, r.text)


async def get_image(message_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            f"{LINE_DATA_API}/message/{message_id}/content",
            headers={"Authorization": f"Bearer {CHANNEL_TOKEN}"},
        )
        r.raise_for_status()
        return r.content


def yen(n: int) -> str:
    return f"¥{n:,}"


def saved_text(e: dict) -> str:
    if e.get("invoice_no"):
        inv = f"登録番号 {e['invoice_no']}"
    elif e.get("kind") == "inc":
        inv = ""
    else:
        ratio = input_credit_ratio(date.fromisoformat(e["date"]), qualified=False)
        inv = f"⚠️ 登録番号なし（仕入税額控除{ratio}%）"
    return (f"登録しました ✅\n"
            f"{e['store']}  {yen(int(e['amount']))}\n"
            f"{e['category']}・税率{e['rate']}%・{e['date']}\n" + (f"{inv}\n" if inv else "") + "\n"
            f"間違っていたら「取消」を押してください")


def _as_entry(row: dict) -> dict:
    """DB satırı → saved_text'in beklediği biçim."""
    return {"store": row["store"], "amount": row["amount"], "category": row["category"], "rate": row["rate"],
            "date": row["d"], "kind": row["kind"], "invoice_no": row["invoice_no"]}


# ---------------------------------------------------------------- OCR (Claude)
OCR_PROMPT = """これは日本のレシートまたは領収書の画像です。次のJSONだけを返してください（説明文なし）:
{"date":"YYYY-MM-DD","store":"店名",
 "total":税込合計の整数,
 "total10":10%対象の税込合計（無ければ0）,
 "total8":8%（軽減税率・※印）対象の税込合計（無ければ0）,
 "invoice_no":"T+13桁の登録番号。無ければ空文字",
 "category":"旅費交通費|消耗品費|会議費|接待交際費|通信費|地代家賃|水道光熱費|外注工賃|新聞図書費|雑費 のどれか"}
税率ごとの内訳が印字されていない場合は total10 または total8 のどちらかに total を入れてください。
読み取れない場合は {"error":"理由"} を返してください。"""


def normalize_ocr(data: dict) -> list[dict] | dict:
    """OCR JSON → 1件または税率ごとに分けた複数の帳簿レコード。エラーは {"error": ...}。"""
    if "error" in data:
        partial = {k: data[k] for k in ("date", "store", "invoice_no") if data.get(k)}
        return {"error": str(data["error"])[:100], "partial": partial}
    try:
        total = int(data.get("total") or data.get("amount") or 0)
        t10 = int(data.get("total10") or 0)
        t8 = int(data.get("total8") or 0)
    except (TypeError, ValueError):
        return {"error": "金額を読み取れません"}
    if t10 + t8 == 0:
        t10 = total if int(data.get("rate", 10)) != 8 else 0
        t8 = total if int(data.get("rate", 10)) == 8 else 0
    if t10 < 0 or t8 < 0 or t10 + t8 <= 0:
        return {"error": "金額を読み取れません"}
    inv = str(data.get("invoice_no", "")).replace("-", "").replace(" ", "").strip()
    d = str(data.get("date") or "")
    try:
        date.fromisoformat(d)
    except ValueError:
        d = datetime.now(JST).date().isoformat()
    cat = data.get("category") if data.get("category") in EXP_CATEGORIES else "雑費"
    base = {"date": d, "kind": "exp", "store": str(data.get("store") or "(店名不明)")[:60],
            "category": cat, "invoice_no": inv if re.fullmatch(r"T\d{13}", inv) else ""}
    out = [{**base, "amount": a, "rate": r} for r, a in ((10, t10), (8, t8)) if a > 0]
    return out


async def ocr_receipt_claude(img: bytes) -> list[dict] | dict:
    media = "image/png" if img[:8].startswith(b"\x89PNG") else "image/jpeg"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={
                "model": OCR_MODEL,
                "max_tokens": 500,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media,
                                                 "data": base64.b64encode(img).decode()}},
                    {"type": "text", "text": OCR_PROMPT},
                ]}],
            },
        )
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
    m = re.search(r"\{.*\}", text, re.S)
    try:
        data = json.loads(m.group(0)) if m else {"error": "JSONなし"}
    except json.JSONDecodeError:
        data = {"error": "JSON不正"}
    return normalize_ocr(data)


async def ocr_receipt_tesseract(img: bytes) -> list[dict] | dict:
    """Yapay zekâsız: Tesseract OCR + kural tabanlı ayrıştırıcı (receipt_ocr.py)."""
    import asyncio

    import receipt_ocr

    data = await asyncio.to_thread(receipt_ocr.read_receipt, img, datetime.now(JST).date())
    data.pop("_raw_text", None)
    return normalize_ocr(data)


async def ocr_receipt(img: bytes) -> list[dict] | dict:
    import receipt_ocr

    engine = OCR_ENGINE
    if engine == "claude":
        if not ANTHROPIC_KEY:
            return {"error": "AI読取が未設定です"}
        return await ocr_receipt_claude(img)
    if not receipt_ocr.available():
        if engine == "auto" and ANTHROPIC_KEY:
            return await ocr_receipt_claude(img)
        return {"error": "OCRエンジンが利用できません"}
    result = await ocr_receipt_tesseract(img)
    if isinstance(result, dict) and engine == "auto" and ANTHROPIC_KEY:
        return await ocr_receipt_claude(img)  # kural tabanlı okuma başarısızsa AI yedeği
    return result


# ---------------------------------------------------------------- handlers
QR_AFTER_SAVE = ("取消", "科目変更", "税率8%", "税率10%", "合計", "📷 レシート")
EXP_CATEGORIES = ("旅費交通費", "消耗品費", "会議費", "接待交際費", "通信費", "地代家賃", "水道光熱費",
                  "外注工賃", "新聞図書費", "広告宣伝費", "支払手数料", "雑費")
HELP = ("レシートの写真か「店名 金額」を送ってください。\n"
        "例：ローソン 540円 軽減\n例：タクシー 2300 T1234567890123\n"
        "例：入金 330000 合同会社ミナト\n\n「合計」今月の集計　「取消」直前の記録を削除\n「パネル」ウェブ管理画面の接続コード")


Options = list[tuple[str, str]]  # (buton etiketi, gönderilecek metin)
CAMERA = "📷 レシート"


def opts(*labels: str) -> Options:
    return [(lb, lb) for lb in labels]


def respond(user_id: str, text: str, source: str = "LINE") -> tuple[str, Options]:
    """Kanaldan bağımsız sohbet çekirdeği (LINE, WhatsApp). Yanıt metni + hızlı yanıt seçenekleri döner."""
    t = text.strip()
    if re.match(r"^(取消|取り消し|iptal)", t):
        row = undo_last(user_id)
        msg = f"「{row['store']} {yen(row['amount'])}」を取り消しました" if row else "取り消す記録がありません"
        return msg, opts("合計", CAMERA)
    if t == "科目変更":
        last = last_entry(user_id)
        if not last:
            return "変更する記録がありません", []
        return (f"「{last['store']} {yen(last['amount'])}」の勘定科目を選んでください",
                [(c, f"科目:{c}") for c in EXP_CATEGORIES[:13]])
    m = re.match(r"^科目[:：](.+)$", t)
    if m:
        cat = m.group(1).strip()
        last = last_entry(user_id)
        if not last or last["kind"] != "exp" or cat not in EXP_CATEGORIES:
            return "変更できませんでした（経費の記録と一覧の科目のみ変更できます）", []
        e = update_entry(user_id, last["id"], category=cat)
        return saved_text(_as_entry(e)).replace("登録しました", "変更しました"), opts(*QR_AFTER_SAVE)
    m = re.match(r"^税率\s*(8|10)\s*[%％]$", t)
    if m:
        last = last_entry(user_id)
        if not last:
            return "変更する記録がありません", []
        e = update_entry(user_id, last["id"], rate=int(m.group(1)))
        return saved_text(_as_entry(e)).replace("登録しました", "変更しました"), opts(*QR_AFTER_SAVE)
    if re.match(r"^(合計|今月|集計)", t):
        inc, exp = month_summary(user_id)
        return f"今月の集計\n売上 {yen(inc)}\n経費 {yen(exp)}\n差引 {yen(inc - exp)}", opts(CAMERA)
    if t in ("レシートを送る", CAMERA):
        return "下のボタンでレシートを撮影するか、写真を送ってください。", opts(CAMERA)
    if re.match(r"^(パネル|ウェブ|web|panel)$", t, re.I):
        tok = issue_token(user_id, f"{source.lower()}-panel")
        base = os.environ.get("PANEL_URL", "")
        link = f"{base}/connect#{tok}" if base else ""
        return ("ウェブ管理画面の接続コードです（他人に見せないでください）:\n" + tok
                + (f"\n\nこちらから開けます:\n{link}" if link else "")), []
    if re.match(r"^(ヘルプ|使い方|help)", t, re.I):
        return HELP, opts(CAMERA, "合計")

    e = parse_text(t, datetime.now(JST).date())
    if not e:
        return "金額が見つかりませんでした。\n" + HELP, []
    if int(e["amount"]) >= MAX_ENTRY_AMOUNT:
        return TOO_LARGE, []
    if e.get("kind") == "exp" and (notice := limit_notice(user_id)):
        return notice, opts("合計")
    add_entry(user_id, e, source=source)
    return saved_text(e), opts(*QR_AFTER_SAVE)


TOO_LARGE = "金額が大きすぎます。1件20億円未満で入力してください。"


def limit_notice(user_id: str) -> str | None:
    """Plan sınırı (T-042b): yeni 経費 kaydından önce. Aşıldıysa kaydetmeden gösterilecek Japonca metin."""
    import billing

    try:
        billing.check_limit(user_id, "receipts")
    except billing.LimitExceeded as ex:
        base = os.environ.get("PANEL_URL", "").rstrip("/")
        link = f"\n\nプランの確認・変更はこちら:\n{base}/billing/" if base else "\n\n「パネル」と送るとウェブ管理画面からプランを変更できます。"
        return f"{ex}\n今回の内容は記録されていません。{link}"
    return None


def to_line(msg: str, options: Options) -> dict:
    items = []
    for label, send in options[:13]:
        if send == CAMERA:
            items.append({"type": "action", "action": {"type": "camera", "label": label}})
        else:
            items.append({"type": "action", "action": {"type": "message", "label": label[:20], "text": send}})
    return text_msg(msg, {"items": items} if items else None)


async def handle_text(user_id: str, token: str, text: str):
    await reply(token, [to_line(*respond(user_id, text, "LINE"))])


READING_TEXT = "レシートを読み取り中です…\n結果はこのあと届きます（少しお待ちください）。"
IMAGE_FAIL_TEXT = "画像を読み取れませんでした。もう一度送るか「店名 金額」で入力してください。"


async def process_image(user_id: str, img: bytes, ref: str, source: str) -> tuple[str, Options]:
    """Fiş görseli → OCR → kayıt. Kanaldan bağımsız."""
    if notice := limit_notice(user_id):  # OCR'dan önce: sınır aşıldıysa görsel işlenmez/saklanmaz
        return notice, opts("合計")
    try:
        os.makedirs("receipts", exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_-]", "", f"{user_id[-8:]}_{ref}")[:80]
        path = f"receipts/{safe}.jpg"
        with open(path, "wb") as f:
            f.write(img)
        result = await ocr_receipt(img)
    except Exception as ex:  # ağ / API hatası
        print("image error", type(ex).__name__)
        return IMAGE_FAIL_TEXT, []
    if isinstance(result, dict):
        p = result.get("partial") or {}
        got = "・".join(x for x in (p.get("date"), p.get("store"), p.get("invoice_no")) if x)
        hint = f"\n読み取れた項目: {got}" if got else ""
        store = p.get("store") or "店名"
        return (f"金額を読み取れませんでした（{result['error']}）。{hint}\n"
                f"「{store} 1234」のように金額を送ってください。"), []
    if any(int(e["amount"]) >= MAX_ENTRY_AMOUNT for e in result):
        return TOO_LARGE, []
    for e in result:
        add_entry(user_id, e, image_path=path, source=source)
    if len(result) == 1:
        return saved_text(result[0]), opts(*QR_AFTER_SAVE)
    lines = "\n".join(f"・{e['rate']}%対象 {yen(e['amount'])}" for e in result)
    head = saved_text(result[0]).split("\n")[0]
    return (f"{head}\n{result[0]['store']}（税率ごとに{len(result)}件に分けて記録）\n{lines}\n"
            f"{result[0]['category']}・{result[0]['date']}\n\n間違っていたら「取消」を押してください"), opts("取消", "合計", CAMERA)


def reply_wait_seconds() -> float:
    """reply token ile sonucu beklemek için süre (sn). Aşılırsa önce 「読み取り中」, sonuç push ile."""
    try:
        return max(0.0, min(float(os.environ.get("LINE_REPLY_WAIT_SEC", "8")), 50.0))
    except ValueError:
        return 8.0


async def _image_result(user_id: str, message_id: str) -> dict:
    try:
        img = await get_image(message_id)
    except Exception as ex:
        print("LINE content error", type(ex).__name__)
        return text_msg("画像を取得できませんでした。もう一度送ってください。")
    return to_line(*await process_image(user_id, img, message_id, "LINE"))


async def handle_image(user_id: str, token: str, message_id: str):
    """Fiş görseli. OCR (özellikle Render free planında) uzun sürebilir; reply token kısa ömürlü
    olduğundan `reply_wait_seconds()` içinde biterse sonuç reply ile (push kotası harcanmaz),
    bitmezse önce 「読み取り中」 reply edilir ve sonuç push mesajla gönderilir."""
    import asyncio
    task = asyncio.ensure_future(_image_result(user_id, message_id))
    try:
        msg = await asyncio.wait_for(asyncio.shield(task), timeout=reply_wait_seconds())
    except asyncio.TimeoutError:
        await reply(token, [text_msg(READING_TEXT)])
        try:
            msg = await task
        except Exception as ex:
            print("image task error", type(ex).__name__)
            msg = text_msg(IMAGE_FAIL_TEXT)
        try:
            await push(user_id, [msg])
        except Exception as ex:
            print("LINE push error", type(ex).__name__)
        return
    except Exception as ex:
        print("image task error", type(ex).__name__)
        msg = text_msg(IMAGE_FAIL_TEXT)
    await reply(token, [msg])


async def handle_event(ev: dict):
    user_id = ev.get("source", {}).get("userId", "")
    token = ev.get("replyToken")
    if ev["type"] == "follow":  # arkadaş ekledi
        return await reply(token, [to_line("てがる会計へようこそ！\n" + HELP, opts(CAMERA))])
    if ev["type"] != "message" or not user_id:
        return
    m = ev["message"]
    if m["type"] == "text":
        await handle_text(user_id, token, m["text"])
    elif m["type"] == "image":
        await handle_image(user_id, token, m["id"])
    else:
        await reply(token, [text_msg("テキストかレシート画像を送ってください。")])


@app.post("/callback")
async def callback(request: Request, bg: BackgroundTasks,
                   x_line_signature: str = Header(default="")):
    body = await request.body()
    if not CHANNEL_SECRET:
        raise HTTPException(503, "LINE_CHANNEL_SECRET is not set")
    if not verify_signature(body, x_line_signature):
        raise HTTPException(400, "invalid signature")
    for ev in json.loads(body).get("events", []):
        bg.add_task(handle_event, ev)  # LINE'a hemen 200 dön, işlem arkada
    return PlainTextResponse("OK")


@app.get("/entries/{user_id}")
def entries(user_id: str, year: str = "2026", x_admin_key: str = Header(default="")):
    """Kayıt listesi (geçici: yalnızca ADMIN_KEY ile; tenant API'si T-005)."""
    if not ADMIN_KEY or not hmac.compare_digest(x_admin_key.encode(), ADMIN_KEY.encode()):
        raise HTTPException(401, "admin key required")
    if not re.fullmatch(r"\d{4}", year):
        raise HTTPException(400, "year must be YYYY")
    from store import entries_in_range
    return entries_in_range(user_id, f"{year}-01-01", f"{year}-12-31")


@app.get("/")
def health():
    return {"ok": True, "line_configured": bool(CHANNEL_SECRET and CHANNEL_TOKEN),
            "ocr_configured": bool(ANTHROPIC_KEY), "ocr_engine": OCR_ENGINE,
            "tesseract": __import__("receipt_ocr").available()}


@app.post("/admin/richmenu")
async def admin_richmenu(x_admin_key: str = Header(default=""), key: str = ""):
    """Alttaki 3 butonlu menüyü kurar. Render'da kabuk olmadığı için HTTP ile çağrılır:
    curl -X POST -H "X-Admin-Key: <ADMIN_KEY>" "https://<adres>/admin/richmenu"
    `?key=` sorgusu geriye uyum için hâlâ kabul edilir ama anahtar erişim log'una düştüğü
    için kullanımdan kalktı (T-028); başlık verilmişse sorgu yok sayılır."""
    supplied = x_admin_key
    if not supplied and key:
        print("admin/richmenu: ?key= deprecated, use X-Admin-Key header")
        supplied = key
    if not ADMIN_KEY or not hmac.compare_digest(supplied.encode(), ADMIN_KEY.encode()):
        raise HTTPException(403, "bad key")
    from setup_richmenu import create_and_set
    with open(os.path.join(os.path.dirname(__file__), "richmenu.png"), "rb") as f:
        rid = await create_and_set(CHANNEL_TOKEN, f.read())
    return {"richMenuId": rid}


# ---------------------------------------------------------------- WhatsApp
from whatsapp import router as wa_router  # noqa: E402

app.include_router(wa_router)
