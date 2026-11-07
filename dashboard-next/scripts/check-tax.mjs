// 消費税カードの TS 実装（app/lib/tax.ts）が Python エンジンと同じ期待値を返すか確認する。
// 実行: npm run check:tax（Node 22.6+ の --experimental-strip-types が必要）
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { estimateIncomeTax } from "../app/lib/income.ts";
import { compute, methodUnavailable, settle, taxIncluded, inputCreditRatio, transitionalBreakdown } from "../app/lib/tax.ts";

const ex = JSON.parse(readFileSync(new URL("../app/lib/tax-example.json", import.meta.url), "utf8"));
const o = { individual: ex.individual, taxYear: ex.taxYear };

for (const [key, want] of Object.entries(ex.expected)) {
  const [method, kani] = key.split("_");
  const opts = { ...o, kaniType: kani ? Number(kani) : null };
  if (want === null) {
    assert.ok(methodUnavailable(method, opts), `${key} should be unavailable`);
    assert.throws(() => compute(ex.sales, ex.purchases, method, opts));
    continue;
  }
  const r = compute(ex.sales, ex.purchases, method, opts);
  assert.deepEqual({ output: r.output, input: r.input, payable: r.payable }, want, key);
  // API 集計値（by_rate）経由の settle でも同じ
  const h = compute(ex.sales, ex.purchases, "honsoku", o);
  assert.deepEqual(settle(h.output, h.input, method, opts), { input: want.input, payable: want.payable }, `${key} settle`);
}
assert.deepEqual(transitionalBreakdown(ex.purchases), ex.expectedUnqualified);

// test_tax_consumption.py と同じ境界値
for (const [g, r, t] of [[1100, 10, 100], [1080, 8, 80], [1, 10, 0], [109, 10, 9], [110, 10, 10], [999, 8, 74], [998, 8, 73], [0, 10, 0], [5000, 0, 0]])
  assert.equal(taxIncluded(g, r), t, `taxIncluded(${g},${r})`);
for (const [d, r] of [["2023-09-30", 100], ["2023-10-01", 80], ["2026-09-30", 80], ["2026-10-01", 70], ["2028-09-30", 70],
  ["2028-10-01", 50], ["2030-09-30", 50], ["2030-10-01", 30], ["2031-09-30", 30], ["2031-10-01", 0]])
  assert.equal(inputCreditRatio(d, false), r, d);
assert.equal(methodUnavailable("niwari", { taxYear: 2027 }) !== null, true);
assert.equal(methodUnavailable("sanwari", { individual: false, taxYear: 2027 }) !== null, true);
assert.equal(methodUnavailable("sanwari", { individual: true, taxYear: 2028 }), null);
// T-050: 1,000万円要件（test_tax_eligibility.py と同じ境界）
assert.equal(methodUnavailable("niwari", { taxYear: 2026, basePeriodSales: 10_000_000 }), null);
assert.ok(methodUnavailable("niwari", { taxYear: 2026, basePeriodSales: 10_000_001 }));
// T-066: 2割も特定期間を見る（NTA Q&A 問115, 消法9の2①）。給与等 ≤ 1,000万なら可
assert.equal(methodUnavailable("niwari", { taxYear: 2026, specificPeriodSales: 10_000_000 }), null);
assert.ok(methodUnavailable("niwari", { taxYear: 2026, specificPeriodSales: 10_000_001 })?.includes("特定期間"));
assert.equal(methodUnavailable("niwari", { taxYear: 2026, specificPeriodSales: 10_000_001, specificPeriodSalaries: 10_000_000 }), null);
assert.ok(methodUnavailable("niwari", { taxYear: 2026, specificPeriodSales: 10_000_001, specificPeriodSalaries: 10_000_001 }));
assert.equal(methodUnavailable("niwari", { taxYear: 2026, specificPeriodSalaries: 50_000_000 }), null); // 給与等のみ超過は売上高で可
assert.equal(methodUnavailable("sanwari", { individual: true, taxYear: 2027, basePeriodSales: 10_000_000, specificPeriodSales: 10_000_000 }), null);
assert.ok(methodUnavailable("sanwari", { individual: true, taxYear: 2027, basePeriodSales: 10_000_001 }));
assert.ok(methodUnavailable("sanwari", { individual: true, taxYear: 2027, specificPeriodSales: 10_000_001 }));
assert.equal(methodUnavailable("sanwari", { individual: true, taxYear: 2027, specificPeriodSales: 10_000_001, specificPeriodSalaries: 10_000_000 }), null);
assert.ok(methodUnavailable("sanwari", { individual: true, taxYear: 2027, specificPeriodSales: 10_000_001, specificPeriodSalaries: 10_000_001 }));
assert.deepEqual(settle(-1_250, 0, "honsoku"), { input: 0, payable: -1_200 }); // 還付も0方向へ切捨て

// 所得税（test_tax_income.py と同じ例）: 2026年分 事業所得 300万 → 基礎控除 104万
const it26 = estimateIncomeTax(3_000_000, 0, 2026, 0, 0, 0);
assert.deepEqual([it26.basic_deduction, it26.taxable, it26.total], [1_040_000, 1_960_000, 100_500], "income 2026");
assert.equal(estimateIncomeTax(8_000_000, 3_000_000, 2025, 650_000, 600_000, 0).total, 213_800, "income 2025");
assert.equal(estimateIncomeTax(8_000_000, 3_000_000, 2027, 650_000, 600_000, 0).total, 177_100, "income 2027");
assert.equal(estimateIncomeTax(3_000_000, 0, 2028, 0, 0, 0), null, "2028 unverified");

console.log("check:tax OK —", Object.entries(ex.expected).map(([k, v]) => `${k}=${v ? v.payable : "n/a"}`).join(" "));
