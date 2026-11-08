"""Q-16: şirket fiyatlandırma ayarları — varsayılan ücretsiz, yönetici ekranından değişir."""
import pytest
from fastapi.testclient import TestClient

import pricing

ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


def signup(client, email):
    j = client.post("/api/v1/auth/signup", json={"email": email, "password": "Passw0rd!x"}).json()
    return {"Authorization": f"Bearer {j['token']}"}


def test_default_is_free_and_unlimited(client, bot):
    assert pricing.get() == {"enabled": False, "included": {"free": 1, "personal": 1, "business": 3}, "extra_price_jpy": 0}
    h = signup(client, "p0@example.com")
    for i in range(4):
        assert client.post("/api/v1/companies", json={"business_name": f"社{i}"}, headers=h).status_code == 201
    st = client.get("/api/v1/companies/pricing", headers=h).json()
    assert st["enabled"] is False and st["companies"] == 5 and st["monthly_extra_jpy"] == 0 and st["can_add"]


def test_admin_screen_auth_and_validation(client):
    assert client.get("/api/v1/admin/pricing").status_code == 401
    assert client.get("/api/v1/admin/pricing", headers=ADMIN).json()["companies"]["enabled"] is False
    bad = {"enabled": True, "included": {"free": 0, "personal": 1, "business": 3}, "extra_price_jpy": 0}
    assert client.put("/api/v1/admin/pricing", json=bad, headers=ADMIN).status_code == 400
    assert client.put("/api/v1/admin/pricing", json={**bad, "included": {"free": 1}}, headers={"X-Admin-Key": "x"}).status_code == 401


def test_limit_when_enabled_without_price(client):
    client.put("/api/v1/admin/pricing", headers=ADMIN,
               json={"enabled": True, "included": {"free": 2, "personal": 2, "business": 3}, "extra_price_jpy": 0})
    h = signup(client, "p1@example.com")
    assert client.post("/api/v1/companies", json={"business_name": "2社目"}, headers=h).status_code == 201
    r = client.post("/api/v1/companies", json={"business_name": "3社目"}, headers=h)
    assert r.status_code == 402 and "2 社まで" in r.json()["detail"]
    st = client.get("/api/v1/companies/pricing", headers=h).json()
    assert st == {"enabled": True, "companies": 2, "included": 2, "extra": 0, "monthly_extra_jpy": 0,
                  "can_add": False, "next_price_jpy": 0}


def test_extra_price_allows_and_shows_charge(client):
    client.put("/api/v1/admin/pricing", headers=ADMIN,
               json={"enabled": True, "included": {"free": 1, "personal": 1, "business": 3}, "extra_price_jpy": 500})
    h = signup(client, "p2@example.com")
    assert client.get("/api/v1/companies/pricing", headers=h).json()["next_price_jpy"] == 500
    client.post("/api/v1/companies", json={"business_name": "2社目"}, headers=h)
    client.post("/api/v1/companies", json={"business_name": "3社目"}, headers=h)
    st = client.get("/api/v1/companies/pricing", headers=h).json()
    assert st["extra"] == 2 and st["monthly_extra_jpy"] == 1000
    # 無料に戻す
    client.put("/api/v1/admin/pricing", headers=ADMIN, json={"enabled": False, "included": {}, "extra_price_jpy": 0})
    assert client.get("/api/v1/companies/pricing", headers=h).json()["monthly_extra_jpy"] == 0


def test_cors_allows_admin_key_header(bot):
    """Yönetici fiyat ekranı tarayıcıdan X-Admin-Key gönderir; CORS ön kontrolü buna izin vermeli."""
    from fastapi.testclient import TestClient
    import security
    origin = (security.cors_origins() or ["http://localhost:3000"])[0]
    c = TestClient(bot.app)
    r = c.options("/api/v1/admin/pricing", headers={
        "Origin": origin, "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "x-admin-key,content-type"})
    assert r.status_code == 200
    assert "x-admin-key" in r.headers.get("access-control-allow-headers", "").lower()
