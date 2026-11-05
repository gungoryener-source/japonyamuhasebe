import os
from datetime import date

import pytest

from receipt_parser import find_date, find_invoice_no, normalize, parse_receipt

TODAY = date(2026, 11, 5)

KONBINI = """ファミリーマート 新宿西口店
東京都新宿区西新宿1-1-1
TEL 03-1234-5678
登録番号 T5013301012345
2026年11月05日(木) 12:34
おにぎり 鮭 ※          ¥160
ボールペン             ¥330
小計                   ¥850
(109%対象              \\550)
(89対象                \\300)
合計                   ¥850
お預り                 ¥1, 000
お釣り                 ¥150
※印は軽減税率対象商品です"""


def test_konbini_text():
    r = parse_receipt(KONBINI, TODAY)
    assert r == {"date": "2026-11-05", "store": "ファミリーマート 新宿西口店", "total": 850, "total10": 550,
                 "total8": 300, "invoice_no": "T5013301012345", "category": "消耗品費"}


@pytest.mark.parametrize("text,expected", [
    ("2026年11月5日", "2026-11-05"), ("2026/10/28 21:05", "2026-10-28"), ("2026-01-02", "2026-01-02"),
    ("令和8年10月14日", "2026-10-14"), ("R8.11.5", "2026-11-05"), ("令和元年5月1日", "2019-05-01"),
    ("26/11/05", "2026-11-05"), ("2026年13月40日", None), ("TEL 03-1234-5678", None),
])
def test_dates(text, expected):
    assert find_date(normalize(text), TODAY) == expected


@pytest.mark.parametrize("text,expected", [
    ("登録番号 T5013301012345", "T5013301012345"), ("T 5013-3010-12345", "T5013301012345"),
    ("T50133O1012345", "T5013301012345"), ("T501330101234", ""), ("No.T12", ""),
])
def test_invoice_no(text, expected):
    assert find_invoice_no(normalize(text)) == expected


def test_total_ignores_change_and_tax_lines():
    r = parse_receipt("居酒屋 たぬき 本店\nお会計 ¥5,500\n(内消費税 ¥500)\nお預り ¥10,000\nお釣り ¥4,500", TODAY)
    assert r["total"] == 5500 and r["total10"] == 5500 and r["category"] == "接待交際費"


def test_amount_on_next_line_and_fullwidth():
    r = parse_receipt("日本交通株式会社\n合計金額\n￥３，４１０\n(10%対象 ¥3,410)", TODAY)
    assert r["total"] == 3410 and r["total10"] == 3410 and r["category"] == "旅費交通費"


def test_reduced_only():
    r = parse_receipt("スーパーマルエツ\n弁当 ※ ¥540\n合計 ¥540\n※は軽減税率対象", TODAY)
    assert (r["total10"], r["total8"]) == (0, 540)


def test_partial_breakdown_completed():
    r = parse_receipt("イオン 品川店\n(8%対象 ¥2,140)\n合計 ¥3,240", TODAY)
    assert (r["total10"], r["total8"]) == (1100, 2140)


def test_no_total():
    assert "error" in parse_receipt("ただの紙\nこんにちは", TODAY)
    assert "error" in parse_receipt("", TODAY)


# ---- gerçek OCR (tesseract + jpn kuruluysa) ----
import receipt_ocr  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
needs_ocr = pytest.mark.skipif(not receipt_ocr.available(), reason="tesseract + jpn not installed")


@needs_ocr
@pytest.mark.parametrize("name,store,total,t10,t8,inv,day,cat", [
    ("konbini", "ファミリーマート 新宿西口店", 850, 550, 300, "T5013301012345", "2026-11-05", "消耗品費"),
    ("konbini_photo", "ファミリーマート 新宿西口店", 850, 550, 300, "T5013301012345", "2026-11-05", "消耗品費"),
    ("taxi", "日本交通株式会社", 3410, 3410, 0, "T6010001054321", "2026-10-14", "旅費交通費"),
    ("restaurant", "居酒屋 たぬき 本店", 5500, 5500, 0, "", "2026-10-28", "接待交際費"),
])
def test_ocr_fixtures(name, store, total, t10, t8, inv, day, cat):
    with open(os.path.join(FIX, f"{name}.jpg"), "rb") as f:
        r = receipt_ocr.read_receipt(f.read(), TODAY)
    r.pop("_raw_text", None)
    assert r == {"date": day, "store": store, "total": total, "total10": t10, "total8": t8, "invoice_no": inv, "category": cat}


@needs_ocr
def test_ocr_second_pass_fixes_invoice_digits():
    # IPA fontunda Japonca model 0→9 okuyor; İngilizce ikinci geçiş T番号'nu düzeltir
    with open(os.path.join(FIX, "konbini_ipa.jpg"), "rb") as f:
        r = receipt_ocr.read_receipt(f.read(), TODAY)
    assert r["invoice_no"] == "T5013301012345" and r["total"] == 850
