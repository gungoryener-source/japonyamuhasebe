"""T-074: 固定資産台帳・減価償却（TAX_RULES §2 減価償却）。"""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tax import depreciation as dep
from tax import params


def A(**kw):
    base = dict(id=1, name="PC", acquired=date(2026, 7, 10), in_service=date(2026, 7, 10), cost=500_000, life=5,
                method="straight", business_pct=100)
    base.update(kw)
    return dep.Asset(**base)


def rows(asset, y0, y1):
    return {y: dep.year_row(asset, y) for y in range(y0, y1 + 1)}


# ---------------------------------------------------------------- 償却率
@pytest.mark.parametrize("life,permille", [(2, 500), (3, 334), (4, 250), (5, 200), (6, 167), (7, 143), (8, 125),
                                           (9, 112), (10, 100), (11, 91), (12, 84), (15, 67), (50, 20)])
def test_rate(life, permille):
    assert dep.straight_rate_permille(life) == permille


@pytest.mark.parametrize("life", [0, 1, 101, -3])
def test_rate_life_range(life):
    with pytest.raises(dep.AssetError):
        dep.straight_rate_permille(life)


def test_params_flags():
    p = params.load_static("depreciation")
    assert p["depreciation.rate_rule"].verified is False and p["depreciation.small_asset_annual_cap"].verified


# ---------------------------------------------------------------- 定額法・月割・備忘価額
def test_straight_month_proration_and_last_year():
    r = rows(A(), 2025, 2032)
    assert r[2025] is None
    assert (r[2026].months, r[2026].ordinary, r[2026].book_end) == (6, 50_000, 450_000)   # 7月〜12月
    assert [r[y].ordinary for y in range(2027, 2031)] == [100_000] * 4
    assert (r[2031].ordinary, r[2031].book_end) == (49_999, 1)                              # 期首帳簿価額 − 1円
    assert r[2032] is None                                                                   # 償却終了


@pytest.mark.parametrize("month,months", [(1, 12), (6, 7), (12, 1)])
def test_month_count_rule(month, months):
    row = dep.year_row(A(in_service=date(2026, month, 28), acquired=date(2026, month, 28)), 2026)
    assert row.months == months and row.ordinary == 500_000 * 200 * months // 12_000


def test_business_ratio_applies_to_expense_only():
    a = A(business_pct=60, in_service=date(2026, 1, 1), acquired=date(2026, 1, 1))
    r = dep.year_row(a, 2027)
    assert (r.ordinary, r.expense) == (100_000, 60_000)
    assert dep.year_row(a, 2027).book_end == 500_000 - 200_000        # 累計は100%基準


# ---------------------------------------------------------------- 一括・少額特例
def test_lump_three_years():
    a = A(method="lump", cost=150_001, life=0)
    ys = [dep.year_row(a, y) for y in (2026, 2027, 2028, 2029)]
    assert [r.ordinary if r else None for r in ys] == [50_000, 50_000, 50_001, None]
    assert ys[2].book_end == 0 and ys[0].months == 12


def test_small_special_full_in_year():
    a = A(method="small", cost=399_999, life=0, acquired=date(2026, 4, 1), in_service=date(2026, 4, 1))
    assert dep.year_row(a, 2026).ordinary == 399_999 and dep.year_row(a, 2027) is None


# ---------------------------------------------------------------- 検証
@pytest.mark.parametrize("kw,ok", [
    (dict(cost=99_999), False), (dict(cost=100_000), True),
    (dict(method="lump", cost=199_999, life=0), True), (dict(method="lump", cost=200_000, life=0), False),
    (dict(method="small", cost=299_999, life=0, acquired=date(2026, 3, 31), in_service=date(2026, 3, 31)), True),
    (dict(method="small", cost=300_000, life=0, acquired=date(2026, 3, 31), in_service=date(2026, 3, 31)), False),
    (dict(method="small", cost=399_999, life=0, acquired=date(2026, 4, 1), in_service=date(2026, 4, 1)), True),
    (dict(method="small", cost=400_000, life=0, acquired=date(2026, 4, 1), in_service=date(2026, 4, 1)), False),
    (dict(method="small", cost=399_999, life=0, acquired=date(2029, 4, 1), in_service=date(2029, 4, 1)), False),
    (dict(acquired=date(2007, 3, 31), in_service=date(2007, 4, 1)), False),
    (dict(acquired=date(2007, 4, 1), in_service=date(2007, 4, 1)), True),
    (dict(in_service=date(2026, 7, 9)), False), (dict(business_pct=0), False), (dict(business_pct=101), False),
    (dict(method="declining"), False), (dict(life=1), False),
])
def test_validate(kw, ok):
    if ok:
        dep.validate(A(**kw))
    else:
        with pytest.raises(dep.AssetError):
            dep.validate(A(**kw))


