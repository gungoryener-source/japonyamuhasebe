"""消費税の計算（docs/TAX_RULES.md §1）。

金額はすべて税込・整数円。端数は切捨て。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Literal

RATES = (10, 8)
Method = Literal["honsoku", "kani", "niwari", "sanwari"]

# 免税事業者等からの課税仕入れに係る経過措置（令和8年度改正後）
# (開始日, 控除割合 %)。開始日以後に行った課税仕入れに適用。
TRANSITIONAL_CREDIT = (
    (date(2023, 10, 1), 80),
    (date(2026, 10, 1), 70),
    (date(2028, 10, 1), 50),
    (date(2030, 10, 1), 30),
    (date(2031, 10, 1), 0),
)

# 簡易課税 みなし仕入率（第1種〜第6種）%。docs/TAX_RULES.md §1 ✅
# 出典: 国税庁 タックスアンサー No.6505（令和8年4月1日現在法令等）、事業区分は No.6509（確認 2026-11-06）
KANI_RATIO = {1: 90, 2: 80, 3: 70, 4: 60, 5: 50, 6: 40}


def tax_included(gross: int, rate: int) -> int:
    """税込金額に含まれる消費税額（切捨て）。rate は 10 / 8 / 0。"""
    if rate == 0 or gross <= 0:
        return 0
    if rate not in RATES:
        raise ValueError(f"unsupported rate: {rate}")
    return (gross * rate) // (100 + rate)


def input_credit_ratio(purchase_date: date, qualified: bool) -> int:
    """仕入税額控除の割合（%）。適格請求書があれば100。"""
    if qualified:
        return 100
    if purchase_date < TRANSITIONAL_CREDIT[0][0]:
        return 100  # インボイス制度開始前（区分記載請求書）
    ratio = 0
    for start, pct in TRANSITIONAL_CREDIT:
        if purchase_date >= start:
            ratio = pct
    return ratio


@dataclass(frozen=True)
class Sale:
    gross: int
    rate: int


@dataclass(frozen=True)
class Purchase:
    gross: int
    rate: int
    day: date
    qualified: bool  # 適格請求書（登録番号）あり


@dataclass(frozen=True)
class Result:
    output_tax: int        # 売上税額
    input_tax: int         # 控除対象仕入税額
    payable: int           # 差引税額（100円未満切捨て、マイナスは還付）
    by_rate: dict          # {rate: {"sales": .., "output": .., "input": ..}}
    method: str


def _floor100(n: int) -> int:
    return (n // 100) * 100 if n >= 0 else -((-n // 100) * 100)


def compute(
    sales: Iterable[Sale],
    purchases: Iterable[Purchase] = (),
    method: Method = "honsoku",
    *,
    kani_type: int | None = None,
    individual: bool = True,
    tax_year: int | None = None,
) -> Result:
    """課税期間の消費税を計算する。

    - honsoku: 本則課税（売上税額 − 仕入税額。経過措置を反映）
    - kani:    簡易課税（売上税額 × みなし仕入率。kani_type 1〜6 必須）
    - niwari:  2割特例（売上税額 × 80% を控除 → 納付 = 売上税額 × 20%）。令和8年分/期まで
    - sanwari: 3割特例（納付 = 売上税額 × 30%）。個人事業者の令和9年・令和10年分のみ
    """
    sales = list(sales)
    purchases = list(purchases)
    by_rate: dict[int, dict[str, int]] = {r: {"sales": 0, "output": 0, "input": 0} for r in RATES}

    for s in sales:
        if s.rate == 0:
            continue
        by_rate[s.rate]["sales"] += s.gross
    for r in RATES:
        # 税率ごとに合計してから1回だけ端数処理
        by_rate[r]["output"] = tax_included(by_rate[r]["sales"], r)
    output = sum(v["output"] for v in by_rate.values())

    if method == "honsoku":
        for p in purchases:
            if p.rate == 0:
                continue
            ratio = input_credit_ratio(p.day, p.qualified)
            by_rate[p.rate]["input"] += tax_included(p.gross, p.rate) * ratio // 100
        input_tax = sum(v["input"] for v in by_rate.values())
    elif method == "kani":
        if kani_type not in KANI_RATIO:
            raise ValueError("kani_type must be 1..6")
        input_tax = output * KANI_RATIO[kani_type] // 100
    elif method == "niwari":
        if tax_year is not None and tax_year > 2026:
            raise ValueError("2割特例 is available only through 2026 (令和8年)")
        input_tax = output * 80 // 100
    elif method == "sanwari":
        if not individual:
            raise ValueError("3割特例 is for individual businesses only")
        if tax_year not in (2027, 2028):
            raise ValueError("3割特例 applies only to tax years 2027 and 2028")
        input_tax = output * 70 // 100
    else:
        raise ValueError(f"unknown method: {method}")

    return Result(output, input_tax, _floor100(output - input_tax), by_rate, method)


def transitional_breakdown(purchases: Iterable[Purchase]) -> list[dict]:
    """登録番号のない課税仕入れを控除割合ごとに集計（経過措置の内訳表示用）。

    戻り値: [{"ratio": 70, "gross": 税込合計, "tax": 含まれる税額, "credited": 控除額}]（割合の降順）。
    税額・控除額は compute(honsoku) と同じく取引ごとに端数処理して合計する。
    """
    groups: dict[int, dict[str, int]] = {}
    for p in purchases:
        if p.qualified or p.rate == 0:
            continue
        ratio = input_credit_ratio(p.day, False)
        if ratio == 100:
            continue  # インボイス制度開始前
        tax = tax_included(p.gross, p.rate)
        g = groups.setdefault(ratio, {"ratio": ratio, "gross": 0, "tax": 0, "credited": 0})
        g["gross"] += p.gross
        g["tax"] += tax
        g["credited"] += tax * ratio // 100
    return [groups[k] for k in sorted(groups, reverse=True)]
