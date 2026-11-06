"""Test fişi görselleri üretir (IPAゴシック). python tests/make_receipts.py"""
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = os.path.join(os.path.dirname(__file__), "..", "fonts", "ipag.ttf")
NOTO = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"  # fikstür üretimi için (yoksa IPA)
OUT = os.path.join(os.path.dirname(__file__), "fixtures")

RECEIPTS = {
    "konbini": [
        ("ファミリーマート 新宿西口店", 30, "c"), ("東京都新宿区西新宿1-1-1", 20, "c"), ("TEL 03-1234-5678", 20, "c"),
        ("登録番号 T4013301012345", 20, "c"), ("", 20, "l"),
        ("2026年11月05日(木) 12:34", 22, "l"), ("レジ0002 責No.123", 20, "l"), ("", 20, "l"),
        ("おにぎり 鮭 ※", 24, "l", "¥160"), ("お茶 500ml ※", 24, "l", "¥140"),
        ("ボールペン", 24, "l", "¥330"), ("ノート A5", 24, "l", "¥220"), ("", 20, "l"),
        ("小計", 24, "l", "¥850"), ("(10%対象", 22, "l", "¥550)"), ("(8%対象", 22, "l", "¥300)"),
        ("合計", 30, "l", "¥850"), ("お預り", 22, "l", "¥1,000"), ("お釣り", 22, "l", "¥150"),
        ("※印は軽減税率対象商品です", 18, "l"),
    ],
    "taxi": [
        ("領収書", 32, "c"), ("日本交通株式会社", 26, "c"), ("登録番号 T4010001054321", 20, "c"),
        ("令和8年10月14日 23:10", 22, "l"), ("乗車地 渋谷 降車地 品川", 22, "l"),
        ("運賃", 24, "l", "¥3,410"), ("(10%対象 ¥3,410 内消費税 ¥310)", 20, "l"),
        ("合計金額", 30, "l", "¥3,410"),
    ],
    "restaurant": [
        ("居酒屋 たぬき 本店", 30, "c"), ("TEL 03-9876-5432", 20, "c"),
        ("2026/10/28 21:05", 22, "l"), ("生ビール", 24, "l", "¥1,200"), ("刺身盛合せ", 24, "l", "¥2,800"),
        ("焼き鳥", 24, "l", "¥1,500"), ("お会計", 30, "l", "¥5,500"), ("(内消費税 ¥500)", 20, "l"),
        ("ありがとうございました", 20, "c"),
    ],
}


def render(lines, photo=False, seed=0):
    W, pad = 640, 30
    font_cache = {}
    def f(sz):
        return font_cache.setdefault(sz, ImageFont.truetype(FONT, sz))
    H = pad * 2 + sum(int(l[1] * 1.5) + 4 for l in lines)
    im = Image.new("L", (W, H), 250)
    d = ImageDraw.Draw(im)
    y = pad
    for line in lines:
        text, sz, align = line[0], line[1], line[2]
        right = line[3] if len(line) > 3 else None
        w = d.textlength(text, font=f(sz))
        x = (W - w) / 2 if align == "c" else pad
        d.text((x, y), text, fill=20, font=f(sz))
        if right:
            d.text((W - pad - d.textlength(right, font=f(sz)), y), right, fill=20, font=f(sz))
        y += int(sz * 1.5) + 4
    if photo:
        rnd = random.Random(seed)
        im = im.rotate(1.5, expand=True, fillcolor=200)
        px = im.load()
        for _ in range(im.size[0] * im.size[1] // 60):
            x, yy = rnd.randrange(im.size[0]), rnd.randrange(im.size[1])
            px[x, yy] = rnd.choice((120, 180, 230))
        im = im.filter(ImageFilter.GaussianBlur(0.6))
        im = im.resize((int(im.size[0] * 0.8), int(im.size[1] * 0.8)))
    return im.convert("RGB")


def main():
    global FONT
    os.makedirs(OUT, exist_ok=True)
    ipa = FONT
    if os.path.exists(NOTO):
        FONT = NOTO
    for name, lines in RECEIPTS.items():
        render(lines).save(os.path.join(OUT, f"{name}.jpg"), quality=88)
    render(RECEIPTS["konbini"], photo=True, seed=1).save(os.path.join(OUT, "konbini_photo.jpg"), quality=80)
    FONT = ipa  # IPA fontu: Japonca model 0→9 karıştırıyor; T番号 ikinci geçiş testi için
    render(RECEIPTS["konbini"]).save(os.path.join(OUT, "konbini_ipa.jpg"), quality=88)
    print("ok")


if __name__ == "__main__":
    main()
