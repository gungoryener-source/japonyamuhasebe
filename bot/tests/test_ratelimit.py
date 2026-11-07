"""T-048: bellek içi hız sınırı (login / signup / password-reset / OCR) → 429 + Retry-After."""
import pytest
from fastapi.testclient import TestClient

import ratelimit

ADMIN = {"X-Admin-Key": "test-admin"}


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture()
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(ratelimit, "_now", c)
    return c


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def ip(addr):
    return {"X-Forwarded-For": f"{addr}, 10.0.0.1"}


def login(client, addr="203.0.113.1"):
    return client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrongpass1"},
                       headers=ip(addr))


def test_login_limit_boundary_and_window(client, clock):
    for _ in range(10):
        assert login(client).status_code == 401          # N=10 geçer (hesap yok → 401)
    r = login(client)
    assert r.status_code == 429                           # N+1
    assert r.json()["detail"] == ratelimit.DETAIL
    assert r.headers["Retry-After"] == "60"
    clock.t += 30
    r = login(client)
    assert r.status_code == 429 and r.headers["Retry-After"] == "30"
    clock.t += 30                                         # pencere doldu
    assert login(client).status_code == 401
    # reddedilen istekler sayılmaz: pencere içinde 9 hak daha var
    for _ in range(9):
        assert login(client).status_code == 401
    assert login(client).status_code == 429


def test_different_ips_independent(client, clock):
    for _ in range(10):
        login(client, "203.0.113.1")
    assert login(client, "203.0.113.1").status_code == 429
    assert login(client, "203.0.113.2").status_code == 401


def test_rules_independent(client, clock):
    for _ in range(10):
        login(client)
    assert login(client).status_code == 429
    r = client.post("/api/v1/auth/password-reset/request", json={"email": "a@example.com"}, headers=ip("203.0.113.1"))
    assert r.status_code == 202


def test_signup_limit(client, clock):
    for i in range(5):
        r = client.post("/api/v1/auth/signup", json={"email": f"u{i}@example.com", "password": "password123"},
                        headers=ip("198.51.100.7"))
        assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/signup", json={"email": "u9@example.com", "password": "password123"},
                    headers=ip("198.51.100.7"))
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_password_reset_limit(client, clock):
    for _ in range(5):
        assert client.post("/api/v1/auth/password-reset/request", json={"email": "x@example.com"},
                           headers=ip("198.51.100.8")).status_code == 202
    assert client.post("/api/v1/auth/password-reset/request", json={"email": "x@example.com"},
                       headers=ip("198.51.100.8")).status_code == 429


def test_ocr_limit(client, bot, clock, monkeypatch):
    async def fake(img):
        return [{"date": "2026-11-01", "kind": "exp", "store": "S", "category": "会議費", "invoice_no": "",
                 "amount": 100, "rate": 10}]
    monkeypatch.setattr(bot, "ocr_receipt", fake)
    tok = client.post("/api/v1/admin/tokens", json={"user_id": "U1"}, headers=ADMIN).json()["token"]
    h = {"Authorization": f"Bearer {tok}", **ip("192.0.2.5")}
    for _ in range(20):
        assert client.post("/api/v1/receipts/ocr", content=b"IMG", headers=h).status_code == 200
    assert client.post("/api/v1/receipts/ocr", content=b"IMG", headers=h).status_code == 429


def test_health_and_other_endpoints_unaffected(client, clock):
    for _ in range(11):
        login(client)
    assert login(client).status_code == 429
    for _ in range(30):
        assert client.get("/", headers=ip("203.0.113.1")).status_code == 200
    assert client.get("/api/v1/billing/plans", headers=ip("203.0.113.1")).status_code == 200


def test_env_override_and_disable(client, clock, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "2/10")
    assert login(client).status_code == 401
    assert login(client).status_code == 401
    r = login(client)
    assert r.status_code == 429 and r.headers["Retry-After"] == "10"
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "0")
    assert all(login(client).status_code == 401 for _ in range(15))
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "bozuk")
    assert ratelimit.limit_for("login") == ratelimit.DEFAULTS["login"]


def test_client_ip_proxy_hops(monkeypatch):
    class R:
        def __init__(self, xff, host="127.0.0.9"):
            self.headers = {"x-forwarded-for": xff} if xff else {}
            self.client = type("C", (), {"host": host})()
    assert ratelimit.client_ip(R("1.1.1.1, 2.2.2.2")) == "1.1.1.1"
    assert ratelimit.client_ip(R("")) == "127.0.0.9"
    monkeypatch.setenv("RATE_LIMIT_PROXY_HOPS", "1")
    assert ratelimit.client_ip(R("spoofed, 1.1.1.1")) == "1.1.1.1"
    monkeypatch.setenv("RATE_LIMIT_PROXY_HOPS", "5")
    assert ratelimit.client_ip(R("1.1.1.1")) == "1.1.1.1"


def test_memory_bound(clock, monkeypatch):
    monkeypatch.setattr(ratelimit, "MAX_KEYS", 5)
    for i in range(5):
        assert ratelimit.hit("login", f"k{i}") is None
    clock.t += 61                                         # hepsinin penceresi doldu → temizlenir
    assert ratelimit.hit("login", "new") is None
    assert len(ratelimit._hits) == 1
    for i in range(10):                                   # canlı anahtarlar sınırı aşarsa en eskisi atılır
        ratelimit.hit("login", f"live{i}")
    assert len(ratelimit._hits) <= 5
