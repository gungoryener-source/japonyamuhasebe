import os
from datetime import date

import pytest

from receipt_parser import find_date, find_invoice_no, normalize, parse_receipt

TODAY = date(2026, 11, 5)

KONBINI = """ファミリーマート 新宿西口店
東京都新宿区西新宿1-1-1
TEL 03-1234-5678
登録番号 T4013301012345
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
                 "total8": 300, "invoice_no": "T4013301012345", "category": "消耗品費"}


@pytest.mark.parametrize("text,expected", [
    ("2026年11月5日", "2026-11-05"), ("2026/10/28 21:05", "2026-10-28"), ("2026-01-02", "2026-01-02"),
    ("令和8年10月14日", "2026-10-14"), ("R8.11.5", "2026-11-05"), ("令和元年5月1日", "2019-05-01"),
    ("26/11/05", "2026-11-05"), ("2026年13月40日", None), ("TEL 03-1234-5678", None),
    ("2026年1月05日(木)", "2026-11-05"),    # 曜日で修復: 1月5日は月曜 → 11月5日(木)
    ("2025年 9月18日(火)", "2025-09-16"),    # 18日は木曜 → 火曜は16日
    ("2026年11月05日(木)", "2026-11-05"),
])
def test_dates(text, expected):
    assert find_date(normalize(text), TODAY) == expected


@pytest.mark.parametrize("text,expected", [
    ("登録番号 T4013301012345", "T4013301012345"), ("T 4013-3010-12345", "T4013301012345"),
    ("T40133O1012345", "T4013301012345"), ("T501330101234", ""), ("No.T12", ""),
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
    ("konbini", "ファミリーマート 新宿西口店", 850, 550, 300, "T4013301012345", "2026-11-05", "消耗品費"),
    ("konbini_photo", "ファミリーマート 新宿西口店", 850, 550, 300, "T4013301012345", "2026-11-05", "消耗品費"),
    ("taxi", "日本交通株式会社", 3410, 3410, 0, "T4010001054321", "2026-10-14", "旅費交通費"),
    ("restaurant", "居酒屋 たぬき 本店", 5500, 5500, 0, "", "2026-10-28", "接待交際費"),
])
def test_ocr_fixtures(name, store, total, t10, t8, inv, day, cat):
    with open(os.path.join(FIX, f"{name}.jpg"), "rb") as f:
        r = receipt_ocr.read_receipt(f.read(), TODAY)
    r.pop("_raw_text", None)
    assert not r.pop("invoice_no_unverified", False)  # fikstür numaraları チェックデジット geçerli
    assert r == {"date": day, "store": store, "total": total, "total10": t10, "total8": t8, "invoice_no": inv, "category": cat}


def test_check_digit():
    from receipt_parser import check_digit_ok
    assert check_digit_ok("8220002014654") and check_digit_ok("5810773044260")
    assert not check_digit_ok("8220002014554") and not check_digit_ok("7822000201465")


def test_registration_number_with_misread_T_prefers_valid():
    from receipt_parser import find_invoice_no
    assert find_invoice_no("登録番号 : 「8220002014654") == "T8220002014654"
    assert find_invoice_no("登録番号 : 5810773044260") == "T5810773044260"
    assert find_invoice_no("T8220002014554\n登録番号 T8220002014654") == "T8220002014654"


# Gerçek fişlerden anonimleştirilmiş OCR çıktıları (kalıplar korunarak) — regresyon testleri
REAL_FAMIMA = r"""FamilyMart
七尾白馬店
登録番号 : T5810773044260
202 5年 9月1 3日
レジ袋2 0号バイオマス \5
合+ 言† \弓
(10O%対象 \3)
(内消費税等 \0)
( 8対象 \985)
(内消費税等 \72)
お 預り \1。 OOO"""

REAL_LAWSON = r"""LAWSON
登録番号:T6810205579808
(10%対象 W5)
(内消費税額 \O)
( 8%対象 311)
(内消費税額 \97)
但し 10%課税
2025年 9月23日"""

REAL_DAILY = r"""責No00000105会計5
小計 \2,065
(外8% タイソョウ \2,060)
外8% \164
(内10% タイッョり \5)
(税合計 \164)
合計 ギ\ジンジ、 2の29
合計獲得ルト 10点
2025年09月08日(月)18:06"""

REAL_VIET = r"""CHO VIET AMA
Ngay 05 thang 09 nam 2025
Teng thanh toan: y2.659
Tien thua : \0"""


def test_real_familymart_noisy_total_uses_rate_lines():
    r = parse_receipt(REAL_FAMIMA, TODAY)
    assert (r["total"], r["total10"], r["total8"], r["date"]) == (988, 3, 985, "2025-09-13")


def test_real_lawson_lost_leading_digit_repaired_by_tax():
    r = parse_receipt(REAL_LAWSON, TODAY)
    assert (r["total"], r["total10"], r["total8"]) == (1316, 5, 1311)


def test_real_exclusive_tax_lines():
    r = parse_receipt(REAL_DAILY, TODAY)
    assert (r["total"], r["total10"], r["total8"], r["date"]) == (2229, 5, 2224, "2025-09-08")


def test_real_vietnamese_receipt():
    r = parse_receipt(REAL_VIET, TODAY)
    assert (r["total"], r["date"]) == (2659, "2025-09-05")


def test_bag_fee_only_is_not_saved():
    r = parse_receipt("(10%対象 \\5)\n( 8 え計 \\671)", TODAY)
    assert "error" in r
