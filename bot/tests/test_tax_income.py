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


@pytest.mark.parametrize("year", [2026, 2027])
@pytest.mark.parametrize("income,ded", [
    (0, 1_040_000), (1_320_000, 1_040_000), (1_320_001, 1_040_000), (3_360_001, 1_040_000),
    (4_890_000, 1_040_000), (4_890_001, 670_000),
    (6_550_000, 670_000), (6_550_001, 620_000),
    (23_500_000, 620_000), (23_500_001, 480_000),
    (24_000_000, 480_000), (24_000_001, 320_000),
    (24_500_000, 320_000), (24_500_001, 160_000),
    (25_000_000, 160_000), (25_000_001, 0),
])
def test_basic_deduction_2026_2027(year, income, ded):
    # TAX_RULES §2 令和8年分・令和9年分（NTA 年末調整のしかた 102.pdf, No.1199）
    assert basic_deduction(income, year) == ded


@pytest.mark.parametrize("year", [2024, 2028])
def test_basic_deduction_unverified_years(year):
    with pytest.raises(NotImplementedError):
        basic_deduction(5_000_000, year)


def test_example_2026():
    # 事業所得 3,000,000（青色控除なし）→ 基礎控除 104万 → 課税 196万
    r = compute(3_000_000, 0, year=2026, blue=0)
    assert r.business_income == 3_000_000 and r.basic_deduction == 1_040_000
    assert r.taxable == 1_960_000
    assert r.base_tax == 98_500             # 196万×10% − 97,500
    assert r.reconstruction == 2_068        # 98,500 × 2.1% 切捨て
    assert r.total == 100_500               # 100,568 → 100円未満切捨て


def test_full_example_2026_same_input_as_2025():
    # 2025 例と同じ入力: 435万 ≤489万 → 基礎104万, 社保60万 → 課税 271万
    r = compute(8_000_000, 3_000_000, year=2026, social_insurance=600_000)
    assert r.basic_deduction == 1_040_000 and r.taxable == 2_710_000
    assert r.base_tax == 173_500 and r.total == 177_100


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


# ---------------------------------------------------------------- T-049: 青色申告特別控除 令和9年分以後
def test_blue_options_by_year():
    from tax import income as it
    assert it.blue_options(2026) == (650_000, 550_000, 100_000, 0)
    assert it.blue_options(2027) == (750_000, 650_000, 100_000, 0)
    assert it.blue_options(2030) == it.blue_options(2027)


def test_blue_validation_2026_vs_2027():
    import pytest as _pt
    from tax import income as it
    it.compute(5_000_000, 0, year=2026, blue=550_000)
    with _pt.raises(ValueError):
        it.compute(5_000_000, 0, year=2026, blue=750_000)
    r = it.compute(5_000_000, 0, year=2027, blue=750_000)
    assert r.blue_deduction == 750_000
    with _pt.raises(ValueError):
        it.compute(5_000_000, 0, year=2027, blue=550_000)
    assert it.compute(300_000, 0, year=2027, blue=750_000).blue_deduction == 300_000   # 所得を超えない
