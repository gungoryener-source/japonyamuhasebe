"""T-025: LINE fiş görseli — OCR uzun sürerse önce 「読み取り中」 reply, sonuç push."""
import asyncio

import pytest

ENTRY = [{"date": "2026-11-01", "kind": "exp", "store": "ローソン", "amount": 540, "rate": 8,
          "category": "会議費", "invoice_no": ""}]


@pytest.fixture()
def line(bot, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    pushed = []

    async def fake_push(user_id, messages):
        pushed.append((user_id, messages))

    async def fake_get_image(message_id):
        return b"\xff\xd8jpg"

    monkeypatch.setattr(bot, "push", fake_push)
    monkeypatch.setattr(bot, "get_image", fake_get_image)
    bot.pushed = pushed
    return bot


def _ocr(delay, result=None, exc=None):
    async def fake(img):
        await asyncio.sleep(delay)
        if exc:
            raise exc
        return result if result is not None else [dict(e) for e in ENTRY]
    return fake


def _count(uid):
    import store
    return len(store.search_entries(uid))


async def test_fast_ocr_uses_reply_only(line, monkeypatch):
    monkeypatch.setenv("LINE_REPLY_WAIT_SEC", "5")
    monkeypatch.setattr(line, "ocr_receipt", _ocr(0))
    await line.handle_image("UA1", "tok", "m1")
    assert len(line.sent) == 1 and line.sent[0][0]["text"].startswith("登録しました")
    assert line.pushed == [] and _count("UA1") == 1


async def test_slow_ocr_reading_then_push(line, monkeypatch):
    monkeypatch.setenv("LINE_REPLY_WAIT_SEC", "0.05")
    monkeypatch.setattr(line, "ocr_receipt", _ocr(0.3))
    await line.handle_image("UA2", "tok", "m1")
    assert len(line.sent) == 1 and line.sent[0][0]["text"] == line.READING_TEXT
    assert "quickReply" not in line.sent[0][0]
    assert len(line.pushed) == 1
    uid, msgs = line.pushed[0]
    assert uid == "UA2" and msgs[0]["text"].startswith("登録しました") and "quickReply" in msgs[0]
    assert _count("UA2") == 1  # OCR zaman aşımında iptal edilmedi, tek kayıt


async def test_slow_ocr_failure_is_pushed(line, monkeypatch):
    monkeypatch.setenv("LINE_REPLY_WAIT_SEC", "0.05")
    monkeypatch.setattr(line, "ocr_receipt", _ocr(0.2, exc=RuntimeError("boom")))
    await line.handle_image("UA3", "tok", "m1")
    assert line.sent[0][0]["text"] == line.READING_TEXT
    assert line.pushed[0][1][0]["text"] == line.IMAGE_FAIL_TEXT and _count("UA3") == 0


async def test_slow_unexpected_error_still_pushes(line, monkeypatch):
    monkeypatch.setenv("LINE_REPLY_WAIT_SEC", "0.05")

    async def broken(user_id, img, ref, source):
        await asyncio.sleep(0.2)
        raise ValueError("db down")

    monkeypatch.setattr(line, "process_image", broken)
    await line.handle_image("UA4", "tok", "m1")
    assert line.sent[0][0]["text"] == line.READING_TEXT
    assert line.pushed[0][1][0]["text"] == line.IMAGE_FAIL_TEXT


async def test_fast_unexpected_error_replies(line, monkeypatch):
    monkeypatch.setenv("LINE_REPLY_WAIT_SEC", "5")

    async def broken(user_id, img, ref, source):
        raise ValueError("db down")

    monkeypatch.setattr(line, "process_image", broken)
    await line.handle_image("UA5", "tok", "m1")
    assert line.sent == [[{"type": "text", "text": line.IMAGE_FAIL_TEXT}]] and line.pushed == []


async def test_get_image_failure_replies(line, monkeypatch):
    monkeypatch.setenv("LINE_REPLY_WAIT_SEC", "5")

    async def fail(message_id):
        raise RuntimeError("404")

    monkeypatch.setattr(line, "get_image", fail)
    await line.handle_image("UA6", "tok", "m1")
    assert "画像を取得できませんでした" in line.sent[0][0]["text"] and line.pushed == []


async def test_push_error_is_swallowed(line, monkeypatch):
    monkeypatch.setenv("LINE_REPLY_WAIT_SEC", "0.05")
    monkeypatch.setattr(line, "ocr_receipt", _ocr(0.2))

    async def bad_push(user_id, messages):
        raise RuntimeError("network")

    monkeypatch.setattr(line, "push", bad_push)
    await line.handle_image("UA7", "tok", "m1")  # istisna yükselmez
    assert line.sent[0][0]["text"] == line.READING_TEXT and _count("UA7") == 1


@pytest.mark.parametrize("raw,expected", [(None, 8.0), ("3", 3.0), ("0", 0.0), ("-1", 0.0),
                                          ("999", 50.0), ("abc", 8.0)])
def test_reply_wait_seconds(bot, monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("LINE_REPLY_WAIT_SEC", raising=False)
    else:
        monkeypatch.setenv("LINE_REPLY_WAIT_SEC", raw)
    assert bot.reply_wait_seconds() == expected


async def test_push_payload(bot, monkeypatch):
    import httpx
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = request.content
        return httpx.Response(200, json={})

    real = httpx.AsyncClient
    monkeypatch.setattr(bot.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    await bot.push("U9", [{"type": "text", "text": "x"}] * 7)
    import json
    body = json.loads(seen["body"])
    assert seen["url"].endswith("/v2/bot/message/push") and seen["auth"] == "Bearer test-token"
    assert body["to"] == "U9" and len(body["messages"]) == 5
