"""T-024: 低信頼の OCR 結果 → LINE で「確認」ボタン付きの要約（日付なし・税率内訳の推定）。"""
from datetime import date, datetime, timedelta

import pytest

from receipt_parser import parse_receipt

TODAY = date(2026, 11, 8)

BOTH_RATES = """ファミリーマート 新宿西口店
2026年11月05日(木)
おにぎり ※ ¥300
ボールペン ¥550
合計 ¥850
(10%対象 ¥550)
(8%対象 ¥300)
"""


# ---------------------------------------------------------------- parse_receipt: güven bayrakları
def test_confident_receipt_has_no_flags():
    r = parse_receipt(BOTH_RATES, TODAY)
    assert r["date"] == "2026-11-05" and (r["total10"], r["total8"]) == (550, 300)
    assert "date_found" not in r and "rate_breakdown_found" not in r   # güvenli → çıktı eskisiyle aynı


def test_missing_date_flagged():
    r = parse_receipt(BOTH_RATES.replace("2026年11月05日(木)\n", ""), TODAY)
    assert r["date"] is None and r["date_found"] is False
    assert "rate_breakdown_found" not in r


def test_total_only_breakdown_is_estimate():
    r = parse_receipt("文具の山田商店\n2026/11/01\nノート ¥1,200\n合計 ¥1,200\n", TODAY)
    assert (r["total10"], r["total8"]) == (1200, 0)
    assert r["rate_breakdown_found"] is False


def test_internal_tax_line_confirms_single_rate_10():
    # floor(5500 × 10 / 110) = 500 → 10% のみと確認できる
    r = parse_receipt("居酒屋 たぬき 本店\n2026/10/28\nお会計 ¥5,500\n(内消費税 ¥500)\n", TODAY)
    assert (r["total10"], r["total8"]) == (5500, 0)
    assert "rate_breakdown_found" not in r


def test_internal_tax_line_mismatch_still_estimate():
    # 5500 の 10% 内税は 500。499 は一致しない → 推定のまま
    r = parse_receipt("居酒屋 たぬき 本店\n2026/10/28\nお会計 ¥5,500\n(内消費税 ¥499)\n", TODAY)
    assert r["rate_breakdown_found"] is False


def test_internal_tax_line_confirms_single_rate_8():
    # 軽減税率のみ: floor(1080 × 8 / 108) = 80
    r = parse_receipt("やまだ青果店\n2026/11/02\n野菜 ※ ¥1,080\n※は軽減税率対象\n合計 ¥1,080\n(内消費税等 ¥80)\n", TODAY)
    assert (r["total10"], r["total8"]) == (0, 1080)
    assert "rate_breakdown_found" not in r


def test_internal_tax_boundary_one_yen_off():
    # 1099 → floor(1099×10/110) = 99（100 ではない）
    ok = parse_receipt("文具の山田商店\n2026/11/01\n合計 ¥1,099\n(内消費税 ¥99)\n", TODAY)
    ng = parse_receipt("文具の山田商店\n2026/11/01\n合計 ¥1,099\n(内消費税 ¥100)\n", TODAY)
    assert "rate_breakdown_found" not in ok and ng["rate_breakdown_found"] is False


def test_other_rate_derived_from_total_is_estimate():
    # 10% 行のみ読めて、8% 分は 合計 − 10% で推定
    r = parse_receipt("ファミリーマート 新宿西口店\n2026/11/05\n合計 ¥850\n(10%対象 ¥550)\n", TODAY)
    assert (r["total10"], r["total8"]) == (550, 300)
    assert r["rate_breakdown_found"] is False


def test_single_rate_line_equal_to_total_is_confident():
    r = parse_receipt("日本交通株式会社\n2026/10/14\n合計 ¥3,410\n(10%対象 ¥3,410)\n", TODAY)
    assert (r["total10"], r["total8"]) == (3410, 0)
    assert "rate_breakdown_found" not in r


# ---------------------------------------------------------------- normalize_ocr: needs_check
def test_normalize_confident_has_no_needs_check(bot):
    r = bot.normalize_ocr({"date": "2026-11-01", "store": "イオン", "total10": 1100, "total8": 2140})
    assert all("needs_check" not in e for e in r)


