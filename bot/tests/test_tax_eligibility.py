"""T-050: 2割/3割特例の 1,000万円要件 と 経過措置 一の免税事業者等 上限（docs/TAX_RULES.md §1）。"""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tax.consumption import (
    Purchase, Sale, compute, method_ineligible, transitional_cap, transitional_cap_warnings,
)

S = [Sale(1_100_000, 10)]  # 売上税額 100,000


# ---------------------------------------------------------------- 2割特例: 基準期間
@pytest.mark.parametrize("base", [None, 0, 9_999_999, 10_000_000])
def test_niwari_base_period_ok(base):
    r = compute(S, method="niwari", tax_year=2026, base_period_sales=base)
    assert (r.output_tax, r.input_tax, r.payable) == (100_000, 80_000, 20_000)


def test_niwari_base_period_over_rejected():
    with pytest.raises(ValueError, match="基準期間"):
        compute(S, method="niwari", tax_year=2026, base_period_sales=10_000_001)


# ---------------------------------------------------------------- 2割特例: 特定期間 (T-066)
# NTA インボイスQ&A 問115: 消法9の2①（特定期間）で免税点制度の適用が制限される課税期間は 2割特例不可。
# 特定期間は課税売上高に代えて給与等支払額で判定できる（どちらかが ≤ 1,000万なら免税判定は可）。
def _niwari(**kw):
    return compute(S, method="niwari", tax_year=2026, **kw)


@pytest.mark.parametrize("kw", [
    dict(specific_period_sales=0),
    dict(specific_period_sales=10_000_000),
    dict(specific_period_sales=10_000_001, specific_period_salaries=10_000_000),
    dict(specific_period_sales=50_000_000, specific_period_salaries=0),
    dict(specific_period_salaries=50_000_000),  # 給与等のみ超過・売上高不明 → 判定しない
    dict(specific_period_sales=9_000_000, specific_period_salaries=50_000_000),
])
def test_niwari_specific_period_ok(kw):
    assert _niwari(**kw).payable == 20_000


@pytest.mark.parametrize("kw", [
    dict(specific_period_sales=10_000_001),
    dict(specific_period_sales=50_000_000),
    dict(specific_period_sales=10_000_001, specific_period_salaries=10_000_001),
    dict(base_period_sales=10_000_000, specific_period_sales=10_000_001),
])
def test_niwari_specific_period_over_rejected(kw):
    with pytest.raises(ValueError, match="2割特例: 特定期間"):
        _niwari(**kw)


def test_niwari_base_checked_before_specific():
    with pytest.raises(ValueError, match="基準期間"):
        _niwari(base_period_sales=10_000_001, specific_period_sales=10_000_001)


def test_niwari_honsoku_unaffected_by_specific():
    # 本則・簡易は 1,000万円要件を見ない
    assert compute(S, method="honsoku", specific_period_sales=10**10).payable == 100_000


# ---------------------------------------------------------------- 3割特例: 基準期間 + 特定期間
def _sanwari(**kw):
    return compute(S, method="sanwari", individual=True, tax_year=2027, **kw)


def test_sanwari_boundaries_ok():
    r = _sanwari(base_period_sales=10_000_000, specific_period_sales=10_000_000)
    assert (r.input_tax, r.payable) == (70_000, 30_000)


def test_sanwari_base_over():
    with pytest.raises(ValueError, match="基準期間"):
        _sanwari(base_period_sales=10_000_001, specific_period_sales=0)


def test_sanwari_specific_over():
    with pytest.raises(ValueError, match="特定期間"):
        _sanwari(base_period_sales=0, specific_period_sales=10_000_001)


def test_sanwari_specific_sales_over_but_salaries_ok():
    # 特定期間は課税売上高に代えて給与等支払額で判定できる
    assert _sanwari(specific_period_sales=10_000_001, specific_period_salaries=10_000_000).payable == 30_000


def test_sanwari_specific_sales_and_salaries_over():
    with pytest.raises(ValueError, match="特定期間"):
        _sanwari(specific_period_sales=10_000_001, specific_period_salaries=10_000_001)


def test_params_omitted_keep_old_behaviour():
    assert _sanwari().payable == 30_000
    assert compute(S, method="niwari", tax_year=2026).payable == 20_000


def test_honsoku_and_kani_ignore_limits():
    big = dict(base_period_sales=10**10, specific_period_sales=10**10)
    assert compute(S, **big).payable == 100_000
    assert compute(S, method="kani", kani_type=5, **big).payable == 50_000


def test_method_ineligible():
    assert method_ineligible() is None
    assert method_ineligible(10_000_000, 10_000_000) is None
    assert method_ineligible(10_000_001) == "base_period"
    assert method_ineligible(None, 10_000_001) == "specific_period"
    assert method_ineligible(None, 10_000_001, 10_000_000) is None


