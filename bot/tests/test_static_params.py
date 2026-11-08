"""T-080: 年分に依存しない税パラメータファイルの形と、コード側の値が正本と一致すること。"""
import pytest

from tax import consumption as ct, income as it, params

FILES = ("consumption_static", "income_static")


@pytest.mark.parametrize("name", FILES)
def test_every_param_has_source_rule_and_checked(name):
    ps = params.load_static(name)
    assert ps
    for k, p in ps.items():
        assert isinstance(p.verified, bool), k
        assert p.source and p.rule and p.checked, f"{name}:{k} に source / rule / checked が必要"


def test_all_static_params_verified_or_flagged():
    # 未検証が混ざったら気づけるようにする（現状は全て出典確認済み）
    assert [k for n in FILES for k, p in params.load_static(n).items() if not p.verified] == []


def test_consumption_values_unchanged():
    assert ct.RATES == (10, 8)
    assert ct.KANI_RATIO == {1: 90, 2: 80, 3: 70, 4: 60, 5: 50, 6: 40}
    assert ct.SMALL_BUSINESS_LIMIT == 10_000_000
    assert [(d.isoformat(), v) for d, v in ct.TRANSITIONAL_CREDIT] == [
        ("2023-10-01", 80), ("2026-10-01", 70), ("2028-10-01", 50), ("2030-10-01", 30), ("2031-10-01", 0)]
    assert [(d.isoformat(), v) for d, v in ct.TRANSITIONAL_CAP] == [("2024-10-01", 1_000_000_000), ("2026-10-01", 100_000_000)]


def test_income_values_unchanged():
    assert it.BRACKETS[0] == (1_950_000, 5, 0) and it.BRACKETS[-1] == (None, 45, 4_796_000) and len(it.BRACKETS) == 7
    assert it.RECONSTRUCTION == (21, 1000)
    assert sorted(it.BASIC_DEDUCTION) == [2025, 2026, 2027]
    assert it.BASIC_DEDUCTION[2025][0] == (1_320_000, 950_000) and it.BASIC_DEDUCTION[2025][-1] == (None, 0)
    assert it.BASIC_DEDUCTION[2026] == it.BASIC_DEDUCTION[2027] and it.BASIC_DEDUCTION[2026][0] == (4_890_000, 1_040_000)
    assert it.BLUE_RETURN == (650_000, 550_000, 100_000, 0) and it.BLUE_RETURN_FROM_2027 == (750_000, 650_000, 100_000, 0)


def test_tables_sorted_ascending():
    for tbl in (it.BRACKETS, *it.BASIC_DEDUCTION.values()):
        lims = [r[0] for r in tbl if r[0] is not None]
        assert lims == sorted(lims) and tbl[-1][0] is None
    assert [d for d, _ in ct.TRANSITIONAL_CREDIT] == sorted(d for d, _ in ct.TRANSITIONAL_CREDIT)
