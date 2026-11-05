"""
てがる会計 LINE Bot — LINE Messaging API webhook sunucusu.

Akış:
  LINE kullanıcısı mesaj / fiş fotoğrafı gönderir
  → /callback (imza doğrulanır, 200 hemen döner)
  → arka planda: metin ise parser, fotoğraf ise Claude ile fiş okuma
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
from store import add_entry, init_db, issue_token, last_entry, month_summary, undo_last, update_entry  # noqa: E402
from api import router as api_router  # noqa: E402

init_db()
app.include_router(api_router)


# ---------------------------------------------------------------- LINE helpers
def verify_signature(body: bytes, signature: str) -> bool:
    mac = hmac.new(CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(mac).decode(), signature or "")


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


# ---------------------------------------------------------------- OCR (Claude)
OCR_PROMPT = """これは日本のレシートまたは領収書の画像です。次のJSONだけを返してください（説明文なし）:
{"date":"YYYY-MM-DD","store":"店名","amount":税込合計の整数,
 "rate":10または8（軽減税率の食品が中心なら8、混在なら金額の大きい方）,
 "invoice_no":"T+13桁の登録番号。無ければ空文字",
 "category":"旅費交通費|消耗品費|会議費|接待交際費|通信費|地代家賃|水道光熱費|外注工賃|新聞図書費|雑費 のどれか"}
読み取れない場合は {"error":"理由"} を返してください。"""


async def ocr_receipt(img: bytes) -> dict:
    media = "image/png" if img[:8].startswith(b"\x89PNG") else "image/jpeg"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={
                "model": OCR_MODEL,
                "max_tokens": 400,
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
    data = json.loads(m.group(0)) if m else {"error": "JSONなし"}
    if "error" in data:
        return data
    inv = str(data.get("invoice_no", "")).replace("-", "").strip()
    data["invoice_no"] = inv if re.fullmatch(r"T\d{13}", inv) else ""
    data["date"] = data.get("date") or date.today().isoformat()
    data["kind"] = "exp"
    data["rate"] = 8 if int(data.get("rate", 10)) == 8 else 10
    return data


# ---------------------------------------------------------------- handlers
QR_AFTER_SAVE = ("取消", "合計", "📷 レシート")
HELP = ("レシートの写真か「店名 金額」を送ってください。\n"
        "例：ローソン 540円 軽減\n例：タクシー 2300 T1234567890123\n"
        "例：入金 330000 合同会社ミナト\n\n「合計」今月の集計　「取消」直前の記録を削除\n「パネル」ウェブ管理画面の接続コード")


async def handle_text(user_id: str, token: str, text: str):
    t = text.strip()
    if re.match(r"^(取消|取り消し|iptal)", t):
        row = undo_last(user_id)
        msg = f"「{row['store']} {yen(row['amount'])}」を取り消しました" if row else "取り消す記録がありません"
        return await reply(token, [text_msg(msg, quick_reply("合計", "📷 レシート"))])
    if re.match(r"^(合計|今月|集計)", t):
        inc, exp = month_summary(user_id)
        return await reply(token, [text_msg(
            f"今月の集計\n売上 {yen(inc)}\n経費 {yen(exp)}\n差引 {yen(inc - exp)}",
            quick_reply("📷 レシート"))])
    if t in ("レシートを送る", "📷 レシート"):
        return await reply(token, [text_msg("下のボタンでレシートを撮影するか、写真を送ってください。",
                                            quick_reply("📷 レシート"))])
    if re.match(r"^(パネル|ウェブ|web|panel)$", t, re.I):
        tok = issue_token(user_id, "line-panel")
        base = os.environ.get("PANEL_URL", "")
        link = f"{base}/connect#{tok}" if base else ""
        msg = ("ウェブ管理画面の接続コードです（他人に見せないでください）:\n" + tok
               + (f"\n\nこちらから開けます:\n{link}" if link else ""))
        return await reply(token, [text_msg(msg)])
    if re.match(r"^(ヘルプ|使い方|help)", t, re.I):
        return await reply(token, [text_msg(HELP, quick_reply("📷 レシート", "合計"))])

    e = parse_text(t, datetime.now(JST).date())
    if not e:
        return await reply(token, [text_msg("金額が見つかりませんでした。\n" + HELP)])
    add_entry(user_id, e)
    await reply(token, [text_msg(saved_text(e), quick_reply(*QR_AFTER_SAVE))])


async def handle_image(user_id: str, token: str, message_id: str):
    try:
        img = await get_image(message_id)
        os.makedirs("receipts", exist_ok=True)
        path = f"receipts/{user_id[-8:]}_{message_id}.jpg"
        with open(path, "wb") as f:
            f.write(img)
        e = await ocr_receipt(img)
    except Exception as ex:  # ağ / API hatası
        print("image error", ex)
        return await reply(token, [text_msg("画像を読み取れませんでした。もう一度送るか「店名 金額」で入力してください。")])
    if "error" in e:
        return await reply(token, [text_msg(f"読み取れませんでした（{e['error']}）。\n「店名 金額」で送ってください。")])
    add_entry(user_id, e, image_path=path)
    await reply(token, [text_msg(saved_text(e), quick_reply(*QR_AFTER_SAVE))])


async def handle_event(ev: dict):
    user_id = ev.get("source", {}).get("userId", "")
    token = ev.get("replyToken")
    if ev["type"] == "follow":  # arkadaş ekledi
        return await reply(token, [text_msg("てがる会計へようこそ！\n" + HELP, quick_reply("📷 レシート"))])
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
    if not ADMIN_KEY or not hmac.compare_digest(x_admin_key, ADMIN_KEY):
        raise HTTPException(401, "admin key required")
    if not re.fullmatch(r"\d{4}", year):
        raise HTTPException(400, "year must be YYYY")
    from store import search_entries
    return search_entries(user_id, date_from=f"{year}-01-01", date_to=f"{year}-12-31", limit=5000)


@app.get("/")
def health():
    return {"ok": True, "line_configured": bool(CHANNEL_SECRET and CHANNEL_TOKEN),
            "ocr_configured": bool(ANTHROPIC_KEY)}


@app.post("/admin/richmenu")
async def admin_richmenu(key: str = ""):
    """Alttaki 3 butonlu menüyü kurar. Render'da kabuk olmadığı için HTTP ile çağrılır:
    curl -X POST "https://<adres>/admin/richmenu?key=<ADMIN_KEY>" """
    if not ADMIN_KEY or not hmac.compare_digest(key, ADMIN_KEY):
        raise HTTPException(403, "bad key")
    from setup_richmenu import create_and_set
    with open(os.path.join(os.path.dirname(__file__), "richmenu.png"), "rb") as f:
        rid = await create_and_set(CHANNEL_TOKEN, f.read())
    return {"richMenuId": rid}
