"""消費税の計算（docs/TAX_RULES.md §1）。

金額はすべて税込・整数円。端数は切捨て。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Literal

Method = Literal["honsoku", "kani", "niwari", "sanwari"]

# 税率・経過措置・みなし仕入率・上限は bot/tax/params/consumption_static.toml（出典・確認日つき）から読む。
# 値を直接書かない（T-080）。名前は従来のまま公開する。
from tax import params as _params  # noqa: E402

_P = _params.load_static("consumption_static")
RATES: tuple[int, ...] = tuple(_P["consumption.rates"].value)
# (開始日, 控除割合 %)。開始日以後に行った課税仕入れに適用。
TRANSITIONAL_CREDIT = tuple((date.fromisoformat(d), int(pct)) for d, pct in _P["consumption.transitional_credit"].value)
KANI_RATIO = {int(k): int(v) for k, v in _P["consumption.kani_ratio"].value.items()}
SMALL_BUSINESS_LIMIT: int = int(_P["consumption.small_business_limit"].value)
# (課税期間の開始日, 上限円)。開始日以後に開始する課税期間に適用。それ以前は上限なし。
TRANSITIONAL_CAP = tuple((date.fromisoformat(d), int(y)) for d, y in _P["consumption.transitional_cap"].value)


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
    seller: str | None = None  # 取引先名（経過措置の上限判定用、任意）


@dataclass(frozen=True)
class Result:
    output_tax: int        # 売上税額
    input_tax: int         # 控除対象仕入税額
    payable: int           # 差引税額（100円未満切捨て、マイナスは還付）
    by_rate: dict          # {rate: {"sales": .., "output": .., "input": ..}}
    method: str


def _floor100(n: int) -> int:
    return (n // 100) * 100 if n >= 0 else -((-n // 100) * 100)


def method_ineligible(
    base_period_sales: int | None = None,
    specific_period_sales: int | None = None,
    specific_period_salaries: int | None = None,
) -> str | None:
    """1,000万円要件を満たさない理由（満たす／不明なら None）。2割・3割とも基準期間と特定期間を見る。

    2割特例: NTA インボイスQ&A 問115（特定期間の課税売上高による納税義務の免除の特例 消法9の2① で
    免税点制度の適用が制限される課税期間は適用不可）。3割特例: TAX_RULES §1。"""
    if base_period_sales is not None and base_period_sales > SMALL_BUSINESS_LIMIT:
        return "base_period"
    if (specific_period_sales is not None and specific_period_sales > SMALL_BUSINESS_LIMIT
            and not (specific_period_salaries is not None and specific_period_salaries <= SMALL_BUSINESS_LIMIT)):
        return "specific_period"
    return None


def _check_small_business(name: str, base: int | None, specific: int | None = None,
                          salaries: int | None = None) -> None:
    why = method_ineligible(base, specific, salaries)
    if why == "base_period":
        raise ValueError(f"{name}: 基準期間の課税売上高が1,000万円を超えています")
    if why == "specific_period":
        raise ValueError(f"{name}: 特定期間の課税売上高（および給与等支払額）が1,000万円を超えています")


def compute(
    sales: Iterable[Sale],
    purchases: Iterable[Purchase] = (),
    method: Method = "honsoku",
    *,
    kani_type: int | None = None,
    individual: bool = True,
    tax_year: int | None = None,
    base_period_sales: int | None = None,
    specific_period_sales: int | None = None,
    specific_period_salaries: int | None = None,
) -> Result:
    """課税期間の消費税を計算する。

    - honsoku: 本則課税（売上税額 − 仕入税額。経過措置を反映）
    - kani:    簡易課税（売上税額 × みなし仕入率。kani_type 1〜6 必須）
    - niwari:  2割特例（売上税額 × 80% を控除 → 納付 = 売上税額 × 20%）。令和8年分/期まで
    - sanwari: 3割特例（納付 = 売上税額 × 30%）。個人事業者の令和9年・令和10年分のみ

    base_period_sales（基準期間の課税売上高）/ specific_period_sales（特定期間の課税売上高）/
    specific_period_salaries（特定期間の給与等支払額）は任意。渡された場合のみ 2割・3割特例の
    1,000万円要件（基準期間・特定期間とも）を確認し、満たさなければ ValueError。特定期間は売上高に代えて給与等で判定できるため、
    売上高が超えていても給与等 ≤ 1,000万なら適用可。省略時は従来どおり確認しない。
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
        _check_small_business("2割特例", base_period_sales, specific_period_sales, specific_period_salaries)
        input_tax = output * 80 // 100
    elif method == "sanwari":
        if not individual:
            raise ValueError("3割特例 is for individual businesses only")
        if tax_year not in (2027, 2028):
            raise ValueError("3割特例 applies only to tax years 2027 and 2028")
        _check_small_business("3割特例", base_period_sales, specific_period_sales, specific_period_salaries)
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


def transitional_cap(period_start: date) -> int | None:
    """その課税期間に一の免税事業者等から経過措置を受けられる仕入れの上限（税込）。上限なしは None。"""
    cap = None
    for start, yen in TRANSITIONAL_CAP:
        if period_start >= start:
            cap = yen
    return cap


def transitional_cap_warnings(purchases: Iterable[Purchase], period_start: date) -> list[dict]:
    """取引先ごとに経過措置対象仕入れ（登録番号なし・課税）の税込合計が上限を超えるものを返す。

    上限を超えた部分は経過措置（仕入税額控除）の対象外。compute はこれを差し引かないため警告として表示する。
    取引先名のない仕入れは判定できないので対象外。
    戻り値: [{"seller", "gross", "cap", "excess"}]（超過額の降順）。
    """
    cap = transitional_cap(period_start)
    if cap is None:
        return []
    totals: dict[str, int] = {}
    for p in purchases:
        seller = (p.seller or "").strip()
        if p.qualified or p.rate == 0 or not seller:
            continue
        if input_credit_ratio(p.day, False) in (100, 0):
            continue  # 制度開始前／経過措置終了後は経過措置の対象外
        totals[seller] = totals.get(seller, 0) + p.gross
    out = [{"seller": k, "gross": v, "cap": cap, "excess": v - cap} for k, v in totals.items() if v > cap]
    return sorted(out, key=lambda r: (-r["excess"], r["seller"]))
