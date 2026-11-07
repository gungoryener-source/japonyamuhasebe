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