@pytest.mark.parametrize("d", ["", None, "bad", "2026-13-01"])
def test_normalize_bad_date_needs_check(bot, d):
    r = bot.normalize_ocr({"date": d, "store": "店", "total10": 1100})
    assert r[0]["needs_check"] == ["date"]


def test_normalize_flags_from_parser(bot):
    r = bot.normalize_ocr({"date": None, "date_found": False, "store": "店", "total": 1200, "total10": 1200,
                           "total8": 0, "rate_breakdown_found": False})
    assert r[0]["needs_check"] == ["date", "rate"]


def test_normalize_ai_without_breakdown_is_rate_estimate(bot):
    r = bot.normalize_ocr({"date": "2026-11-01", "store": "店", "total": 1200})   # total10/total8 なし
    assert r[0]["needs_check"] == ["rate"] and r[0]["rate"] == 10


def test_normalize_explicit_rate_is_not_estimate(bot):
    r = bot.normalize_ocr({"date": "2026-11-01", "store": "店", "amount": 540, "rate": 8})
    assert "needs_check" not in r[0] and r[0]["rate"] == 8


# ---------------------------------------------------------------- LINE yanıtı
@pytest.fixture()
def ocr(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def use(data):
        async def fake(img, reader=""):
            return bot.normalize_ocr(dict(data))
        monkeypatch.setattr(bot, "ocr_receipt", fake)
    return use


def _sends(options):
    return [s for _, s in options]


async def test_confident_reply_unchanged(bot, ocr):
    ocr({"date": "2026-11-01", "store": "文具店", "total10": 1100})
    msg, options = await bot.process_image("UC1", b"\xff\xd8", "m1", "LINE")
    e = {"date": "2026-11-01", "kind": "exp", "store": "文具店", "amount": 1100, "category": "雑費", "rate": 10,
         "invoice_no": ""}
    assert msg == bot.saved_text(e)
    assert options == bot.opts(*bot.QR_AFTER_SAVE)
    assert "確認" not in _sends(options)


async def test_missing_date_reply_asks_confirmation(bot, ocr):
    ocr({"date": "", "store": "文具店", "total10": 1100})
    msg, options = await bot.process_image("UC2", b"\xff\xd8", "m2", "LINE")
    today = datetime.now(bot.JST).date().isoformat()
    assert "日付を確認してください" in msg and today in msg and "「日付 11/3」" in msg
    s = _sends(options)
    assert s[0] == "確認" and "日付:昨日" in s and "日付:一昨日" in s and "取消" in s
    assert s[-1] == bot.CAMERA
    assert len(options) <= 13
    import store
    assert store.search_entries("UC2")[0]["d"] == today   # kayıt yine yapılır


async def test_rate_estimate_reply_warns(bot, ocr):
    ocr({"date": "2026-11-01", "store": "文具店", "total": 1200, "total10": 1200, "total8": 0,
         "rate_breakdown_found": False})
    msg, options = await bot.process_image("UC3", b"\xff\xd8", "m3", "LINE")
    assert "税率を確認してください" in msg and "日付を確認" not in msg
    s = _sends(options)
    assert s[0] == "確認" and "税率8%" in s and "税率10%" in s and "日付:昨日" not in s


async def test_multi_rate_estimate_reply(bot, ocr):
    ocr({"date": None, "date_found": False, "store": "ファミマ", "total": 850, "total10": 550, "total8": 300,
         "rate_breakdown_found": False})
    msg, options = await bot.process_image("UC4", b"\xff\xd8", "m4", "LINE")
    assert "2件に分けて記録" in msg and "日付を確認" in msg and "税率を確認" in msg
    s = _sends(options)
    assert "確認" in s and "日付:昨日" in s and "税率8%" not in s   # 1件だけの税率変更は誤解を招く


async def test_turkish_warning_and_buttons(bot, ocr):
    bot.respond("UC5", "Türkçe")
    ocr({"date": "", "store": "文具店", "total10": 1100})
    msg, options = await bot.process_image("UC5", b"\xff\xd8", "m5", "LINE")
    assert "Lütfen tarihi kontrol edin." in msg
    labels = [l for l, _ in options]
    assert "Onayla" in labels and "Tarih: dün" in labels
    # buton metni geri çevrilir → 日付:昨日 komutu
    msg, _ = bot.respond("UC5", "Tarih: dün")
    y = (datetime.now(bot.JST).date() - timedelta(days=1)).isoformat()
    assert msg.startswith("Güncellendi ✅") and y in msg


# ---------------------------------------------------------------- 確認 / 日付 komutları
def test_confirm_command(bot):
    msg, _ = bot.respond("UD0", "確認")
    assert msg == "確認する記録がありません"
    bot.respond("UD0", "タクシー 2300")
    msg, options = bot.respond("UD0", "確認")
    assert msg.startswith("確認しました") and "合計" in _sends(options)


def test_date_command_changes_last_entry(bot):
    import store
    bot.respond("UD1", "タクシー 2300")
    today = datetime.now(bot.JST).date()
    msg, _ = bot.respond("UD1", "日付:昨日")
    y = (today - timedelta(days=1)).isoformat()
    assert msg.startswith("変更しました") and y in msg
    assert store.last_entry("UD1")["d"] == y
    eid = store.last_entry("UD1")["id"]
    assert [a["action"] for a in store.audit_history("UD1", "entry", eid)][-1] == "update"   # 訂正履歴 (T-065)


def test_date_command_rejects_future_and_garbage(bot):
    import store
    bot.respond("UD2", "タクシー 2300")
    before = store.last_entry("UD2")["d"]
    future = (datetime.now(bot.JST).date() + timedelta(days=1)).strftime("%Y-%m-%d")
    for arg in (future, "abc", "2026-02-30"):
        msg, _ = bot.respond("UD2", f"日付 {arg}")
        assert msg.startswith("日付を読み取れませんでした")
    assert store.last_entry("UD2")["d"] == before


def test_date_command_without_entries(bot):
    msg, _ = bot.respond("UD3", "日付 11/3")
    assert msg == "変更する記録がありません"


async def test_date_command_updates_all_rows_of_receipt(bot, ocr):
    import store
    bot.respond("UD4", "コンビニ 100")   # 別の記録（変更されない）
    ocr({"date": "", "store": "ファミマ", "total10": 550, "total8": 300})
    await bot.process_image("UD4", b"\xff\xd8", "m6", "LINE")
    msg, _ = bot.respond("UD4", "日付 2026-11-03")
    assert "2026-11-03" in msg and "2件をまとめて変更" in msg
    ds = sorted((r["store"], r["rate"], r["d"]) for r in store.search_entries("UD4"))
    today = datetime.now(bot.JST).date().isoformat()
    assert [d for s, _, d in ds if s == "ファミマ"] == ["2026-11-03", "2026-11-03"]
    assert [d for s, _, d in ds if s != "ファミマ"] == [today]


def test_date_command_is_not_an_entry(bot):
    import store
    bot.respond("UD5", "日付 11/3")
    assert store.last_entry("UD5") is None


# ---------------------------------------------------------------- parse_date_arg sınırları
@pytest.mark.parametrize("arg,today,want", [
    ("今日", date(2026, 11, 8), date(2026, 11, 8)),
    ("昨日", date(2026, 3, 1), date(2026, 2, 28)),
    ("一昨日", date(2026, 1, 1), date(2025, 12, 30)),
    ("11/3", date(2026, 11, 8), date(2026, 11, 3)),
    ("11月3日", date(2026, 11, 8), date(2026, 11, 3)),
    ("2026/11/8", date(2026, 11, 8), date(2026, 11, 8)),      # 当日 OK
    ("2026-11-09", date(2026, 11, 8), None),                  # 未来
    ("12/28", date(2027, 1, 5), date(2026, 12, 28)),          # 年なし未来 → 去年
    ("1/5", date(2027, 1, 5), date(2027, 1, 5)),
    ("1/6", date(2027, 1, 5), date(2026, 1, 6)),
    ("2/29", date(2028, 3, 1), date(2028, 2, 29)),            # うるう年
    ("2/29", date(2027, 2, 1), None),                         # 2026-02-29 は存在しない
    ("13/1", date(2026, 11, 8), None),
    ("2026-11", date(2026, 11, 8), None),
])
def test_parse_date_arg(bot, arg, today, want):
    assert bot.parse_date_arg(arg, today) == want