def test_small_limit_by_date():
    assert dep.small_asset_limit(date(2026, 3, 31)) == 300_000 and dep.small_asset_limit(date(2026, 4, 1)) == 400_000


# ---------------------------------------------------------------- 一覧表
def test_schedule_totals_and_warnings():
    smalls = [A(id=i, method="small", cost=399_999, life=0, acquired=date(2026, 5, 1), in_service=date(2026, 5, 1))
              for i in range(8)]                                    # 合計 3,199,992 > 300万
    s = dep.schedule([A(id=99, business_pct=50)] + smalls, 2026)
    assert s.total_ordinary == 50_000 + 8 * 399_999 and s.total_expense == 25_000 + 8 * 399_999
    assert any("年間合計が" in w and "超えています" in w for w in s.warnings) and any("二重計上" in w for w in s.warnings)
    assert s.warnings[-1].endswith("確認してください。") and "depreciation.rate_rule" in s.unverified


def test_schedule_empty():
    s = dep.schedule([], 2026)
    assert s.rows == [] and s.total_expense == 0 and s.unverified == []


def test_pure():
    assert dep.schedule([A()], 2027) == dep.schedule([A()], 2027)


# ---------------------------------------------------------------- API / P&L
@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "U1"}, headers={"X-Admin-Key": "test-admin"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


BODY = {"name": "ノートPC", "acquired": "2026-07-10", "in_service": "2026-07-10", "cost": 500_000, "life": 5}


def test_api_assets_and_pl(client, auth):
    assert client.get("/api/v1/assets").status_code == 401
    r = client.post("/api/v1/assets", json=BODY, headers=auth)
    assert r.status_code == 201 and r.json()["id"] and "warnings" in r.json()
    assert client.post("/api/v1/assets", json={**BODY, "cost": 50_000}, headers=auth).status_code == 400
    assert client.post("/api/v1/assets", json={**BODY, "method": "x"}, headers=auth).status_code == 422
    assert len(client.get("/api/v1/assets", headers=auth).json()) == 1
    s = client.get("/api/v1/assets/schedule?year=2026", headers=auth).json()
    assert s["total_expense"] == 50_000 and s["rows"][0]["months"] == 6
    pl = client.get("/api/v1/pl?year=2026", headers=auth).json()
    assert {"category": "減価償却費", "amount": 50_000} in pl["expenses"] and pl["expenses_total"] == 50_000
    assert client.get("/api/v1/pl?year=2025", headers=auth).json()["expenses_total"] == 0
    # 青色申告決算書 PDF と所得税の概算にも反映される
    assert client.get("/api/v1/tax/income?year=2026", headers=auth).json()["expenses"] == 50_000
    other = client.post("/api/v1/admin/tokens", json={"user_id": "U2"}, headers={"X-Admin-Key": "test-admin"}).json()["token"]
    assert client.get("/api/v1/assets", headers={"Authorization": f"Bearer {other}"}).json() == []
    aid = client.get("/api/v1/assets", headers=auth).json()[0]["id"]
    assert client.delete(f"/api/v1/assets/{aid}", headers={"Authorization": f"Bearer {other}"}).status_code == 404
    assert client.delete(f"/api/v1/assets/{aid}", headers=auth).status_code == 204
    assert client.get("/api/v1/pl?year=2026", headers=auth).json()["expenses_total"] == 0
    h = client.get("/api/v1/audit?entity=asset", headers=auth)
    assert h.status_code == 200
