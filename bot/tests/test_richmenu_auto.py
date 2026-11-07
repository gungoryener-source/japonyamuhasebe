"""Alt menü (リッチメニュー) açılışta yoksa kurulur, varsa dokunulmaz."""
import asyncio

import httpx

import setup_richmenu


def _patch(monkeypatch, has_default: bool):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((req.method, req.url.path))
        if req.method == "GET":
            return httpx.Response(200, json={"richMenuId": "rm-old"}) if has_default else httpx.Response(404, json={})
        if req.url.path == "/v2/bot/richmenu":
            return httpx.Response(200, json={"richMenuId": "rm-new"})
        return httpx.Response(200, json={})

    real = httpx.AsyncClient
    monkeypatch.setattr(setup_richmenu.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    return calls


def test_creates_when_missing(monkeypatch):
    calls = _patch(monkeypatch, has_default=False)
    assert asyncio.run(setup_richmenu.ensure_default("tok", b"png")) == "rm-new"
    assert ("POST", "/v2/bot/user/all/richmenu/rm-new") in calls


def test_skips_when_present(monkeypatch):
    calls = _patch(monkeypatch, has_default=True)
    assert asyncio.run(setup_richmenu.ensure_default("tok", b"png")) is None
    assert [m for m, _ in calls] == ["GET"]


def test_auth_error_raises_and_does_not_create(monkeypatch):
    """review: 401 等（200/404 以外）では新しいメニューを作らず例外（起動処理側でログのみ）。"""
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.method)
        return httpx.Response(401, json={"message": "Authentication failed"})

    real = httpx.AsyncClient
    monkeypatch.setattr(setup_richmenu.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    import pytest
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(setup_richmenu.ensure_default("bad", b"png"))
    assert calls == ["GET"]


def test_startup_hook_respects_switch_and_missing_token(bot, monkeypatch):
    """review: RICHMENU_AUTO=0 または token なしなら LINE API を呼ばない。"""
    called = []

    async def fake(token, png):
        called.append(token)

    monkeypatch.setattr(setup_richmenu, "ensure_default", fake)

    async def run_hook():
        await bot._auto_richmenu()
        await asyncio.sleep(0)  # 作成されたタスクがあれば走らせる
        await asyncio.sleep(0)

    monkeypatch.setattr(bot, "CHANNEL_TOKEN", "")
    asyncio.run(run_hook())
    monkeypatch.setattr(bot, "CHANNEL_TOKEN", "tok")
    monkeypatch.setenv("RICHMENU_AUTO", "0")
    asyncio.run(run_hook())
    assert called == []
    monkeypatch.setenv("RICHMENU_AUTO", "1")
    asyncio.run(run_hook())
    assert called == ["tok"]
