"""Yapay zekâsız fiş okuma: görüntü ön işleme (Pillow) + Tesseract OCR (jpn+eng) + kural tabanlı ayrıştırıcı.

Sunucuda `tesseract` ve Japonca dil paketi gerekir (bot/Dockerfile kurar).
"""
from __future__ import annotations

import io
import shutil
import subprocess
from datetime import date

from receipt_parser import parse_receipt

import os

TESSERACT = shutil.which("tesseract")
# Ayarlar (ortam değişkeni): model klasörü (tessdata_best önerilir), hedef genişlik, ikili görüntü.
# Varsayılanlar 67 gerçek fişle ölçüldü (docs/OCR.md): tessdata_best + 1200px + ikili görüntü kapalı.
TESSDATA = os.environ.get("OCR_TESSDATA", "")
TARGET_WIDTH = int(os.environ.get("OCR_WIDTH", "1200"))
BINARIZE = os.environ.get("OCR_BINARIZE", "0") == "1"
# T-026: kırmızı / 朱色 damga (角印・丸印・認印) bastırma. Varsayılan açık; `OCR_RED_SUPPRESS=0` kapatır.
# Görselde kırmızı piksel yoksa ön işleme çıktısı birebir aynıdır (67 fişlik ölçüm etkilenmez).
RED_SUPPRESS = os.environ.get("OCR_RED_SUPPRESS", "1") != "0"
# Pillow HSV kanalları 0–255. Kırmızı tonu 0 çevresinde: H ≤ 14 (≈20°, 朱色 dahil) veya H ≥ 232 (≈327°, koyu pembe).
RED_HUE_LOW, RED_HUE_HIGH = 14, 232
RED_SAT_MIN = 70   # soluk damga mürekkebi de yakalansın; gri/siyah (S düşük) korunur
RED_VAL_MIN = 90   # damga üstündeki siyah yazının koyu kırmızımsı kenarları (V düşük) korunur
RED_HALO_LUMA = 150  # damga kenarı halesi yalnızca bu parlaklığın üstündeyse silinir (siyah yazı < ~100)


def available() -> bool:
    if not TESSERACT:
        return False
    try:
        langs = subprocess.run([TESSERACT, "--list-langs"] + (["--tessdata-dir", TESSDATA] if TESSDATA else []),
                               capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return False
    return "jpn" in langs.split()


def preprocess(img_bytes: bytes) -> bytes:
    """EXIF döndürme, kırmızı damga bastırma (T-026), gri ton, küçük görselleri büyütme, kontrast ve hafif keskinleştirme → PNG."""
    from PIL import Image, ImageFilter, ImageOps

    im = Image.open(io.BytesIO(img_bytes))
    im = ImageOps.exif_transpose(im)
    if RED_SUPPRESS and im.mode not in ("L", "1", "I", "I;16", "F"):
        im = suppress_red(im.convert("RGB"))
    im = im.convert("L")
    w, h = im.size
    if abs(w - TARGET_WIDTH) > TARGET_WIDTH * 0.15:  # termal fişler küçük yazılı; hedef genişliğe ölçekle
        scale = TARGET_WIDTH / w
        im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    im = im.filter(ImageFilter.MedianFilter(3))          # tuz-biber gürültüsü
    im = ImageOps.autocontrast(im, cutoff=2)
    if BINARIZE:
        im = im.point(lambda v, th=_otsu(im): 255 if v > th else 0)  # ikili görüntü (termal kâğıt için)
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def red_mask(rgb):
    """RGB görsel → "L" maske: damga kırmızısı pikseller 255, diğerleri 0 (yalnızca Pillow LUT işlemleri)."""
    from PIL import ImageChops

    h, s, v = rgb.convert("HSV").split()
    hue = h.point(lambda x: 255 if (x <= RED_HUE_LOW or x >= RED_HUE_HIGH) else 0)
    sat = s.point(lambda x: 255 if x >= RED_SAT_MIN else 0)
    val = v.point(lambda x: 255 if x >= RED_VAL_MIN else 0)
    return ImageChops.multiply(ImageChops.multiply(hue, sat), val)


def suppress_red(rgb):
    """Kırmızı damga piksellerini beyaza çevirir (gri tona geçmeden önce).

    朱色 damga gri tonda ~100 parlaklığa düşer ve altındaki tarih/rakamlarla birleşir; beyaza çekilince
    yalnızca siyah baskı kalır. Kırmızı piksel yoksa aynı nesne döner.
    """
    from PIL import ImageChops, ImageFilter

    mask = red_mask(rgb)
    if mask.getbbox() is None:
        return rgb
    # Damga kenarındaki açık pembe JPEG halesi: maskenin 1 px komşuluğunda ve açık renkli (siyah baskı değil)
    light = rgb.convert("L").point(lambda x: 255 if x >= RED_HALO_LUMA else 0)
    mask = ImageChops.lighter(mask, ImageChops.multiply(mask.filter(ImageFilter.MaxFilter(3)), light))
    out = rgb.copy()
    out.paste((255, 255, 255), mask=mask)
    return out


def _otsu(im) -> int:
    """Otsu eşiği (gri histogramdan)."""
    hist = im.histogram()[:256]
    total = sum(hist)
    sum_all = sum(i * h for i, h in enumerate(hist))
    w_b = sum_b = 0
    best, th = -1.0, 128
    for i, h in enumerate(hist):
        w_b += h
        if w_b == 0 or w_b == total:
            continue
        sum_b += i * h
        m_b, m_f = sum_b / w_b, (sum_all - sum_b) / (total - w_b)
        between = w_b * (total - w_b) * (m_b - m_f) ** 2
        if between > best:
            best, th = between, i
    return th


def _tesseract(png: bytes, lang: str, timeout: int) -> str:
    args = [TESSERACT, "stdin", "stdout", "-l", lang, "--psm", os.environ.get("OCR_PSM", "6"),
            "-c", "preserve_interword_spaces=1"]
    if TESSDATA:
        args[1:1] = ["--tessdata-dir", TESSDATA]
    r = subprocess.run(
        args,
        input=png, capture_output=True, timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError("tesseract failed")
    return r.stdout.decode("utf-8", errors="replace")


def ocr_text(img_bytes: bytes, timeout: int = 60) -> str:
    if not TESSERACT:
        raise RuntimeError("tesseract is not installed")
    return _tesseract(preprocess(img_bytes), "jpn", timeout)


def read_receipt(img_bytes: bytes, today: date | None = None) -> dict:
    """Görsel → normalize_ocr'ın beklediği dict (veya {"error": ...})."""
    from receipt_parser import check_digit_ok, invoice_candidates, normalize

    try:
        png = preprocess(img_bytes)
        text = _tesseract(png, "jpn", 90)
        jp_cands = invoice_candidates(normalize(text))
        latin = ""
        if not any(check_digit_ok(c[1:]) for c in jp_cands):
            # İkinci geçiş (İngilizce model, rakamlarda daha isabetli) yalnızca T番号 doğrulanamadıysa
            latin = _tesseract(png, "eng", 90)
    except Exception as ex:
        return {"error": f"OCRエラー（{type(ex).__name__}）"}
    data = parse_receipt(text, today)
    cands = invoice_candidates(normalize(latin)) + jp_cands
    valid = [c for c in cands if check_digit_ok(c[1:])]
    if valid:
        data["invoice_no"] = valid[0]
    elif cands:
        data["invoice_no"] = cands[0]
        data["invoice_no_unverified"] = True   # チェックデジット不一致 → 要確認
    data["_raw_text"] = text[:2000]  # hata ayıklama için (DB'ye yazılmaz)
    return data
