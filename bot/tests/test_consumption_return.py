"""T-071: 消費税申告書 計算（TAX_RULES §1 申告書の計算手順）+ 年分パラメータ。"""
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tax import params
from tax.consumption import Purchase, Sale
from tax.consumption_return import compute_return

Q = date(2026, 6, 1)


def line(res, key):
    return next(l for l in res.lines if l.key == key)


# ---------------------------------------------------------------- params
def test_param_years_and_schema():
    assert params.years() == [2024, 2025, 2026, 2027, 2028]
    common = None
    for y in params.years():
        ps = params.load(y)
        for p in ps.values():
            assert isinstance(p.verified, bool) and p.source and p.rule and p.checked
            if isinstance(p.value, list):
                num, den = p.value
                assert type(num) is int and type(den) is int and num > 0 and den > 0  # float 禁止
        keys = {k for k in ps if not k.startswith(("consumption.special_credit", "consumption.sanwari",
                                                   "consumption.reduced_rate"))}
        common = keys if common is None else common
        assert keys == common
    assert params.has(2026, "consumption.special_credit.niwari") and not params.has(2027, "consumption.special_credit.niwari")
    assert params.has(2027, "consumption.special_credit.sanwari") and not params.has(2026, "consumption.special_credit.sanwari")


def test_unverified_report():
    assert params.unverified(2026) == []
    assert {p.key for p in params.unverified(2027)} == {"consumption.sanwari_forms_final",
                                                        "consumption.reduced_rate_change_pending"}


def test_no_params_year():
    with pytest.raises(params.ParamsNotAvailable):
        compute_return(2023, [Sale(1100, 10)])


# ---------------------------------------------------------------- 1–2 課税標準額・消費税額
@pytest.mark.parametrize("gross,base", [
    (1_099_999, 999_000),     # 999,999 → 千円未満切捨て
    (1_100_000, 1_000_000),
    (1_101_099, 1_000_000),   # 1,000,999
    (1_101_100, 1_001_000),
    (0, 0),
])
def test_base_thousand_floor(gross, base):
    r = compute_return(2026, [Sale(gross, 10)])
    assert line(r, "base.10").value == base
    assert line(r, "output.10").value == base * 78 // 1000


def test_reduced_rate_base_and_tax():
    r = compute_return(2026, [Sale(1_080_000, 8), Sale(5_000, 0)])   # 税率0（非課税等）は除外
    assert line(r, "base.8").value == 1_000_000 and line(r, "output.8").value == 62_400
    assert line(r, "base").value == 1_000_000 and r.output_tax == 62_400


def test_nta_local_vector():
    # 差引税額 231,200 → 譲渡割額 231,200×22/78 = 65,210 → 65,200（NTA 設例 甲野商店）
    r = compute_return(2026, [Sale(3_261_500, 10)])
    assert line(r, "base.10").value == 2_965_000 and r.output_tax == 231_270
    assert r.national_payable == 231_200 and r.local_payable == 65_200
    assert r.total_payable == 296_400


# ---------------------------------------------------------------- 4–6 仕入税額
def test_purchase_warimodoshi_and_transitional():
    ps = [Purchase(1_100_000, 10, Q, True),
          Purchase(1_100_000, 10, date(2026, 9, 30), False),   # 80%
          Purchase(1_100_000, 10, date(2026, 10, 1), False),   # 70%
          Purchase(1_080_000, 8, Q, True)]
    r = compute_return(2026, [Sale(11_000_000, 10)], ps)
    assert line(r, "input.10.100").value == 78_000
    assert line(r, "input.10.80").value == 62_400
    assert line(r, "input.10.70").value == 54_600
    assert line(r, "input.8.100").value == 62_400
    assert r.credit == 78_000 + 62_400 + 54_600 + 62_400
    assert r.output_tax == 780_000 and r.national_payable == (780_000 - r.credit) // 100 * 100


