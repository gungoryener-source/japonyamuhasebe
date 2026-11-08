"""Reviewer 2026-11-08 (2): T-024 / T-019 / T-066 kenar durumları."""
import logging
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import timing


@pytest.fixture()
def ocr(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def use(data):
        async def fake(img, reader=""):
            return bot.normalize_ocr(dict(data))
        monkeypatch.setattr(bot, "ocr_receipt", fake)
    return use


# ---------------------------------------------------------------- T-024 日付 komutu: kullanıcı ayrımı
async def test_date_command_does_not_touch_other_users_receipt(bot, ocr):
    import store
    ocr({"date": "", "store": "ファミマ", "total10": 550, "total8": 300})
    await bot.process_image("URA", b"\xff\xd8", "same-ref", "LINE")
    await bot.process_image("URB", b"\xff\xd8", "same-ref", "LINE")   # aynı mesaj ref'i
    msg, _ = bot.respond("URB", "日付 2026-11-01")
    assert "2件をまとめて変更" in msg
    today = datetime.now(bot.JST).date().isoformat()
    assert {r["d"] for r in store.search_entries("URA")} == {today}
    assert {r["d"] for r in store.search_entries("URB")} == {"2026-11-01"}


async def test_date_command_after_manual_entry_changes_only_manual(bot, ocr):
    import store
    ocr({"date": "", "store": "ファミマ", "total10": 550, "total8": 300})
    await bot.process_image("URC", b"\xff\xd8", "m1", "LINE")
    bot.respond("URC", "タクシー 2300")   # fişten sonra elle kayıt → son kayıt bu
    msg, _ = bot.respond("URC", "日付：昨日")   # tam genişlik ":"
    y = (datetime.now(bot.JST).date() - timedelta(days=1)).isoformat()
    assert msg.startswith("変更しました") and y in msg
    rows = store.search_entries("URC")
    assert [r["d"] for r in rows if r["store"] == "ファミマ"] == [datetime.now(bot.JST).date().isoformat()] * 2
    assert [r["d"] for r in rows if r["store"] != "ファミマ"] == [y]


async def test_needs_check_is_not_persisted(bot, ocr):
    import store
    ocr({"date": "", "store": "店", "total10": 1100})
    await bot.process_image("URD", b"\xff\xd8", "m2", "LINE")
    row = store.last_entry("URD")
    assert row is not None and "needs_check" not in row


async def test_confident_multi_rate_reply_has_no_warning(bot, ocr):
    ocr({"date": "2026-11-01", "store": "ファミマ", "total10": 550, "total8": 300})
    msg, options = await bot.process_image("URE", b"\xff\xd8", "m3", "LINE")
    assert "⚠️" not in msg and "確認" not in [s for _, s in options]


# ---------------------------------------------------------------- T-019 yavaş istek: hata yolu
def test_slow_request_logged_even_when_handler_raises(caplog):
    caplog.set_level(logging.WARNING, logger="tegaru.slow")
    app = FastAPI()

    @app.get("/boom/{uid}")
    def boom(uid: str):
        raise RuntimeError("x")

    wrapped = timing.SlowRequestMiddleware(app, threshold=-1)
    c = TestClient(wrapped, raise_server_exceptions=False)
    assert c.get("/boom/U-secret-id").status_code == 500
    msgs = [r.getMessage() for r in caplog.records if r.name == "tegaru.slow"]
    assert len(msgs) == 1 and "U-secret-id" not in msgs[0]


def test_non_http_scope_passthrough():
    seen = []

    async def inner(scope, receive, send):
        seen.append(scope["type"])

    import asyncio
    asyncio.run(timing.SlowRequestMiddleware(inner, threshold=-1)({"type": "lifespan"}, None, None))
    assert seen == ["lifespan"]


# ---------------------------------------------------------------- T-066 2割特例: 特定期間 sınırları (compute)
@pytest.mark.parametrize("specific,salaries,ok", [
    (10_000_000, None, True),
    (10_000_001, None, False),
    (10_000_001, 10_000_000, True),
    (10_000_001, 10_000_001, False),
    (None, 99_999_999, True),        # 特定期間売上が不明 → 確認しない
])
def test_niwari_specific_period_boundaries(specific, salaries, ok):
    from tax.consumption import Sale, compute
    kw = dict(method="niwari", tax_year=2026, base_period_sales=5_000_000,
              specific_period_sales=specific, specific_period_salaries=salaries)
    sales = [Sale(1_100_000, 10)]
    if ok:
        compute(sales, [], **kw)
    else:
        with pytest.raises(ValueError):
            compute(sales, [], **kw)
