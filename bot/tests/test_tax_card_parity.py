"""消費税カード（dashboard-next/app/lib/tax.ts）と Python 税エンジンの共通例による整合テスト。

同じ例を `cd dashboard-next && npm run check:tax`（Node 22+）が TypeScript 側で検証する。
"""
import json
from datetime import date
from pathlib import Path

import pytest

from tax.consumption import Purchase, Sale, compute, transitional_breakdown

EXAMPLE = Path(__file__).resolve().parents[2] / "dashboard-next" / "app" / "lib" / "tax-example.json"


@pytest.fixture(scope="module")
def ex():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _inputs(ex):
    sales = [Sale(s["gross"], s["rate"]) for s in ex["sales"]]
    purchases = [Purchase(p["gross"], p["rate"], date.fromisoformat(p["day"]), p["qualified"]) for p in ex["purchases"]]
    return sales, purchases


@pytest.mark.parametrize("key", ["honsoku", "kani_5", "niwari"])
def test_example_matches_engine(ex, key):
    sales, purchases = _inputs(ex)
    method, _, kani = key.partition("_")
    r = compute(sales, purchases, method, kani_type=int(kani) if kani else None,  # type: ignore[arg-type]
                individual=ex["individual"], tax_year=ex["taxYear"])
    assert {"output": r.output_tax, "input": r.input_tax, "payable": r.payable} == ex["expected"][key]


def test_example_sanwari_unavailable_in_2026(ex):
    sales, purchases = _inputs(ex)
    assert ex["expected"]["sanwari"] is None
    with pytest.raises(ValueError):
        compute(sales, purchases, "sanwari", individual=True, tax_year=ex["taxYear"])


def test_example_unqualified_breakdown(ex):
    _, purchases = _inputs(ex)
    assert transitional_breakdown(purchases) == ex["expectedUnqualified"]


def P(gross, d, qualified=False, rate=10):
    return Purchase(gross, rate, d, qualified)


def test_breakdown_boundaries_and_exclusions():
    rows = transitional_breakdown([
        P(110_000, date(2026, 9, 30)),                 # 80%
        P(110_000, date(2026, 10, 1)),                 # 70%
        P(110_000, date(2028, 9, 30)),                 # 70%
        P(110_000, date(2028, 10, 1)),                 # 50%
        P(110_000, date(2031, 10, 1)),                 # 0%
        P(110_000, date(2023, 9, 30)),                 # 制度開始前 → 対象外
        P(110_000, date(2026, 10, 1), qualified=True),  # 適格 → 対象外
        P(5_000, date(2026, 10, 1), rate=0),           # 非課税 → 対象外
    ])
    assert [(r["ratio"], r["gross"], r["tax"], r["credited"]) for r in rows] == [
        (80, 110_000, 10_000, 8_000),
        (70, 220_000, 20_000, 14_000),
        (50, 110_000, 10_000, 5_000),
        (0, 110_000, 10_000, 0),
    ]


def test_breakdown_rounds_per_purchase_like_compute():
    ps = [P(1_099, date(2026, 10, 1)), P(1_099, date(2026, 10, 1))]  # 税 99 → 控除 69 ずつ
    rows = transitional_breakdown(ps)
    assert rows == [{"ratio": 70, "gross": 2_198, "tax": 198, "credited": 138}]
    r = compute([], ps)
    assert r.input_tax == 138


def test_breakdown_empty():
    assert transitional_breakdown([]) == []