def test_transitional_ratio_applied_last_per_rate():
    # 合計してから 7.8/110、最後に 70%（取引ごとではない）
    ps = [Purchase(1_099, 10, date(2026, 11, 1), False)] * 3
    r = compute_return(2026, [Sale(0, 10)], ps)
    assert line(r, "input.10.70").value == (3 * 1_099 * 78 // 1100) * 70 // 100


def test_ledger_vs_warimodoshi():
    ps = [Purchase(1_099, 10, Q, True), Purchase(1_099, 10, Q, True)]
    w = compute_return(2026, [Sale(0, 10)], ps, purchase_calc="warimodoshi")
    l = compute_return(2026, [Sale(0, 10)], ps, purchase_calc="ledger")
    assert w.credit == 2_198 * 78 // 1100 == 155
    assert l.credit == (99 + 99) * 78 // 100 == 154        # 仮払消費税 1,099×10/110=99 を仕入ごとに切捨て
    assert l.purchase_calc == "ledger"


def test_no_credit_after_transitional_end():
    r = compute_return(2026, [Sale(0, 10)], [Purchase(1_100_000, 10, date(2031, 10, 1), False)])
    assert r.credit == 0


def test_bad_purchase_calc():
    with pytest.raises(ValueError):
        compute_return(2026, [], [], purchase_calc="tsumiage")  # type: ignore[arg-type]


# ---------------------------------------------------------------- 8–9 還付
def test_refund():
    r = compute_return(2026, [], [Purchase(1_100_000, 10, Q, True)])
    assert r.national_refund == 78_000 and r.national_payable == 0
    assert r.local_refund == 22_000 and r.local_payable == 0
    assert r.total_payable == -100_000
    assert line(r, "national_refund").value == 78_000


def test_payable_hundred_floor_boundary():
    # 消費税額 78,099 → 78,000 / 78,100 → 78,100
    a = compute_return(2026, [Sale(1_101_100, 10)])           # base 1,001,000 → 78,078
    assert a.national_payable == 78_000
    assert compute_return(2026, [Sale(1_102_200, 10)]).national_payable == 78_100   # base 1,002,000 → 78,156


# ---------------------------------------------------------------- 11–13 簡易・2割・3割
def test_kani():
    r = compute_return(2026, [Sale(3_261_500, 10)], method="kani", kani_type=5)
    assert r.credit == 231_270 * 50 // 100
    assert any(w.code == "kani_single_business" for w in r.warnings)
    with pytest.raises(ValueError):
        compute_return(2026, [Sale(1, 10)], method="kani", kani_type=7)


def test_niwari():
    r = compute_return(2026, [Sale(3_261_500, 10)], method="niwari")
    assert r.credit == 231_270 * 80 // 100 == 185_016
    assert r.national_payable == 46_200 and r.local_payable == 13_000
    assert any(w.code == "eligibility_unchecked" for w in r.warnings)
    with pytest.raises(ValueError):
        compute_return(2027, [Sale(1, 10)], method="niwari")
    with pytest.raises(ValueError):
        compute_return(2026, [Sale(1, 10)], method="niwari", base_period_sales=10_000_001)
    ok = compute_return(2026, [Sale(1, 10)], method="niwari", base_period_sales=10_000_000)
    assert not any(w.code == "eligibility_unchecked" for w in ok.warnings)


def test_sanwari():
    r = compute_return(2027, [Sale(3_261_500, 10)], method="sanwari")
    assert r.credit == 231_270 * 70 // 100 == 161_889
    assert r.national_payable == 69_300
    assert "consumption.sanwari_forms_final" in r.unverified
    assert any(w.code == "sanwari_forms_draft" for w in r.warnings)
    with pytest.raises(ValueError):
        compute_return(2026, [Sale(1, 10)], method="sanwari")
    with pytest.raises(ValueError):
        compute_return(2027, [Sale(1, 10)], method="sanwari", individual=False)
    with pytest.raises(ValueError):
        compute_return(2028, [Sale(1, 10)], method="sanwari", specific_period_sales=10_000_001)
    compute_return(2028, [Sale(1, 10)], method="sanwari", specific_period_sales=10_000_001,
                   specific_period_salaries=10_000_000)   # 給与等で判定


def test_unknown_method():
    with pytest.raises(ValueError):
        compute_return(2026, [], method="foo")  # type: ignore[arg-type]


# ---------------------------------------------------------------- 警告・根拠・純粋性
def test_reduced_rate_pending_warning_only_2027_plus():
    w26 = compute_return(2026, [Sale(1_080, 8)])
    w27 = compute_return(2027, [Sale(1_080, 8)])
    w27std = compute_return(2027, [Sale(1_100, 10)])
    code = "reduced_rate_change_pending"
    assert not any(w.code == code for w in w26.warnings)
    assert any(w.code == code for w in w27.warnings) and code.join(["consumption.", ""]) in w27.unverified
    assert not any(w.code == code for w in w27std.warnings) and w27std.unverified == []


def test_trace_and_disclaimer():
    r = compute_return(2026, [Sale(3_261_500, 10)], [Purchase(110_000, 10, Q, True)])
    for l in r.lines:
        assert l.rule.startswith("申告書#") and isinstance(l.value, int) and l.formula
    assert line(r, "base.10").inputs == {"taxable_sales_gross": 3_261_500}
    assert all(l.verified for l in r.lines) and r.unverified == []
    assert r.warnings[-1].code == "disclaimer" and "税理士" in r.warnings[-1].message
    assert r.total_payable == r.national_payable + r.local_payable


def test_pure_and_serializable():
    args = (2026, [Sale(1_234_567, 10), Sale(98_765, 8)], [Purchase(54_321, 10, Q, False)])
    a, b = compute_return(*args), compute_return(*args)
    assert a == b
    json.dumps(a.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------- API
@pytest.fixture()
def client(bot):
    return TestClient(bot.app)


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/admin/tokens", json={"user_id": "U1"}, headers={"X-Admin-Key": "test-admin"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _entry(client, auth, **kw):
    body = {"date": "2026-10-05", "kind": "exp", "store": "JR東日本", "amount": 11000,
            "category": "旅費交通費", "rate": 10, "invoice_no": "T7011001666666"}
    body.update(kw)
    assert client.post("/api/v1/entries", json=body, headers=auth).status_code == 201


def test_api_return(client, auth):
    assert client.get("/api/v1/tax/consumption/return?year=2026").status_code == 401
    _entry(client, auth, kind="inc", store="A社", amount=3_261_500, category="売上高", invoice_no="")
    _entry(client, auth, date="2026-10-15", amount=110_000, invoice_no="")   # 経過措置 70%
    r = client.get("/api/v1/tax/consumption/return?year=2026", headers=auth)
    assert r.status_code == 200
    j = r.json()
    assert j["output_tax"] == 231_270 and j["credit"] == 7_800 * 70 // 100
    assert j["national_payable"] == 225_800 and j["local_payable"] == 63_600
    assert any(l["key"] == "input.10.70" for l in j["lines"]) and j["transitional_over_cap"] == []
    n = client.get("/api/v1/tax/consumption/return?year=2026&method=niwari", headers=auth).json()
    assert n["national_payable"] == 46_200
    assert client.get("/api/v1/tax/consumption/return?year=2027&method=niwari", headers=auth).status_code == 400
    assert client.get("/api/v1/tax/consumption/return?year=2023", headers=auth).status_code == 409
    assert client.get("/api/v1/tax/consumption/return?year=2026&purchase_calc=x", headers=auth).status_code == 422
