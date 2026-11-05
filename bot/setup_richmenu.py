"""LINE リッチメニュー（画面下の3ボタン）を作成して全ユーザーに設定する。

- Sunucuda: POST /admin/richmenu?key=ADMIN_KEY (hazır richmenu.png kullanılır)
- Yerelde:  python setup_richmenu.py   (görseli yeniden çizer; Pillow + Japonca font gerekir)
"""
import io
import os

import httpx

W, HT = 2500, 843
BUTTONS = [("レシート", "Receipt", "レシートを送る"), ("今月の集計", "Summary", "合計"), ("取り消し", "Undo", "取消")]
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
]


def make_image() -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    def font(size):
        for p in FONT_CANDIDATES:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default(size)

    img = Image.new("RGB", (W, HT), "#ffffff")
    d = ImageDraw.Draw(img)
    cw = W // 3
    for i, (ja, tr, _) in enumerate(BUTTONS):
        x0 = i * cw
        d.rectangle([x0, 0, x0 + cw, HT], fill="#06c755" if i == 0 else "#f2f5f3")
        col = "#ffffff" if i == 0 else "#1b2a3d"
        d.text((x0 + cw / 2, HT / 2 - 40), ja, font=font(120), fill=col, anchor="mm")
        d.text((x0 + cw / 2, HT / 2 + 90), tr, font=font(64), fill=col, anchor="mm")
        if i:
            d.line([x0, 60, x0, HT - 60], fill="#d5dcd8", width=4)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


async def create_and_set(token: str, png: bytes) -> str:
    h = {"Authorization": f"Bearer {token}"}
    cw = W // 3
    body = {
        "size": {"width": W, "height": HT}, "selected": True,
        "name": "tegaru-main", "chatBarText": "メニュー",
        "areas": [{"bounds": {"x": i * cw, "y": 0, "width": cw, "height": HT},
                   "action": {"type": "message", "text": t}} for i, (_, _, t) in enumerate(BUTTONS)],
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post("https://api.line.me/v2/bot/richmenu", headers=h, json=body)
        r.raise_for_status()
        rid = r.json()["richMenuId"]
        (await c.post(f"https://api-data.line.me/v2/bot/richmenu/{rid}/content",
                      headers={**h, "Content-Type": "image/png"}, content=png)).raise_for_status()
        (await c.post(f"https://api.line.me/v2/bot/user/all/richmenu/{rid}", headers=h)).raise_for_status()
    return rid


if __name__ == "__main__":
    import asyncio
    print("Rich menu ready:", asyncio.run(create_and_set(os.environ["LINE_CHANNEL_ACCESS_TOKEN"], make_image())))
