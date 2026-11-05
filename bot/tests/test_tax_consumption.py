from datetime import date

import pytest

from tax.consumption import Purchase, Sale, compute, input_credit_ratio, tax_included


@pytest.mark.parametrize("gross,rate,tax", [
    (1100, 10, 100), (1080, 8, 80), (1, 10, 0), (109, 10, 9), (110, 10, 10),
    (999, 8, 74), (998, 8, 73), (0, 10, 0), (5000, 0, 0),
])
def test_tax_included(gross, rate, tax):
    assert tax_included(gross, rate) == tax


def test_bad_rate():
    with pytest.raises(ValueError):
        tax_included(1000, 5)


@pytest.mark.parametrize("d,ratio", [
    (date(2023, 9, 30), 100),
    (date(2023, 10, 1), 80),
    (date(2026, 9, 30), 80),
    (date(2026, 10, 1), 70),   # 令和8年度改正: 50 → 70
    (date(2028, 9, 30), 70),
    (date(2028, 10, 1), 50),
    (date(2030, 9, 30), 50),
    (date(2030, 10, 1), 30),
    (date(2031, 9, 30), 30),
    (date(2031, 10, 1), 0),
])
def test_transitional_ratio(d, ratio):
    assert input_credit_ratio(d, qualified=False) == ratio


def test_qualified_is_full():
    assert input_credit_ratio(date(2032, 1, 1), qualified=True) == 100


def test_rounding_per_rate_not_per_line():
    # 3件×¥105（10%）: 行ごとだと 9×3=27、税率ごと合計 315 → 28
    r = compute([Sale(105, 10)] * 3)
    assert r.output_tax == 28


def test_honsoku_mixed():
    sales = [Sale(1_100_000, 10), Sale(108_000, 8)]
    purchases = [
        Purchase(330_000, 10, date(2026, 10, 15), True),     # 30,000
        Purchase(110_000, 10, date(2026, 10, 15), False),    # 10,000 × 70% = 7,000
        Purchase(54_000, 8, date(2026, 9, 1), False),        # 4,000 × 80% = 3,200
    ]
    r = compute(sales, purchases)
    assert r.output_tax == 100_000 + 8_000
    assert r.input_tax == 30_000 + 7_000 + 3_200
    assert r.payable == 67_800
    assert r.by_rate[8]["input"] == 3_200


def test_refund_is_negative_and_rounded():
    r = compute([Sale(110_000, 10)], [Purchase(550_550, 10, date(2026, 5, 1), True)])
    assert r.payable == -40_000  # 10,000 − 50,050 = −40,050 → −40,000


def test_niwari():
    r = compute([Sale(5_500_000, 10)], method="niwari", tax_year=2026)
    assert r.output_tax == 500_000 and r.payable == 100_000


def test_niwari_expired():
    with pytest.raises(ValueError):
        compute([Sale(1100, 10)], method="niwari", tax_year=2027)


def test_sanwari_individual_2027():
    r = compute([Sale(5_500_000, 10)], method="sanwari", individual=True, tax_year=2027)
    assert r.payable == 150_000


@pytest.mark.parametrize("individual,year", [(False, 2027), (True, 2026), (True, 2029)])
def test_sanwari_rejected(individual, year):
    with pytest.raises(ValueError):
        compute([Sale(1100, 10)], method="sanwari", individual=individual, tax_year=year)


def test_kani_type5():
    r = compute([Sale(11_000_000, 10)], method="kani", kani_type=5)
    assert r.output_tax == 1_000_000 and r.payable == 500_000


def test_kani_requires_type():
    with pytest.raises(ValueError):
        compute([Sale(1100, 10)], method="kani")


def test_zero_rate_sales_ignored():
    assert compute([Sale(100_000, 0)]).output_tax == 0
