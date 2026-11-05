"""Yapay zekâsız fiş okuma: görüntü ön işleme (Pillow) + Tesseract OCR (jpn+eng) + kural tabanlı ayrıştırıcı.

Sunucuda `tesseract` ve Japonca dil paketi gerekir (bot/Dockerfile kurar).
"""
from __future__ import annotations

import io
import shutil
import subprocess
from datetime import date

from receipt_parser import parse_receipt

TESSERACT = shutil.which("tesseract")


def available() -> bool:
    if not TESSERACT:
        return False
    try:
        langs = subprocess.run([TESSERACT, "--list-langs"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return False
    return "jpn" in langs.split()


def preprocess(img_bytes: bytes) -> bytes:
    """Gri ton, EXIF döndürme, küçük görselleri büyütme, kontrast ve hafif keskinleştirme → PNG."""
    from PIL import Image, ImageFilter, ImageOps

    im = Image.open(io.BytesIO(img_bytes))
    im = ImageOps.exif_transpose(im).convert("L")
    w, h = im.size
    if w < 1400:  # termal fiş fotoğrafları genelde küçük yazılı; ~1600px genişlik iyi sonuç verir
        scale = 1600 / w
        im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    elif w > 2600:
        scale = 2200 / w
        im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    im = im.filter(ImageFilter.MedianFilter(3))          # tuz-biber gürültüsü
    im = ImageOps.autocontrast(im, cutoff=2)
    im = im.point(lambda v, th=_otsu(im): 255 if v > th else 0)  # ikili görüntü (termal kâğıt için)
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


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
    r = subprocess.run(
        [TESSERACT, "stdin", "stdout", "-l", lang, "--psm", "6", "-c", "preserve_interword_spaces=1"],
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
    try:
        png = preprocess(img_bytes)
        text = _tesseract(png, "jpn", 60)
        # İkinci geçiş (İngilizce model): rakam dizilerinde daha isabetli → T 番号 doğrulaması
        latin = _tesseract(png, "eng", 60)
    except Exception as ex:
        return {"error": f"OCRエラー（{type(ex).__name__}）"}
    data = parse_receipt(text, today)
    from receipt_parser import find_invoice_no, normalize
    alt = find_invoice_no(normalize(latin))
    if alt and "error" not in data:
        data["invoice_no"] = alt
    data["_raw_text"] = text[:2000]  # hata ayıklama için (DB'ye yazılmaz)
    return data
