"""WhatsApp Business (Meta Cloud API) kanalı. Sohbet mantığı `app.respond` ile LINE'la ortaktır.

Ortam değişkenleri:
  WHATSAPP_VERIFY_TOKEN   webhook doğrulama (Meta'da girdiğin rastgele metin)
  WHATSAPP_APP_SECRET     X-Hub-Signature-256 doğrulaması (Meta App Secret)
  WHATSAPP_TOKEN          kalıcı erişim token'ı (System User)
  WHATSAPP_PHONE_ID       Phone number ID
Webhook URL: https://<sunucu>/whatsapp
Defter anahtarı: `wa:<telefon>` (LINE defterinden ayrı).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

GRAPH = "https://graph.facebook.com/v21.0"
router = APIRouter(tags=["whatsapp"])


def _env(k: str) -> str:
    return os.environ.get(k, "")


def verify_signature(body: bytes, header: str) -> bool:
    secret = _env("WHATSAPP_APP_SECRET")
    if not secret or not header.startswith("sha256="):
        return False
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac.encode(), header.removeprefix("sha256=").encode())


def build_message(to: str, text: str, options: list[tuple[str, str]]) -> dict:
    """Seçenek ≤3 → reply buttons, 4–10 → list message, yoksa düz metin.
    WhatsApp etiket sınırları: buton başlığı 20, liste satırı 24 karakter; buton id = gönderilecek metin."""
    base = {"messaging_product": "whatsapp", "to": to}
    opts = [(lb, send) for lb, send in options if send != "📷 レシート"]  # WhatsApp'ta kamera butonu yok
    if not opts:
        return {**base, "type": "text", "text": {"body": text[:4096]}}
    if len(opts) <= 3:
        return {**base, "type": "interactive", "interactive": {
            "type": "button", "body": {"text": text[:1024]},
            "action": {"buttons": [{"type": "reply", "reply": {"id": send[:256], "title": lb[:20]}} for lb, send in opts]}}}
    return {**base, "type": "interactive", "interactive": {
        "type": "list", "body": {"text": text[:1024]},
        "action": {"button": "選択する", "sections": [{"title": "操作", "rows": [
            {"id": send[:200], "title": lb[:24]} for lb, send in opts[:10]]}]}}}


async def send(payload: dict) -> None:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{GRAPH}/{_env('WHATSAPP_PHONE_ID')}/messages",
                         headers={"Authorization": f"Bearer {_env('WHATSAPP_TOKEN')}"}, json=payload)
        if r.status_code >= 300:
            print("WhatsApp send error", r.status_code)


async def get_media(media_id: str) -> bytes:
    h = {"Authorization": f"Bearer {_env('WHATSAPP_TOKEN')}"}
    async with httpx.AsyncClient(timeout=30) as c:
        meta = await c.get(f"{GRAPH}/{media_id}", headers=h)
        meta.raise_for_status()
        r = await c.get(meta.json()["url"], headers=h)
        r.raise_for_status()
        return r.content


def extract_text(msg: dict) -> str | None:
    t = msg.get("type")
    if t == "text":
        return msg["text"]["body"]
    if t == "interactive":
        it = msg["interactive"]
        return (it.get("button_reply") or it.get("list_reply") or {}).get("id")
    if t == "button":
        return msg["button"].get("payload") or msg["button"].get("text")
    return None


async def handle_message(msg: dict) -> None:
    import app  # lazy: app bu modülü içe aktarıyor

    phone = msg.get("from", "")
    if not phone:
        return
    uid = f"wa:{phone}"
    if msg.get("type") == "image":
        try:
            img = await get_media(msg["image"]["id"])
        except Exception as ex:
            print("WhatsApp media error", type(ex).__name__)
            return await send(build_message(phone, "画像を取得できませんでした。もう一度送ってください。", []))
        text, options = await app.process_image(uid, img, msg["image"]["id"], "WhatsApp")
    else:
        body = extract_text(msg)
        if body is None:
            return await send(build_message(phone, "テキストかレシート画像を送ってください。", []))
        text, options = app.respond(uid, body, "WhatsApp")
    await send(build_message(phone, text, options))


@router.get("/whatsapp")
def verify(mode: str = Query("", alias="hub.mode"), token: str = Query("", alias="hub.verify_token"),
           challenge: str = Query("", alias="hub.challenge")):
    expected = _env("WHATSAPP_VERIFY_TOKEN")
    if mode == "subscribe" and expected and hmac.compare_digest(token.encode(), expected.encode()):
        return PlainTextResponse(challenge)
    raise HTTPException(403, "verification failed")


@router.post("/whatsapp")
async def webhook(request: Request, bg: BackgroundTasks, x_hub_signature_256: str = Header(default="")):
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(401, "invalid signature")
    data = json.loads(body or b"{}")
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []) or []:
                bg.add_task(handle_message, msg)
    return PlainTextResponse("OK")
