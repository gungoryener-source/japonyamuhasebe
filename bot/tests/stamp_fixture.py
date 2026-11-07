"""T-026: fikstür fişlerinin üstüne sentetik kırmızı damga (角印 / 丸印) basar.

Damgalı görseller depoya ikili dosya olarak konmaz; testler ve `scripts/ocr_eval.py --synthetic`
bunları temiz fikstürlerden deterministik olarak üretir.
"""
from __future__ import annotations

import io
import os

from PIL import Image, ImageDraw, ImageFont

BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(BOT_DIR, "fonts", "ipag.ttf")
SHUIRO = (226, 64, 48)       # 朱色 (yaygın şirket damgası mürekkebi)
FADED = (232, 120, 120)      # soluk / az mürekkepli damga


def _font(size: int):
    return ImageFont.truetype(FONT, size)


def _kakuin(layer, box, color, chars="日本交通之印"):
    """Kare şirket damgası: çerçeve + 3x2 karakter. `box` = (x, y, kenar)."""
    x, y, side = box
    d = ImageDraw.Draw(layer)
    d.rectangle([x, y, x + side, y + side], outline=color + (200,), width=max(3, side // 22))
    f = _font(side // 3)
    cell = side // 3
    for i, ch in enumerate(chars[:6]):
        col, row = divmod(i, 3)
        cx = x + side - (col + 1) * (side // 2) + side // 4 - cell // 2
        cy = y + side // 12 + row * (side - side // 6) // 3
        d.text((cx, cy), ch, font=f, fill=color + (200,))


def _maruin(layer, center, r, color, ch="済"):
    """Yuvarlak damga (認印・受領印)."""
    cx, cy = center
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color + (210,), width=max(3, r // 9))
    f = _font(int(r * 1.2))
    d.text((cx, cy), ch, font=f, fill=color + (210,), anchor="mm")


def stamp(img_bytes: bytes, stamps: list[tuple], quality: int = 90) -> bytes:
    """Görsele damgaları yarı saydam (mürekkep gibi) basar → JPEG bayt.

    stamps: ("kaku", (x, y, kenar), renk) veya ("maru", (cx, cy), yarıçap, renk) — koordinatlar
    görsel genişliğinin oranı (0–1) olarak verilir, böylece farklı boyutlu fikstürlerde çalışır.
    """
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, _ = im.size
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for s in stamps:
        if s[0] == "kaku":
            _, (fx, fy, fs), color = s
            _kakuin(layer, (int(fx * w), int(fy * w), int(fs * w)), color)
        else:
            _, (fx, fy), fr, color = s
            _maruin(layer, (int(fx * w), int(fy * w)), int(fr * w), color)
    # Mürekkep: siyah baskının üstünde koyulaşır (multiply), beyazda saf renk görünür
    ink = Image.new("RGB", im.size, (255, 255, 255))
    ink.paste(layer, mask=layer.split()[3])
    from PIL import ImageChops
    out = ImageChops.multiply(im, ink)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


# Fikstür başına damga yerleşimleri: 角印 şirket adı/登録番号 üstünde, 丸印 tarih veya tutar üstünde.
LAYOUTS = {
    "taxi": [("kaku", (0.56, 0.10, 0.20), SHUIRO), ("maru", (0.22, 0.28), 0.07, SHUIRO),
             ("maru", (0.88, 0.52), 0.065, FADED)],
    "restaurant": [("kaku", (0.60, 0.04, 0.20), SHUIRO), ("maru", (0.25, 0.30), 0.07, SHUIRO)],
    "konbini": [("maru", (0.30, 0.20), 0.07, SHUIRO), ("maru", (0.80, 0.62), 0.065, FADED)],
}


def stamped_fixture(name: str) -> bytes:
    with open(os.path.join(BOT_DIR, "tests", "fixtures", f"{name}.jpg"), "rb") as f:
        return stamp(f.read(), LAYOUTS[name])
