import pytest


@pytest.fixture()
def app_mod(bot):
    return bot


def test_single_rate(app_mod):
    r = app_mod.normalize_ocr({"date": "2026-10-14", "store": "JR東日本", "total": 14720, "total10": 14720,
                               "total8": 0, "invoice_no": "T7011-0016-66666", "category": "旅費交通費"})
    assert r == [{"date": "2026-10-14", "kind": "exp", "store": "JR東日本", "category": "旅費交通費",
                  "invoice_no": "T7011001666666", "amount": 14720, "rate": 10}]


def test_mixed_rates_split(app_mod):
    r = app_mod.normalize_ocr({"date": "2026-11-01", "store": "イオン", "total": 3240, "total10": 1100, "total8": 2140,
                               "invoice_no": "", "category": "会議費"})
    assert [(e["rate"], e["amount"]) for e in r] == [(10, 1100), (8, 2140)]


def test_legacy_shape_and_bad_values(app_mod):
    r = app_mod.normalize_ocr({"date": "bad", "store": "", "amount": 540, "rate": 8, "category": "謎"})
    assert r[0]["rate"] == 8 and r[0]["amount"] == 540 and r[0]["category"] == "雑費" and r[0]["store"] == "(店名不明)"
    assert len(r[0]["date"]) == 10
    assert "error" in app_mod.normalize_ocr({"total": "abc"})
    assert "error" in app_mod.normalize_ocr({"total": 0})
    assert "error" in app_mod.normalize_ocr({"error": "blurry"})


async def test_process_image_mixed(app_mod, monkeypatch, tmp_path):
    import store
    monkeypatch.chdir(tmp_path)

    async def fake_ocr(img):
        return app_mod.normalize_ocr({"date": "2026-11-01", "store": "イオン", "total10": 1100, "total8": 2140})

    monkeypatch.setattr(app_mod, "ocr_receipt", fake_ocr)
    text, options = await app_mod.process_image("OC1", b"\xff\xd8", "m/../1", "LINE")
    assert "2件" in text
    rows = store.search_entries("OC1")
    assert sorted((r["rate"], r["amount"]) for r in rows) == [(8, 2140), (10, 1100)]
    assert all(r["image_path"].startswith("receipts/") and ".." not in r["image_path"] for r in rows)


async def test_engine_selection(app_mod, monkeypatch):
    import receipt_ocr
    monkeypatch.setattr(app_mod, "OCR_ENGINE", "tesseract")
    monkeypatch.setattr(receipt_ocr, "available", lambda: False)
    assert "error" in await app_mod.ocr_receipt(b"x")

    called = []

    async def fake_claude(img):
        called.append(1)
        return [{"date": "2026-11-01", "kind": "exp", "store": "A", "category": "雑費", "invoice_no": "", "amount": 1, "rate": 10}]

    monkeypatch.setattr(app_mod, "ocr_receipt_claude", fake_claude)
    monkeypatch.setattr(app_mod, "ANTHROPIC_KEY", "k")
    monkeypatch.setattr(app_mod, "OCR_ENGINE", "auto")
    assert (await app_mod.ocr_receipt(b"x"))[0]["store"] == "A" and called
    monkeypatch.setattr(app_mod, "OCR_ENGINE", "claude")
    await app_mod.ocr_receipt(b"x")
    assert len(called) == 2
