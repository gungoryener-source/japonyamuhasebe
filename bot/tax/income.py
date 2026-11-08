"""所得税の計算（個人・docs/TAX_RULES.md §2）。金額は整数円。"""
from __future__ import annotations

from dataclasses import dataclass

from tax import params as _params

_P = _params.load_static("income_static")
_INF = -1   # 上限なし


def _table(value) -> tuple[tuple, ...]:
    return tuple(tuple(None if x == _INF and i == 0 else x for i, x in enumerate(row)) for row in value)


# 速算表: (課税所得の上限, 税率%, 控除額)。値は bot/tax/params/income_static.toml（出典・確認日つき）
BRACKETS = _table(_P["income.brackets"].value)
RECONSTRUCTION = tuple(_P["income.reconstruction_rate"].value)      # 復興特別所得税率 [分子, 分母]

# 基礎控除（合計所得金額の上限, 控除額）。年ごと。TAX_RULES §2 ✅ の年のみ。
# 令和10年分以後 (2028〜): 132万超の段階が TAX_RULES で ⚠️。確定するまで未実装。
BASIC_DEDUCTION = {int(k): _table(p.value) for k, p in
                   ((key.rsplit(".", 1)[1], prm) for key, prm in _P.items() if key.startswith("income.basic_deduction."))}

BLUE_RETURN = tuple(_P["income.blue_return.to_2026"].value)            # 令和8年分（2026）まで — TAX_RULES §2, NTA No.2072
BLUE_RETURN_FROM_2027 = tuple(_P["income.blue_return.from_2027"].value)  # 令和9年分以後（令和8年度改正）


def blue_options(year: int) -> tuple[int, ...]:
    """その年分に選べる青色申告特別控除額。"""
    return BLUE_RETURN_FROM_2027 if year >= 2027 else BLUE_RETURN


def basic_deduction(total_income: int, year: int) -> int:
    table = BASIC_DEDUCTION.get(year)
    if table is None:
        raise NotImplementedError(f"基礎控除 table for {year} is not verified yet (see docs/TAX_RULES.md §2)")
    for limit, amount in table:
        if limit is None or total_income <= limit:
            return amount
    return 0


def income_tax_on(taxable: int) -> int:
    """課税所得金額（1,000円未満切捨て後）に対する所得税額（基準所得税額）。"""
    t = max(0, taxable) // 1000 * 1000
    for limit, rate, deduct in BRACKETS:
        if limit is None or t <= limit:
            return max(0, t * rate // 100 - deduct)
    raise AssertionError("unreachable")


@dataclass(frozen=True)
class IncomeTaxResult:
    business_income: int     # 事業所得（青色控除後）
    blue_deduction: int
    basic_deduction: int
    taxable: int             # 課税所得金額（1,000円未満切捨て）
    base_tax: int            # 基準所得税額
    reconstruction: int      # 復興特別所得税
    total: int               # 申告納税額（100円未満切捨て、源泉徴収前）


def compute(
    revenue: int,
    expenses: int,
    *,
    year: int,
    blue: int = 650_000,
    social_insurance: int = 0,
    other_deductions: int = 0,
    other_income: int = 0,
) -> IncomeTaxResult:
    """事業所得者の所得税（概算）。源泉徴収税額・予定納税は考慮しない。"""
    if blue not in blue_options(year):
        raise ValueError(f"blue must be one of {'/'.join(map(str, blue_options(year)))} for {year}")
    profit = revenue - expenses
    blue_used = min(blue, max(0, profit))
    business = profit - blue_used
    total_income = max(0, business) + max(0, other_income)
    bd = basic_deduction(total_income, year)
    deductions = bd + max(0, social_insurance) + max(0, other_deductions)
    taxable = max(0, total_income - deductions) // 1000 * 1000
    base = income_tax_on(taxable)
    recon = base * RECONSTRUCTION[0] // RECONSTRUCTION[1]
    total = (base + recon) // 100 * 100
    return IncomeTaxResult(business, blue_used, bd, taxable, base, recon, total)
