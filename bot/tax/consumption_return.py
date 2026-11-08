"""消費税及び地方消費税 申告書（第一表・第二表相当）の計算（T-071）。

docs/TAX_RULES.md §1 「消費税申告書の計算手順」に従う。国税（7.8% / 6.24%）と地方消費税（22/78）を分けて計算し、
すべての数値に「どこから来たか」（式・入力・規則・検証状態）を付ける。税率・端数単位はすべて
`tax.params` の年分パラメータから読む（コードに直書きしない）。

- 売上税額は割戻し計算（原則）のみ。積上げ（特例）は交付した請求書の税額データがないため未対応。
- 仕入税額: 割戻し（特例、売上も割戻しなので可）／帳簿積上げ（仮払消費税 10/110・8/108 を仕入ごとに切捨て）。
- 免税事業者等からの仕入れ: 同じ方法で計算し、経過措置の控除割合を税率ごと最後に掛ける（申告書#6）。
- 売上返還等・貸倒れ・中間納付・控除過大調整は未反映（警告を出す）。

純粋関数: 同じ入力 → 同じ出力。I/O は tax.params の TOML 読み込み（キャッシュ）のみ。
これは計算結果であり税務相談ではない。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Literal

from tax import params
from tax.consumption import Purchase, Sale, input_credit_ratio, method_ineligible

Method = Literal["honsoku", "kani", "niwari", "sanwari"]
PurchaseCalc = Literal["warimodoshi", "ledger"]

_RATE_KEY = {10: "standard", 8: "reduced"}
_RATE_LABEL = {10: "7.8%", 8: "6.24%"}


@dataclass(frozen=True)
class Line:
    key: str            # 機械用キー（例 "base.10"）
    label: str          # 申告書上の名称（日本語）
    value: int          # 円
    formula: str        # 計算式（人が読める）
    rule: str           # TAX_RULES §1 申告書#n
    verified: bool      # 使ったパラメータがすべて verified か
    inputs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Warning_:
    code: str
    message: str


@dataclass(frozen=True)
class ReturnResult:
    year: int
    method: str
    purchase_calc: str
    output_tax: int           # 課税標準額に対する消費税額（国税）
    credit: int               # 控除税額（控除対象仕入税額 / 特別控除税額）
    national_payable: int     # 差引税額（国税・百円未満切捨て）
    national_refund: int      # 控除不足還付税額（国税）
    local_payable: int        # 譲渡割額 納税額
    local_refund: int         # 譲渡割額 還付額
    total_payable: int        # 納付税額合計（還付なら負）
    lines: list[Line]
    warnings: list[Warning_]
    unverified: list[str]     # 計算に使った verified=false パラメータ（TODO(verify)）

    def to_dict(self) -> dict:
        return asdict(self)


def _mul(n: int, frac: tuple[int, int]) -> int:
    """n × 分数 の1円未満切捨て（負数は 0 方向）。"""
    num, den = frac
    return n * num // den if n >= 0 else -((-n) * num // den)


def _floor_unit(n: int, unit: int) -> int:
    return (n // unit) * unit


def compute_return(
    year: int,
    sales: Iterable[Sale],
    purchases: Iterable[Purchase] = (),
    method: Method = "honsoku",
    *,
    kani_type: int | None = None,
    individual: bool = True,
    purchase_calc: PurchaseCalc = "warimodoshi",
    base_period_sales: int | None = None,
    specific_period_sales: int | None = None,
    specific_period_salaries: int | None = None,
) -> ReturnResult:
    """年分（個人=暦年）の消費税申告書相当の数値を計算する。要件を満たさない入力は ValueError。"""
    P = params.load(year)  # 年分パラメータがなければ ParamsNotAvailable
    used: dict[str, params.Param] = {}

    def prm(key: str) -> params.Param:
        p = params.get(year, key)
        used[key] = p
        return p

    def ok(*keys: str) -> bool:
        return all(used[k].verified for k in keys)

    if purchase_calc not in ("warimodoshi", "ledger"):
        raise ValueError(f"unknown purchase_calc: {purchase_calc}")
    sales = [s for s in sales if s.rate in _RATE_KEY]
    purchases = [p for p in purchases if p.rate in _RATE_KEY]
    lines: list[Line] = []
    warnings: list[Warning_] = []

    # ---- 1–2. 課税標準額・消費税額（税率ごと、割戻し計算）
    base_unit = prm("consumption.base_round").value
    output = 0
    total_base = 0
    for rate, rk in _RATE_KEY.items():
        gross = sum(s.gross for s in sales if s.rate == rate)
        br, nr = prm(f"consumption.base_ratio.{rk}"), prm(f"consumption.national_rate.{rk}")
        base = _floor_unit(_mul(gross, br.frac), base_unit)
        tax = _mul(base, nr.frac)
        total_base += base
        output += tax
        lines.append(Line(f"base.{rate}", f"課税標準額（{_RATE_LABEL[rate]}適用分）", base,
                          f"floor({gross:,} × {br.frac[0]}/{br.frac[1]}, {base_unit:,}円)", "申告書#1",
                          ok(br.key, "consumption.base_round"), {"taxable_sales_gross": gross}))
        lines.append(Line(f"output.{rate}", f"消費税額（{_RATE_LABEL[rate]}適用分）", tax,
                          f"floor({base:,} × {nr.frac[0]}/{nr.frac[1]})", "申告書#2", ok(nr.key), {"base": base}))
    lines.append(Line("base", "課税標準額", total_base, "税率ごとの課税標準額の合計", "申告書#1",
                      all(l.verified for l in lines if l.key.startswith("base.")), {}))
    lines.append(Line("output", "消費税額", output, "税率ごとの消費税額の合計", "申告書#2",
                      all(l.verified for l in lines if l.key.startswith("output.")), {}))

    # ---- 控除税額
    if method == "honsoku":
        credit = 0
        tsumiage = prm("consumption.tsumiage_ratio") if purchase_calc == "ledger" else None
        groups: dict[tuple[int, int], list[Purchase]] = {}
        for p in purchases:
            groups.setdefault((p.rate, input_credit_ratio(p.day, p.qualified)), []).append(p)
        for (rate, ratio), ps in sorted(groups.items(), key=lambda kv: (-kv[0][0], -kv[0][1])):
            rk = _RATE_KEY[rate]
            gross = sum(p.gross for p in ps)
            if purchase_calc == "warimodoshi":
                ir = prm(f"consumption.input_ratio.{rk}")
                tax = _mul(gross, ir.frac)
                formula = f"floor({gross:,} × {ir.frac[0]}/{ir.frac[1]})"
                v = ok(ir.key)
            else:
                lt = prm(f"consumption.ledger_tax.{rk}")
                ledger = sum(_mul(p.gross, lt.frac) for p in ps)
                tax = _mul(ledger, tsumiage.frac)  # type: ignore[union-attr]
                formula = f"floor(Σfloor(仕入 × {lt.frac[0]}/{lt.frac[1]}) = {ledger:,} × {tsumiage.frac[0]}/{tsumiage.frac[1]})"  # type: ignore[union-attr]
                v = ok(lt.key, "consumption.tsumiage_ratio")
            credited = tax * ratio // 100
            if ratio != 100:
                formula += f" × {ratio}/100（経過措置）"
            credit += credited
            label = "控除対象仕入税額" + ("" if ratio == 100 else f"（適格請求書なし・控除{ratio}%）")
            lines.append(Line(f"input.{rate}.{ratio}", f"{label}（{_RATE_LABEL[rate]}適用分）", credited, formula,
                              "申告書#4-6", v, {"purchases_gross": gross, "count": len(ps), "credit_ratio": ratio}))
        credit_label, credit_rule, credit_ok = "控除対象仕入税額", "申告書#4-6", all(
            l.verified for l in lines if l.key.startswith("input."))
    elif method == "kani":
        table = prm("consumption.kani_ratio")
        if kani_type is None or str(kani_type) not in table.value:
            raise ValueError("kani_type must be 1..6")
        ratio = int(table.value[str(kani_type)])
        credit = output * ratio // 100
        credit_label, credit_rule, credit_ok = f"控除対象仕入税額（第{kani_type}種 みなし仕入率{ratio}%）", "申告書#11", table.verified
        warnings.append(Warning_("kani_single_business",
                                 "簡易課税は単一の事業区分として計算しています。2種類以上の事業がある場合は税理士・税務署に確認してください。"))
    elif method in ("niwari", "sanwari"):
        key = f"consumption.special_credit.{method}"
        name = "2割特例" if method == "niwari" else "3割特例"
        if not params.has(year, key):
            raise ValueError(f"{name} は{year}年分には適用できません")
        if method == "sanwari" and not individual:
            raise ValueError("3割特例は個人事業者のみです")
        why = method_ineligible(base_period_sales, specific_period_sales, specific_period_salaries)
        if why == "base_period":
            raise ValueError(f"{name}: 基準期間の課税売上高が1,000万円を超えています")
        if why == "specific_period":
            raise ValueError(f"{name}: 特定期間の課税売上高（および給与等支払額）が1,000万円を超えています")
        sc = prm(key)
        credit = _mul(output, sc.frac)
        credit_label, credit_rule, credit_ok = f"特別控除税額（{name}）", "申告書#12" if method == "niwari" else "申告書#13", sc.verified
        if base_period_sales is None:
            warnings.append(Warning_("eligibility_unchecked",
                                     f"{name}の適用要件（基準期間・特定期間の課税売上高1,000万円以下など）は確認していません。"))
    else:
        raise ValueError(f"unknown method: {method}")

    formula = "Σ控除対象仕入税額" if method == "honsoku" else f"floor({output:,} × 割合)"
    lines.append(Line("credit", credit_label, credit, formula, credit_rule, credit_ok, {}))

    # ---- 8. 差引税額 / 控除不足還付税額（国税）
    unit = prm("consumption.payable_round").value
    diff = output - credit
    if diff >= 0:
        national_payable, national_refund = _floor_unit(diff, unit), 0
        lines.append(Line("national_payable", "差引税額", national_payable,
                          f"floor({output:,} − {credit:,}, {unit}円)", "申告書#8", ok("consumption.payable_round"), {}))
    else:
        national_payable, national_refund = 0, -diff
        lines.append(Line("national_refund", "控除不足還付税額", national_refund, f"{credit:,} − {output:,}",
                          "申告書#8", True, {}))

    # ---- 9. 地方消費税（譲渡割額）
    lr = prm("consumption.local_ratio")
    if national_payable:
        local_payable, local_refund = _floor_unit(_mul(national_payable, lr.frac), unit), 0
        lines.append(Line("local_payable", "譲渡割額（納税額）", local_payable,
                          f"floor({national_payable:,} × {lr.frac[0]}/{lr.frac[1]}, {unit}円)", "申告書#9",
                          ok(lr.key, "consumption.payable_round"), {"local_base": national_payable}))
    else:
        local_payable, local_refund = 0, _mul(national_refund, lr.frac)
        lines.append(Line("local_refund", "譲渡割額（還付額）", local_refund,
                          f"floor({national_refund:,} × {lr.frac[0]}/{lr.frac[1]})", "申告書#9", ok(lr.key),
                          {"local_base": national_refund}))
    total = national_payable + local_payable - national_refund - local_refund
    lines.append(Line("total", "消費税及び地方消費税の合計（納付又は還付）税額", total,
                      "国税 + 地方消費税（還付は負）", "申告書#10", True, {}))

    # ---- 警告（申告前の確認事項）
    warnings.append(Warning_("not_included",
                             "売上げの返還等・貸倒れ・中間納付税額・控除過大調整税額は反映していません。"))
    if method == "honsoku" and purchase_calc == "warimodoshi":
        warnings.append(Warning_("purchase_warimodoshi",
                                 "仕入税額は割戻し計算です（売上税額も割戻し計算の場合に限り選択できます）。"))
    if params.has(year, "consumption.reduced_rate_change_pending"):
        if any(s.rate == 8 for s in sales) or any(p.rate == 8 for p in purchases):
            used["consumption.reduced_rate_change_pending"] = P["consumption.reduced_rate_change_pending"]
            warnings.append(Warning_("reduced_rate_change_pending",
                                     "令和9年4月1日以後の飲食料品の税率引下げ（1%案）は反映していません（8%で計算）。"))
    if method == "sanwari" and params.has(year, "consumption.sanwari_forms_final"):
        used["consumption.sanwari_forms_final"] = P["consumption.sanwari_forms_final"]
        warnings.append(Warning_("sanwari_forms_draft",
                                 "3割特例の申告書様式は確定版が未公表です（ドラフト版に基づく）。"))
    warnings.append(Warning_("disclaimer", "これは帳簿データからの計算結果です。申告前に税理士・税務署に確認してください。"))

    return ReturnResult(year, method, purchase_calc if method == "honsoku" else "", output, credit,
                        national_payable, national_refund, local_payable, local_refund, total, lines, warnings,
                        sorted(k for k, p in used.items() if not p.verified))
