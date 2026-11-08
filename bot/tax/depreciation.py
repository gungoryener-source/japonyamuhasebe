"""減価償却費の計算（個人事業者, T-074）。docs/TAX_RULES.md §2 「減価償却」。

対象: 平成19年4月1日以後に取得した資産の **定額法**（通常）／一括償却資産／少額減価償却資産の特例。
定率法・旧定額法・除却売却・特別償却は未対応（登録時に拒否または警告）。
純粋関数・整数円。パラメータは tax/params/depreciation.toml（verified=false は TODO(verify)）。
計算結果であり税務相談ではない。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable, Literal

from tax import params

Method = Literal["straight", "lump", "small"]
METHODS: tuple[str, ...] = ("straight", "lump", "small")


class AssetError(ValueError):
    """登録できない資産（理由は日本語）。"""


def _p(key: str) -> params.Param:
    return params.load_static("depreciation")[key]


def straight_rate_permille(life: int) -> int:
    """定額法の償却率 ×1000（= ceil(1000/耐用年数)）。0.200 → 200。規則は未照合（TAX_RULES ⚠️）。"""
    lo, hi = _p("depreciation.life_range").value
    if not lo <= life <= hi:
        raise AssetError(f"耐用年数は{lo}〜{hi}年で指定してください")
    return -(-1000 // life)


def small_asset_limit(acquired: date) -> int:
    """少額減価償却資産の特例の上限（未満）。取得日で版が変わる。"""
    limit = 0
    for start, yen in _p("depreciation.small_asset_limits").value:
        if acquired >= date.fromisoformat(start):
            limit = yen
    return limit


@dataclass(frozen=True)
class Asset:
    id: int
    name: str
    acquired: date          # 取得日
    in_service: date        # 事業供用日（月割の起点）
    cost: int               # 取得価額
    life: int               # 耐用年数（straight のみ使用）
    method: Method = "straight"
    business_pct: int = 100  # 事業専用割合 %


def validate(a: Asset) -> list[str]:
    """登録時の検証。拒否は AssetError、続行できる注意は警告文のリストで返す。"""
    warns: list[str] = []
    if a.method not in METHODS:
        raise AssetError("償却方法は straight / lump / small のいずれかです")
    if not 1 <= a.business_pct <= 100:
        raise AssetError("事業専用割合は1〜100%で指定してください")
    if a.cost <= 0:
        raise AssetError("取得価額は1円以上で指定してください")
    if a.in_service < a.acquired:
        raise AssetError("事業供用日は取得日以後にしてください")
    if a.acquired < date.fromisoformat(_p("depreciation.acquired_from").value):
        raise AssetError("平成19年3月31日以前に取得した資産（旧定額法・旧定率法）は未対応です")
    expense_limit = _p("depreciation.expense_limit").value
    if a.cost < expense_limit:
        raise AssetError(f"取得価額{expense_limit:,}円未満は固定資産台帳の対象外です（消耗品費などで全額を経費にします）")
    if a.method == "straight":
        straight_rate_permille(a.life)
    elif a.method == "lump":
        if a.cost >= _p("depreciation.lump_limit").value:
            raise AssetError(f"一括償却資産は取得価額{_p('depreciation.lump_limit').value:,}円未満の資産が対象です")
    else:  # small
        lim = small_asset_limit(a.acquired)
        if a.cost >= lim:
            raise AssetError(f"少額減価償却資産の特例は取得価額{lim:,}円未満の資産が対象です（取得日 {a.acquired}）")
        if a.in_service > date.fromisoformat(_p("depreciation.small_asset_deadline").value):
            raise AssetError("少額減価償却資産の特例の適用期限（令和11年3月31日）を過ぎています")
        warns.append("少額減価償却資産の特例は青色申告者が対象で、年間の合計は300万円までです。")
    return warns


@dataclass(frozen=True)
class YearRow:
    asset_id: int
    name: str
    method: str
    cost: int
    life: int | None
    rate_permille: int | None
    months: int                 # 本年中の償却期間（月）
    ordinary: int               # 本年分の普通償却費
    business_pct: int
    expense: int                # 本年分の必要経費算入額
    book_end: int               # 本年末の未償却残高
    note: str = ""


def _ordinary_by_year(a: Asset, up_to: int) -> dict[int, tuple[int, int]]:
    """{年: (普通償却費, 月数)}。up_to 年まで。事業専用割合は掛けない（累計・備忘価額の判定は100%基準）。"""
    out: dict[int, tuple[int, int]] = {}
    y0 = a.in_service.year
    if a.method == "small":
        out[y0] = (a.cost, 12)
    elif a.method == "lump":
        third = a.cost // 3
        for i, y in enumerate((y0, y0 + 1, y0 + 2)):
            out[y] = (third if i < 2 else a.cost - 2 * third, 12)
    else:
        rate = straight_rate_permille(a.life)
        acc = 0
        y = y0
        while y <= up_to:
            months = 13 - a.in_service.month if y == y0 else 12
            calc = (a.cost * rate * months) // (12 * 1000)
            book = a.cost - acc
            dep = max(0, min(calc, book - 1))   # 備忘価額1円を残す（最終年 = 期首帳簿価額 − 1円）
            out[y] = (dep, months)
            acc += dep
            if book - dep <= 1:
                break
            y += 1
    return out


def year_row(a: Asset, year: int) -> YearRow | None:
    """指定年の償却行。その年に償却がなければ None（供用前・償却終了）。"""
    by_year = _ordinary_by_year(a, year)
    if year not in by_year:
        return None
    ordinary, months = by_year[year]
    acc_after = sum(v[0] for y, v in by_year.items() if y <= year)
    expense = ordinary * a.business_pct // 100
    method_note = {"straight": "", "lump": "一括償却資産（3年均等）", "small": "少額減価償却資産の特例"}[a.method]
    return YearRow(a.id, a.name, a.method, a.cost, a.life if a.method == "straight" else None,
                   straight_rate_permille(a.life) if a.method == "straight" else None,
                   months, ordinary, a.business_pct, expense, a.cost - acc_after, method_note)


@dataclass(frozen=True)
class Schedule:
    year: int
    rows: list[YearRow]
    total_ordinary: int
    total_expense: int          # 決算書 ⑱ 減価償却費 に入る額
    warnings: list[str]
    unverified: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def schedule(assets: Iterable[Asset], year: int) -> Schedule:
    assets = list(assets)
    rows = [r for a in assets if (r := year_row(a, year)) is not None]
    warns: list[str] = []
    small_total = sum(a.cost for a in assets if a.method == "small" and a.in_service.year == year)
    cap = _p("depreciation.small_asset_annual_cap").value
    if small_total > cap:
        warns.append(f"少額減価償却資産の特例の年間合計が{cap:,}円を超えています（超過分は通常の減価償却になります）。")
    if any(a.method == "straight" for a in assets):
        warns.append("償却率は規則（耐用年数から算出）に基づく暫定値です。耐用年数省令の別表と照合してください。")
    if rows:
        warns.append("この資産を経費としても別に登録している場合は二重計上になります。")
    warns.append("これは帳簿データからの計算結果です。申告前に税理士・税務署に確認してください。")
    unverified = sorted(k for k in ("depreciation.rate_rule", "depreciation.expense_limit", "depreciation.lump_limit")
                        if rows and not params.load_static("depreciation")[k].verified)
    return Schedule(year, rows, sum(r.ordinary for r in rows), sum(r.expense for r in rows), warns, unverified)
