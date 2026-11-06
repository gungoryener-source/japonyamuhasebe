"""T-028: /admin/richmenu anahtarı X-Admin-Key başlığıyla alınır; ?key= yalnızca geriye uyum."""
import sys
import types

from fastapi.testclient import TestClient


def _fake_richmenu(monkeypatch):
    calls = []
    mod = types.ModuleType("setup_richmenu")

    async def create_and_set(token, png):
        calls.append(len(png))
        return "richmenu-test"

    mod.create_and_set = create_and_set
    monkeypatch.setitem(sys.modules, "setup_richmenu", mod)
    return calls


def test_header_key_ok(bot, monkeypatch):
    calls = _fake_richmenu(monkeypatch)
    r = TestClient(bot.app).post("/admin/richmenu", headers={"X-Admin-Key": "test-admin"})
    assert r.status_code == 200 and r.json() == {"richMenuId": "richmenu-test"}
    assert len(calls) == 1 and calls[0] > 0


def test_header_key_wrong_or_missing(bot, monkeypatch):
    calls = _fake_richmenu(monkeypatch)
    c = TestClient(bot.app)
    assert c.post("/admin/richmenu", headers={"X-Admin-Key": "wrong"}).status_code == 403
    assert c.post("/admin/richmenu").status_code == 403
    assert c.post("/admin/richmenu", headers={"X-Admin-Key": ""}).status_code == 403
    assert calls == []


def test_query_key_still_accepted(bot, monkeypatch):
    calls = _fake_richmenu(monkeypatch)
    r = TestClient(bot.app).post("/admin/richmenu", params={"key": "test-admin"})
    assert r.status_code == 200 and len(calls) == 1


def test_header_takes_precedence_over_query(bot, monkeypatch):
    calls = _fake_richmenu(monkeypatch)
    c = TestClient(bot.app)
    r = c.post("/admin/richmenu", params={"key": "test-admin"}, headers={"X-Admin-Key": "wrong"})
    assert r.status_code == 403 and calls == []


def test_no_admin_key_configured(bot, monkeypatch):
    calls = _fake_richmenu(monkeypatch)
    monkeypatch.setattr(bot, "ADMIN_KEY", "")
    r = TestClient(bot.app).post("/admin/richmenu", headers={"X-Admin-Key": ""})
    assert r.status_code == 403 and calls == []