# ---------------------------------------------------------------- 経過措置 上限
@pytest.mark.parametrize("start,cap", [
    (date(2023, 10, 1), None),
    (date(2024, 9, 30), None),
    (date(2024, 10, 1), 1_000_000_000),
    (date(2026, 1, 1), 1_000_000_000),
    (date(2026, 9, 30), 1_000_000_000),
    (date(2026, 10, 1), 100_000_000),
    (date(2027, 1, 1), 100_000_000),
])
def test_transitional_cap_by_period_start(start, cap):
    assert transitional_cap(start) == cap


def P(gross, seller, d=date(2027, 3, 1), qualified=False, rate=10):
    return Purchase(gross, rate, d, qualified, seller)


def test_cap_exact_is_ok_one_yen_over_is_flagged():
    ps = [P(60_000_000, "A商店"), P(40_000_000, "A商店"),   # ちょうど 1億 → OK
          P(100_000_001, "B工業")]                        # 1億+1 → 警告
    assert transitional_cap_warnings(ps, date(2027, 1, 1)) == [
        {"seller": "B工業", "gross": 100_000_001, "cap": 100_000_000, "excess": 1}]


def test_cap_excludes_qualified_nontaxable_unnamed_and_out_of_scope():
    ps = [
        P(100_000_000, "C"),
        P(1, "C", qualified=True),                  # 適格 → 対象外
        P(1, "C", rate=0),                          # 非課税 → 対象外
        P(200_000_000, ""),                         # 取引先名なし → 判定不可
        P(200_000_000, None),
        P(1, "C", d=date(2031, 10, 1)),             # 経過措置終了後 (0%)
    ]
    assert transitional_cap_warnings(ps, date(2027, 1, 1)) == []


def test_cap_sellers_merged_after_strip_and_sorted_by_excess():
    ps = [P(100_000_000, " D "), P(5, "D"), P(100_000_010, "E")]
    rows = transitional_cap_warnings(ps, date(2027, 1, 1))
    assert [(r["seller"], r["excess"]) for r in rows] == [("E", 10), ("D", 5)]


def test_cap_ten_oku_for_periods_before_2026_10():
    ps = [P(999_999_999, "F", d=date(2026, 5, 1)), P(1, "F", d=date(2026, 5, 1))]
    assert transitional_cap_warnings(ps, date(2026, 1, 1)) == []
    ps.append(P(1, "F", d=date(2026, 5, 1)))
    assert transitional_cap_warnings(ps, date(2026, 1, 1))[0]["excess"] == 1
    assert transitional_cap_warnings(ps, date(2024, 1, 1)) == []  # 上限なし


# ---------------------------------------------------------------- API
ADMIN = {"X-Admin-Key": "test-admin"}


@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "UELIG"}, headers=ADMIN)
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_api_eligibility_params(client, auth):
    base = "/api/v1/tax/consumption?year=2026&method=niwari"
    assert client.get(base + "&base_period_sales=10000000", headers=auth).status_code == 200
    r = client.get(base + "&base_period_sales=10000001", headers=auth)
    assert r.status_code == 400 and "基準期間" in r.json()["detail"]
    assert client.get(base + "&base_period_sales=-1", headers=auth).status_code == 422


@pytest.mark.parametrize("q,status", [
    ("&specific_period_sales=10000000", 200),
    ("&specific_period_sales=10000001", 400),
    ("&specific_period_sales=10000001&specific_period_salaries=10000000", 200),
    ("&specific_period_sales=10000001&specific_period_salaries=10000001", 400),
    ("&specific_period_sales=-1", 422),
])
def test_api_niwari_specific_period(client, auth, q, status):  # T-066
    r = client.get("/api/v1/tax/consumption?year=2026&method=niwari" + q, headers=auth)
    assert r.status_code == status, r.text
    if status == 400:
        assert "特定期間" in r.json()["detail"]


def test_api_reports_cap_fields(client, auth):
    r = client.get("/api/v1/tax/consumption?year=2027", headers=auth).json()
    assert r["transitional_cap"] == 100_000_000
    assert r["transitional_over_cap"] == []
    r = client.get("/api/v1/tax/consumption?year=2026", headers=auth).json()
    assert r["transitional_cap"] == 1_000_000_000


def test_api_flags_seller_over_cap(client, auth):
    exp = {"date": "2027-02-01", "kind": "exp", "store": "G商事", "amount": 100_000_001,
           "category": "消耗品費", "rate": 10, "invoice_no": ""}
    assert client.post("/api/v1/entries", json=exp, headers=auth).status_code == 201
    ok = dict(exp, store="H商店", amount=100_000_000)
    assert client.post("/api/v1/entries", json=ok, headers=auth).status_code == 201
    r = client.get("/api/v1/tax/consumption?year=2027", headers=auth).json()
    assert r["transitional_over_cap"] == [{"seller": "G商事", "gross": 100_000_001, "cap": 100_000_000, "excess": 1}]
