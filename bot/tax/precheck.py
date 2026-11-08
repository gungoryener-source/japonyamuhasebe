"""申告前チェックリスト (T-081) — 帳簿から機械的に拾える抜け漏れの確認。純関数・整数のみ。

税額の判断はしない。「確認してください」の候補を出すだけで、最終判断は税理士・税務署に確認する。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

LEVELS = ("ok", "warn", "info")


@dataclass(frozen=True)
class Item:
    key: str
    level: str          # ok | warn | info
    message: str        # 日本語
    count: int = 0
    link: str = ""      # パネルの遷移先

    def to_dict(self) -> dict:
        return asdict(self)


def invoice_gaps(numbers: list[str]) -> list[str]:
    """`PREFIX-YYYY-NNNN` 形式の連番で、最小〜最大の間に欠けている番号を返す（接頭辞ごと）。"""
    groups: dict[str, list[int]] = {}
    width: dict[str, int] = {}
    for n in numbers:
        m = re.fullmatch(r"(.*?)(\d+)", n)
        if m:
            groups.setdefault(m.group(1), []).append(int(m.group(2)))
            width[m.group(1)] = len(m.group(2))
    out: list[str] = []
    for pre, nums in groups.items():
        have = set(nums)
        out += [f"{pre}{k:0{width[pre]}d}" for k in range(min(nums), max(nums) + 1) if k not in have]
    return sorted(out)


def run(*, year: int, entries: list[dict], invoices: list[dict], bank: list[dict], profile: dict,
        transitional_over: list, apportioned: dict[str, int], asset_warnings: list[str],
        unverified_keys: list[str], params_available: bool) -> list[Item]:
    items: list[Item] = []
    add = lambda *a, **k: items.append(Item(*a, **k))  # noqa: E731

    if not profile.get("business_name"):
        add("profile_name", "warn", "屋号・氏名が未設定です（請求書・決算書に使います）。", link="/settings/")
    if not profile.get("registration_no"):
        add("profile_reg", "info", "適格請求書発行事業者の登録番号が未設定です（免税事業者・未登録の場合は問題ありません）。", link="/settings/")

    exp = [e for e in entries if e["kind"] == "exp"]
    inc = [e for e in entries if e["kind"] == "inc"]
    if not entries:
        add("no_entries", "warn", f"{year}年の仕訳がありません。", link="/expenses/")
    elif not inc:
        add("no_income", "info", f"{year}年の売上の仕訳がありません。", link="/invoices/")

    noinv = [e for e in exp if e["rate"] > 0 and not e.get("invoice_no")]
    if noinv:
        add("no_invoice_no", "warn", f"登録番号のない課税仕入が{len(noinv)}件あります。経過措置（80%・70%など）の対象か確認してください。",
            len(noinv), "/expenses/")
    if transitional_over:
        add("transitional_cap", "warn", f"一の免税事業者等からの経過措置の上限を超える取引先が{len(transitional_over)}件あります。", len(transitional_over), "/tax/")

    gaps = invoice_gaps([i["no"] for i in invoices if str(i.get("issued", "")).startswith(str(year))])
    if gaps:
        add("invoice_gaps", "warn", f"請求書番号に欠番があります: {', '.join(gaps[:5])}{' ほか' if len(gaps) > 5 else ''}。", len(gaps), "/invoices/")
    unpaid = [i for i in invoices if str(i.get("issued", "")).startswith(str(year)) and i.get("status") == "unpaid"]
    if unpaid:
        add("unpaid_invoices", "info", f"未入金の請求書が{len(unpaid)}件あります（売上は発行時に計上済みか確認）。", len(unpaid), "/invoices/")

    pending = [t for t in bank if str(t["d"]).startswith(str(year)) and not t.get("invoice_no") and not t.get("entry_id")]
    if pending:
        add("bank_pending", "warn", f"消込・経費登録が済んでいない銀行明細が{len(pending)}件あります。", len(pending), "/bank/")

    mixed = {"地代家賃", "水道光熱費", "通信費"} & {e["category"] for e in exp}
    if mixed and not apportioned:
        add("apportion_unset", "info", f"{'・'.join(sorted(mixed))}の家事按分が未設定（100%＝全額事業用）です。私用分がないか確認してください。", link="/settings/")

    for w in asset_warnings:
        if "税理士" not in w:
            add("asset_warning", "warn", w, link="/assets/")

    if not params_available:
        add("params_missing", "warn", f"{year}年分の税額計算パラメータが未整備です。計算結果は参考になりません。", link="/tax/")
    elif unverified_keys:
        add("unverified_params", "warn", f"出典未確認のパラメータが{len(unverified_keys)}件あります（TODO(verify)）。該当の計算結果は仮の値です。",
            len(unverified_keys), "/tax/")

    if not any(i.level == "warn" for i in items):
        add("all_clear", "ok", "自動チェックで見つかった要確認事項はありません。")
    add("disclaimer", "info", "これは帳簿データからの確認候補です。申告前に税理士・税務署に確認してください。")
    return items
