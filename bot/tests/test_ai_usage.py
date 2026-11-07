"""AI 読み取りの選択（OCR / AI / 自動）と概算料金。"""
import io

import pytest
from fastapi.testclient import TestClient

import ai_usage

ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "UAI"}, headers=ADMIN)
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_estimates_and_formula(monkeypatch):
    assert ai_usage.image_tokens(1000, 1000) == 1296            # 公式ドキュメントの例
    assert ai_usage.image_tokens(1456, 819) == 1560
    monkeypatch.setenv("AI_PRICE_INPUT_USD_PER_MTOK", "2")
    monkeypatch.setenv("AI_PRICE_OUTPUT_USD_PER_MTOK", "10")
    monkeypatch.setenv("USD_JPY", "155")
    # レシート: 入力 500 + 2,494（1200x1600）, 出力 250 → (2994*2 + 250*10)/1e6*155 ≈ 1.32円
    assert round(ai_usage.assumed_jpy("receipt"), 2) == 1.32
    assert 1 < ai_usage.assumed_jpy("slip") < 4 and 1 < ai_usage.assumed_jpy("passbook") < 5
    monkeypatch.setenv("USD_JPY", "100")
    assert round(ai_usage.cost_jpy(1_000_000, 0)) == 200


def test_shrink_large_photo():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (3000, 4000), "white").save(buf, "JPEG")
    small = ai_usage.shrink(buf.getvalue(), "receipt")
    im = Image.open(io.BytesIO(small))
    assert max(im.size) == 1600
    assert ai_usage.shrink(b"%PDF-1.7", "receipt") == b"%PDF-1.7"
    assert ai_usage.shrink(b"not an image", "receipt") == b"not an image"


def test_record_and_measured_average(bot):
    for _ in range(5):
        ai_usage.record("receipt", {"input_tokens": 3000, "output_tokens": 200}, user_id="UAI")
    per = ai_usage.per_unit_jpy()["receipt"]
    assert per["basis"] == "measured" and per["samples"] == 5
    assert per["jpy"] == round(ai_usage.cost_jpy(3000, 200), 1)
    m = ai_usage.month_summary("UAI")
    assert m["by_kind"]["receipt"]["count"] == 5 and m["total_jpy"] > 0
    ai_usage.record("receipt", None, user_id="UAI")             # usage なし → 記録しない
    assert ai_usage.month_summary("UAI")["by_kind"]["receipt"]["count"] == 5


def test_api_settings(client, auth, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    g = client.get("/api/v1/settings/ai", headers=auth).json()
    assert g["receipt_reader"] == "" and g["ai_available"] is False and g["per_unit"]["receipt"]["basis"] == "estimate"
    assert client.put("/api/v1/settings/ai", json={"receipt_reader": "ai"}, headers=auth).status_code == 409
    assert client.put("/api/v1/settings/ai", json={"receipt_reader": "ocr"}, headers=auth).json()["receipt_reader"] == "ocr"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert client.put("/api/v1/settings/ai", json={"receipt_reader": "auto"}, headers=auth).json()["receipt_reader"] == "auto"
    assert client.put("/api/v1/settings/ai", json={"receipt_reader": "x"}, headers=auth).status_code == 422


async def test_line_reader_choice_is_used(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bot, "ANTHROPIC_KEY", "")
    msg, options = bot.respond("ULR", "読取設定")
    assert "OCR: 無料" in msg and [s for _, s in options] == ["読取設定 ocr", "読取設定 ai", "読取設定 auto"]
    msg, _ = bot.respond("ULR", "読取設定 ai")
    assert "まだ設定されていません" in msg
    monkeypatch.setattr(bot, "ANTHROPIC_KEY", "k")
    msg, _ = bot.respond("ULR", "読取設定 ai")
    assert "「AI」にしました" in msg
    seen = {}

    async def fake_ocr(img, reader=""):
        seen["reader"] = reader
        return bot.normalize_ocr({"date": "2026-11-01", "store": "店", "total10": 1100})

    monkeypatch.setattr(bot, "ocr_receipt", fake_ocr)
    text, _ = await bot.process_image("ULR", b"\xff\xd8", "r1", "LINE")
    assert seen["reader"] == "ai" and text.startswith("登録しました")
    bot.respond("ULR", "Türkçe")
    msg, _ = bot.respond("ULR", "okuma ayarı")
    assert "Fiş okuma yöntemini seçin" in msg and "yen/fiş" in msg


async def test_engine_mapping(bot, monkeypatch):
    calls = []

    async def fake_claude(img):
        calls.append("claude")
        return {"error": "x"}

    async def fake_tess(img):
        calls.append("tess")
        return {"error": "x"}

    import receipt_ocr
    monkeypatch.setattr(receipt_ocr, "available", lambda: True)
    monkeypatch.setattr(bot, "ocr_receipt_claude", fake_claude)
    monkeypatch.setattr(bot, "ocr_receipt_tesseract", fake_tess)
    monkeypatch.setattr(bot, "ANTHROPIC_KEY", "k")
    await bot.ocr_receipt(b"x", "ai")
    await bot.ocr_receipt(b"x", "auto")
    await bot.ocr_receipt(b"x", "ocr")
    assert calls == ["claude", "tess", "claude", "tess"]
    monkeypatch.setattr(bot, "ANTHROPIC_KEY", "")
    calls.clear()
    await bot.ocr_receipt(b"x", "ai")                            # キーなし → OCR にフォールバック
    assert calls == ["tess"]
