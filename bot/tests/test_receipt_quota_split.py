"""T-054: 税率ごとに分割された 1 枚のレシートは plan kotasında 1 件 sayılır."""
import pytest

import store


@pytest.fixture()
def stripe_on(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("PANEL_URL", "https://panel.example")
    monkeypatch.delenv("BILLING_ENFORCE_LIMITS", raising=False)


def _rows(uid):
    with store.tx() as con:
        return int(con.execute("SELECT COUNT(*) n FROM entries WHERE user_id=?", (uid,)).fetchone()["n"])


def _fill(bot, uid, n):
    for i in range(n):
        assert bot.respond(uid, f"コンビニ {100 + i}", "LINE")[0].startswith("登録しました")


def _two_rate(monkeypatch, bot):
    async def fake_ocr(img):
        base = {"date": "2026-11-01", "kind": "exp", "store": "スーパーA", "category": "消耗品費", "invoice_no": ""}
        return [{**base, "amount": 1080, "rate": 8}, {**base, "amount": 550, "rate": 10}]

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)


async def test_split_receipt_counts_once(bot, monkeypatch, tmp_path):
    import billing
    monkeypatch.chdir(tmp_path)
    _two_rate(monkeypatch, bot)
    msg, _ = await bot.process_image("Q1", b"jpg", "m1", "LINE")
    assert "2件に分けて記録" in msg and _rows("Q1") == 2
    assert billing.usage("Q1")["receipts"] == 1
    await bot.process_image("Q1", b"jpg", "m2", "LINE")      # 別のレシート → 2件
    bot.respond("Q1", "タクシー 2300")                        # 画像なしの入力 → 行ごと
    assert billing.usage("Q1")["receipts"] == 3 and _rows("Q1") == 5


async def test_split_receipt_at_29_stays_within_30(bot, stripe_on, monkeypatch, tmp_path):
    import billing
    monkeypatch.chdir(tmp_path)
    _fill(bot, "Q2", 29)
    _two_rate(monkeypatch, bot)
    msg, _ = await bot.process_image("Q2", b"jpg", "m1", "LINE")   # 30枚目: 可
    assert "2件に分けて記録" in msg
    assert billing.usage("Q2")["receipts"] == 30 and _rows("Q2") == 31
    msg, _ = await bot.process_image("Q2", b"jpg", "m2", "LINE")   # 31枚目: 拒否
    assert "上限（経費30件）" in msg and _rows("Q2") == 31
    assert "上限" in bot.respond("Q2", "タクシー 2300")[0]


async def test_status_reports_receipt_count(bot, stripe_on, monkeypatch, tmp_path):
    import billing
    monkeypatch.chdir(tmp_path)
    _two_rate(monkeypatch, bot)
    await bot.process_image("Q3", b"jpg", "m1", "LINE")
    assert billing.status("Q3")["usage"]["receipts"] == 1


def test_text_entries_still_count_per_row(bot, stripe_on):
    import billing
    _fill(bot, "Q4", 3)
    assert billing.usage("Q4")["receipts"] == 3
