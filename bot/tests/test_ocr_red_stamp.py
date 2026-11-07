"""T-026: OCR ön işlemede kırmızı damga (角印・丸印) bastırma."""
import io
import os
from datetime import date

import pytest
from PIL import Image, ImageDraw

import receipt_ocr
from stamp_fixture import FADED, SHUIRO, stamped_fixture

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
TODAY = date(2026, 11, 5)
needs_ocr = pytest.mark.skipif(not receipt_ocr.available(), reason="tesseract + jpn not installed")


def _png(im) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _gray_at(png: bytes, xy):
    im = Image.open(io.BytesIO(png))
    w0 = 400
    scale = im.size[0] / w0
    return im.getpixel((int(xy[0] * scale), int(xy[1] * scale)))


def _swatches(mode="RGB"):
    """400x200: siyah metin bloğu, 朱色 blok, soluk kırmızı, mavi, yeşil, gri ve damga üstünde siyah."""
    im = Image.new("RGB", (400, 200), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([10, 10, 60, 60], fill=(20, 20, 20))       # siyah baskı
    d.rectangle([80, 10, 130, 60], fill=SHUIRO)            # 朱色 damga
    d.rectangle([150, 10, 200, 60], fill=FADED)            # soluk damga
    d.rectangle([220, 10, 270, 60], fill=(30, 60, 200))    # mavi mürekkep (ボールペン)
    d.rectangle([290, 10, 340, 60], fill=(30, 140, 60))    # yeşil
    d.rectangle([10, 100, 60, 150], fill=(128, 128, 128))  # gri
    d.rectangle([80, 100, 180, 150], fill=SHUIRO)
    d.rectangle([110, 110, 150, 140], fill=(60, 15, 12))   # damga üstüne basılmış siyah yazı (multiply)
    d.rectangle([220, 100, 270, 150], fill=(210, 40, 90))   # koyu pembe (≈342°) damga
    return im.convert(mode) if mode != "RGB" else im


def test_red_and_faded_stamp_become_white():
    out = receipt_ocr.preprocess(_png(_swatches()))
    assert _gray_at(out, (105, 35)) >= 240      # 朱色
    assert _gray_at(out, (175, 35)) >= 240      # soluk
    assert _gray_at(out, (245, 125)) >= 240     # koyu pembe
    assert _gray_at(out, (90, 105)) >= 240      # damganın siyah yazı dışındaki kısmı


def test_black_blue_green_gray_and_text_on_stamp_are_kept():
    out = receipt_ocr.preprocess(_png(_swatches()))
    assert _gray_at(out, (35, 35)) <= 40        # siyah baskı
    assert _gray_at(out, (130, 125)) <= 60      # damga üstündeki siyah yazı silinmez
    assert _gray_at(out, (245, 35)) <= 120      # mavi kalem
    assert _gray_at(out, (315, 35)) <= 160      # yeşil
    assert _gray_at(out, (35, 125)) <= 180      # gri


def test_disabled_keeps_stamp_dark(monkeypatch):
    monkeypatch.setattr(receipt_ocr, "RED_SUPPRESS", False)
    out = receipt_ocr.preprocess(_png(_swatches()))
    assert _gray_at(out, (105, 35)) <= 160      # bastırma kapalıyken damga gri tonda koyu kalır


@pytest.mark.parametrize("mode", ["L", "RGBA", "P", "CMYK", "LA"])
def test_other_image_modes(mode):
    im = _swatches(mode)
    buf = io.BytesIO()
    im.save(buf, "TIFF" if mode == "CMYK" else "PNG")
    out = Image.open(io.BytesIO(receipt_ocr.preprocess(buf.getvalue())))
    assert out.mode == "L"
    if mode not in ("L", "LA"):
        assert _gray_at(receipt_ocr.preprocess(buf.getvalue()), (105, 35)) >= 240


@pytest.mark.parametrize("name", ["taxi", "restaurant", "konbini", "konbini_photo", "konbini_ipa"])
def test_no_red_pixels_output_identical(name, monkeypatch):
    """Damgasız fişlerde ön işleme çıktısı birebir aynı → önceki ölçümler (docs/OCR.md) geçerli."""
    with open(os.path.join(FIX, f"{name}.jpg"), "rb") as f:
        b = f.read()
    on = receipt_ocr.preprocess(b)
    monkeypatch.setattr(receipt_ocr, "RED_SUPPRESS", False)
    assert receipt_ocr.preprocess(b) == on


def test_suppress_red_returns_same_object_without_red():
    im = Image.new("RGB", (50, 50), (255, 255, 255))
    assert receipt_ocr.suppress_red(im) is im


def test_hue_boundaries(monkeypatch):
    """Ton/doygunluk/parlaklık eşiklerinin iki yanı (Pillow HSV 0–255)."""
    def masked(hsv):
        px = Image.new("HSV", (1, 1), hsv).convert("RGB")
        return receipt_ocr.red_mask(px).getpixel((0, 0)) == 255

    lo, hi = receipt_ocr.RED_HUE_LOW, receipt_ocr.RED_HUE_HIGH
    s, v = receipt_ocr.RED_SAT_MIN, receipt_ocr.RED_VAL_MIN
    assert masked((0, 200, 200)) and masked((lo - 1, 200, 200)) and masked((hi + 1, 200, 200)) and masked((255, 200, 200))
    assert not masked((lo + 3, 200, 200)) and not masked((hi - 3, 200, 200))   # turuncu-sarı / mor
    assert masked((0, s + 2, 200)) and not masked((0, s - 3, 200))             # doygunluk eşiği
    assert masked((0, 200, v + 2)) and not masked((0, 200, v - 3))             # parlaklık eşiği (koyu → yazı)


def test_env_toggle(monkeypatch):
    import importlib
    monkeypatch.setenv("OCR_RED_SUPPRESS", "0")
    try:
        assert importlib.reload(receipt_ocr).RED_SUPPRESS is False
        monkeypatch.delenv("OCR_RED_SUPPRESS")
        assert importlib.reload(receipt_ocr).RED_SUPPRESS is True
    finally:
        monkeypatch.delenv("OCR_RED_SUPPRESS", raising=False)
        importlib.reload(receipt_ocr)


# ---- gerçek OCR: damgalı fikstür temiz fikstürle aynı sonucu vermeli ----
EXPECTED = {
    "taxi": {"date": "2026-10-14", "store": "日本交通株式会社", "total": 3410, "total10": 3410, "total8": 0,
             "invoice_no": "T4010001054321", "category": "旅費交通費"},
    "restaurant": {"date": "2026-10-28", "store": "居酒屋 たぬき 本店", "total": 5500, "total10": 5500, "total8": 0,
                   "invoice_no": "", "category": "接待交際費"},
    "konbini": {"date": "2026-11-05", "store": "ファミリーマート 新宿西口店", "total": 850, "total10": 550,
                "total8": 300, "invoice_no": "T4013301012345", "category": "消耗品費"},
}


@needs_ocr
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_stamped_fixture_reads_like_clean(name):
    r = receipt_ocr.read_receipt(stamped_fixture(name), TODAY)
    r.pop("_raw_text", None)
    assert not r.pop("invoice_no_unverified", False)
    assert r == EXPECTED[name]

