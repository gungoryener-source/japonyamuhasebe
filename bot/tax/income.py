"""所得税の計算（個人・docs/TAX_RULES.md §2）。金額は整数円。"""
from __future__ import annotations

from dataclasses import dataclass

# 速算表: (課税所得の上限, 税率%, 控除額)
BRACKETS = (
    (1_950_000, 5, 0),
    (3_300_000, 10, 97_500),
    (6_950_000, 20, 427_500),
    (9_000_000, 23, 636_000),
    (18_000_000, 33, 1_536_000),
    (40_000_000, 40, 2_796_000),
    (None, 45, 4_796_000),
)

# 基礎控除（合計所得金額の上限, 控除額）。年ごと。TAX_RULES §2 ✅ の年のみ。
_BASIC_R8_R9 = (  # 令和8年度改正: 本則62万 + 措法41の16の2 特例（≤489万 +42万, ≤655万 +5万）
    (4_890_000, 1_040_000),
    (6_550_000, 670_000),
    (23_500_000, 620_000),
    (24_000_000, 480_000),
    (24_500_000, 320_000),
    (25_000_000, 160_000),
    (None, 0),
)
BASIC_DEDUCTION = {
    2025: (
        (1_320_000, 950_000),
        (3_360_000, 880_000),
        (4_890_000, 680_000),
        (6_550_000, 630_000),
        (23_500_000, 580_000),
        (24_000_000, 480_000),
        (24_500_000, 320_000),
        (25_000_000, 160_000),
        (None, 0),
    ),
    2026: _BASIC_R8_R9,  # 令和8年分
    2027: _BASIC_R8_R9,  # 令和9年分
    # 2028〜 (令和10年分以後): 132万超の段階が TAX_RULES で ⚠️。確定するまで未実装。
}

BLUE_RETURN = (650_000, 550_000, 100_000, 0)


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
    if blue not in BLUE_RETURN:
        raise ValueError("blue must be one of 650000/550000/100000/0")
    profit = revenue - expenses
    blue_used = min(blue, max(0, profit))
    business = profit - blue_used
    total_income = max(0, business) + max(0, other_income)
    bd = basic_deduction(total_income, year)
    deductions = bd + max(0, social_insurance) + max(0, other_deductions)
    taxable = max(0, total_income - deductions) // 1000 * 1000
    base = income_tax_on(taxable)
    recon = base * 21 // 1000
    total = (base + recon) // 100 * 100
    return IncomeTaxResult(business, blue_used, bd, taxable, base, recon, total)
