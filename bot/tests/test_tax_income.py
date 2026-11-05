import pytest

from tax.income import basic_deduction, compute, income_tax_on


@pytest.mark.parametrize("taxable,tax", [
    (0, 0),
    (1_950_000, 97_500),
    (1_951_000, 97_600),          # 10% − 97,500
    (3_300_000, 232_500),
    (3_301_000, 232_700),         # 20% − 427,500
    (6_950_000, 962_500),
    (9_000_000, 1_434_000),
    (18_000_000, 4_404_000),
    (40_000_000, 13_204_000),
    (50_000_000, 17_704_000),
    (1_950_999, 97_500),          # 1,000円未満切捨て
])
def test_brackets(taxable, tax):
    assert income_tax_on(taxable) == tax


@pytest.mark.parametrize("income,ded", [
    (1_320_000, 950_000), (1_320_001, 880_000), (3_360_000, 880_000), (4_890_000, 680_000),
    (6_550_000, 630_000), (23_500_000, 580_000), (24_000_000, 480_000), (25_000_001, 0),
])
def test_basic_deduction_2025(income, ded):
    assert basic_deduction(income, 2025) == ded


def test_basic_deduction_2026_not_verified():
    with pytest.raises(NotImplementedError):
        basic_deduction(5_000_000, 2026)


def test_full_example_2025():
    # 売上 800万 − 経費 300万 = 500万, 青色65万 → 435万, 基礎68万, 社保60万 → 課税 307万
    r = compute(8_000_000, 3_000_000, year=2025, social_insurance=600_000)
    assert r.business_income == 4_350_000
    assert r.basic_deduction == 680_000
    assert r.taxable == 3_070_000
    assert r.base_tax == 209_500           # 307万×10% − 97,500
    assert r.reconstruction == 4_399       # 209,500 × 2.1% 切捨て
    assert r.total == 213_800              # 213,899 → 100円未満切捨て


def test_blue_capped_by_profit():
    r = compute(1_000_000, 700_000, year=2025)
    assert r.blue_deduction == 300_000 and r.business_income == 0 and r.total == 0


def test_loss():
    r = compute(500_000, 900_000, year=2025)
    assert r.blue_deduction == 0 and r.total == 0


def test_bad_blue():
    with pytest.raises(ValueError):
        compute(1, 0, year=2025, blue=123)
