"""T-048b: CORS izin listesi (PANEL_URL + localhost) ve güvenlik başlıkları."""
import base64
import hashlib
import hmac
import importlib
import json

import pytest
from fastapi.testclient import TestClient

import security

PANEL = "https://jsaas-panel.onrender.com"


@pytest.fixture()
def make_client(bot, monkeypatch):
    def _make(cors=None, panel=PANEL):
        if cors is None:
            monkeypatch.delenv("CORS_ORIGINS", raising=False)
        else:
            monkeypatch.setenv("CORS_ORIGINS", cors)
        if panel is None:
            monkeypatch.delenv("PANEL_URL", raising=False)
        else:
            monkeypatch.setenv("PANEL_URL", panel)
        import app as app_module
        return TestClient(importlib.reload(app_module).app)
    return _make


# ---------------------------------------------------------------- cors_origins()

@pytest.mark.parametrize("cors", [None, "", "*", " * ", "*,https://x.example"])
def test_wildcard_or_empty_falls_back_to_panel(cors):
    env = {"PANEL_URL": PANEL + "/"}
    if cors is not None:
        env["CORS_ORIGINS"] = cors
    assert security.cors_origins(env) == [PANEL, "http://localhost:3000"]


def test_panel_url_path_and_case_normalized():
    env = {"CORS_ORIGINS": "*", "PANEL_URL": "HTTPS://Panel.Example.com/app/"}
    assert security.cors_origins(env)[0] == "https://panel.example.com"


def test_explicit_list_used_as_is():
    env = {"CORS_ORIGINS": "https://a.example, https://b.example/ ,", "PANEL_URL": PANEL}
    assert security.cors_origins(env) == ["https://a.example", "https://b.example"]


def test_no_panel_url_only_localhost_and_invalid_dropped():
    assert security.cors_origins({"CORS_ORIGINS": "*"}) == ["http://localhost:3000"]
    assert security.cors_origins({"CORS_ORIGINS": "*", "PANEL_URL": "not a url"}) == ["http://localhost:3000"]


# ---------------------------------------------------------------- HTTP davranışı

def test_allowed_origin_gets_cors_header(make_client):
    c = make_client(cors="*")
    r = c.get("/", headers={"Origin": PANEL})
    assert r.headers.get("access-control-allow-origin") == PANEL
    r = c.get("/", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_foreign_origin_gets_no_cors_header(make_client):
    c = make_client(cors="*")
    r = c.get("/", headers={"Origin": "https://evil.example"})
    assert r.status_code == 200
    assert "access-control-allow-origin" not in r.headers
    pre = c.options("/api/v1/summary", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in pre.headers


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_preflight_allows_panel_methods(make_client, method):
    """Panel PATCH /entries ve DELETE /entries, /tokens/current kullanıyor."""
    c = make_client(cors="*")
    r = c.options("/api/v1/entries/1", headers={
        "Origin": PANEL, "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": "authorization,content-type"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == PANEL
    assert method in r.headers["access-control-allow-methods"]
    assert r.headers["x-content-type-options"] == "nosniff"


def test_explicit_cors_origins_respected(make_client):
    c = make_client(cors="https://other.example")
    assert c.get("/", headers={"Origin": "https://other.example"}).headers.get(
        "access-control-allow-origin") == "https://other.example"
    assert "access-control-allow-origin" not in c.get("/", headers={"Origin": PANEL}).headers


def _assert_security_headers(r):
    for k, v in security.SECURITY_HEADERS.items():
        assert r.headers.get(k) == v, k


def test_security_headers_on_health_api_and_errors(make_client):
    c = make_client()
    _assert_security_headers(c.get("/"))
    r = c.get("/api/v1/summary")  # token yok → 401 de başlıkları taşır
    assert r.status_code == 401
    _assert_security_headers(r)
    _assert_security_headers(c.get("/does-not-exist"))


def test_security_headers_on_line_callback_and_signature_still_checked(make_client):
    c = make_client()
    body = json.dumps({"events": []}).encode()
    sig = base64.b64encode(hmac.new(b"test-secret", body, hashlib.sha256).digest()).decode()
    ok = c.post("/callback", content=body, headers={"X-Line-Signature": sig})
    assert ok.status_code == 200
    _assert_security_headers(ok)
    bad = c.post("/callback", content=body, headers={"X-Line-Signature": "bad"})
    assert bad.status_code in (400, 401, 403)
