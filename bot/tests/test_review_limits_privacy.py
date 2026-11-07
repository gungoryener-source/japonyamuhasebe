"""Reviewer (2026-11-07): T-042b plan sınırı ve T-043 gizlilik metni ile davranışın tutarlılığı."""
import pytest

import store


@pytest.fixture()
def stripe_on(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.delenv("BILLING_ENFORCE_LIMITS", raising=False)


def _fill(bot, uid, n):
    for i in range(n):
        assert bot.respond(uid, f"コンビニ {100 + i}")[0].startswith("登録しました")


def test_panel_url_trailing_slash_single_slash(bot, stripe_on, monkeypatch):
    monkeypatch.setenv("PANEL_URL", "https://panel.example/")
    _fill(bot, "RL1", 30)
    msg = bot.limit_notice("RL1")
    assert msg and "https://panel.example/billing/" in msg and "//billing" not in msg


def test_previous_month_entries_not_counted(bot, stripe_on):
    """Sınır JST'de bu ayın created_at'ine göre: geçen ayın 30 kaydı yeni kaydı engellemez."""
    _fill(bot, "RL2", 30)
    assert bot.limit_notice("RL2")
    prev = store.today().replace(day=1).toordinal() - 1  # geçen ayın son günü
    from datetime import date
    old = date.fromordinal(prev).isoformat() + "T12:00:00+09:00"
    with store.tx() as con:
        con.execute("UPDATE entries SET created_at=? WHERE user_id=?", (old, "RL2"))
    assert bot.limit_notice("RL2") is None
    assert bot.respond("RL2", "タクシー 2300")[0].startswith("登録しました")


def test_limit_is_per_ledger(bot, stripe_on):
    _fill(bot, "RL3", 30)
    assert bot.limit_notice("RL3")
    assert bot.limit_notice("RL4") is None


async def test_receipt_image_is_stored_and_linked(bot, monkeypatch, tmp_path):
    """Gizlilik politikası (T-043) bu davranışı anlatmalı: görsel sunucuya yazılır, kayda image_path bağlanır."""
    monkeypatch.chdir(tmp_path)

    async def fake_ocr(img):
        return [{"date": "2026-11-01", "kind": "exp", "store": "A", "amount": 500, "rate": 10,
                 "category": "雑費", "invoice_no": ""}]

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)
    msg, _ = await bot.process_image("U-img-12345678", b"\xff\xd8jpg", "m/../1", "LINE")
    assert msg.startswith("登録しました")
    with store.tx() as con:
        row = con.execute("SELECT image_path FROM entries WHERE user_id=?", ("U-img-12345678",)).fetchone()
    path = row["image_path"]
    assert path.startswith("receipts/") and ".." not in path and "/" not in path[len("receipts/"):]
    assert (tmp_path / path).read_bytes() == b"\xff\xd8jpg"
