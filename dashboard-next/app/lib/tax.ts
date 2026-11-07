/**
 * 消費税の計算 — `bot/tax/consumption.py` の忠実な移植（docs/TAX_RULES.md §1）。
 * 金額はすべて税込・整数円、端数は切捨て。ロジックを変えるときは Python 側と
 * `tax-example.json`（両方のテストが読む共通例）も同時に更新すること。
 * Node 22+ で `npm run check:tax` により Python と同じ期待値か確認できる。
 * 注意: このファイルは型注釈のみの TypeScript（enum 等なし）に保つ。
 */

export type Rate = 10 | 8 | 0;
export type Method = "honsoku" | "kani" | "niwari" | "sanwari";
export type Sale = { gross: number; rate: Rate };
export type Purchase = { gross: number; rate: Rate; day: string /* YYYY-MM-DD */; qualified: boolean };
export type ByRate = Record<"10" | "8", { sales: number; output: number; input: number }>;
export type Opts = {
  kaniType?: number | null; individual?: boolean; taxYear?: number | null;
  // 任意: 2割・3割特例の 1,000万円要件（Python compute の base_period_sales 等と同じ）
  basePeriodSales?: number | null; specificPeriodSales?: number | null; specificPeriodSalaries?: number | null;
};
export type Result = { output: number; input: number; payable: number; byRate: ByRate; method: Method };
export type Transitional = { ratio: number; gross: number; tax: number; credited: number };

export const RATES = [10, 8] as const;

// 免税事業者等からの課税仕入れに係る経過措置（令和8年度改正後）: [開始日, 控除割合 %]
export const TRANSITIONAL_CREDIT: readonly (readonly [string, number])[] = [
  ["2023-10-01", 80],
  ["2026-10-01", 70],
  ["2028-10-01", 50],
  ["2030-10-01", 30],
  ["2031-10-01", 0],
];

// 簡易課税 みなし仕入率（第1種〜第6種）— TAX_RULES §1 ✅（NTA No.6505）
export const KANI_RATIO: Record<number, number> = { 1: 90, 2: 80, 3: 70, 4: 60, 5: 50, 6: 40 };
export const KANI_LABEL: Record<number, string> = {
  1: "第1種 卸売業", 2: "第2種 小売業", 3: "第3種 製造業等", 4: "第4種 その他", 5: "第5種 サービス業等", 6: "第6種 不動産業",
};

// 2割・3割特例の要件: 基準期間（3割は特定期間も）の課税売上高 ≤ 1,000万円 — TAX_RULES §1 ✅
export const SMALL_BUSINESS_LIMIT = 10_000_000;

/** Python method_ineligible と同じ。特定期間は給与等支払額 ≤ 1,000万でも可。 */
export function smallBusinessIneligible(o: Opts): "base_period" | "specific_period" | null {
  if (o.basePeriodSales != null && o.basePeriodSales > SMALL_BUSINESS_LIMIT) return "base_period";
  if (o.specificPeriodSales != null && o.specificPeriodSales > SMALL_BUSINESS_LIMIT
    && !(o.specificPeriodSalaries != null && o.specificPeriodSalaries <= SMALL_BUSINESS_LIMIT)) return "specific_period";
  return null;
}

export const METHOD_LABEL: Record<Method, string> = { honsoku: "本則課税", kani: "簡易課税", niwari: "2割特例", sanwari: "3割特例" };

export function taxIncluded(gross: number, rate: number): number {
  if (rate === 0 || gross <= 0) return 0;
  if (rate !== 10 && rate !== 8) throw new Error(`unsupported rate: ${rate}`);
  return Math.floor((gross * rate) / (100 + rate));
}

export function inputCreditRatio(day: string, qualified: boolean): number {
  if (qualified) return 100;
  if (day < TRANSITIONAL_CREDIT[0][0]) return 100; // インボイス制度開始前
  let ratio = 0;
  for (const [start, pct] of TRANSITIONAL_CREDIT) if (day >= start) ratio = pct;
  return ratio;
}

/** Python の _floor100: 0 方向へ 100円未満切捨て（還付はマイナス）。 */
export const floor100 = (n: number) => (n >= 0 ? Math.floor(n / 100) * 100 : -Math.floor(-n / 100) * 100);

/** その方式が使えない理由（使えるなら null）。compute の ValueError と同じ条件。 */
export function methodUnavailable(method: Method, o: Opts = {}): string | null {
  if (method === "kani" && !(o.kaniType != null && o.kaniType in KANI_RATIO)) return "事業区分（第1〜6種）を選択してください";
  if (method === "niwari") {
    if (o.taxYear != null && o.taxYear > 2026) return "2割特例は令和8年（2026年）分までです";
    const why = smallBusinessIneligible(o);
    if (why === "base_period") return "基準期間の課税売上高が1,000万円を超えるため2割特例は使えません";
    if (why === "specific_period") return "特定期間の課税売上高（および給与等）が1,000万円を超えるため2割特例は使えません";
  }
  if (method === "sanwari") {
    if (o.individual === false) return "3割特例は個人事業者のみです";
    if (o.taxYear !== 2027 && o.taxYear !== 2028) return "3割特例は令和9・10年（2027・2028年）分のみです";
    const why = smallBusinessIneligible(o);
    if (why === "base_period") return "基準期間の課税売上高が1,000万円を超えるため3割特例は使えません";
    if (why === "specific_period") return "特定期間の課税売上高（および給与等）が1,000万円を超えるため3割特例は使えません";
  }
  return null;
}

/**
 * 売上税額と本則の控除税額から、方式ごとの控除税額・差引税額を出す。
 * 本則以外は売上税額だけで決まるため、API の集計値（by_rate）からも同じ結果になる。
 */
export function settle(output: number, honsokuInput: number, method: Method, o: Opts = {}): { input: number; payable: number } {
  const why = methodUnavailable(method, o);
  if (why) throw new Error(why);
  const input =
    method === "honsoku" ? honsokuInput
    : method === "kani" ? Math.floor((output * KANI_RATIO[o.kaniType as number]) / 100)
    : method === "niwari" ? Math.floor((output * 80) / 100)
    : Math.floor((output * 70) / 100);
  return { input, payable: floor100(output - input) };
}

export function compute(sales: Sale[], purchases: Purchase[], method: Method = "honsoku", o: Opts = {}): Result {
  const byRate: ByRate = { "10": { sales: 0, output: 0, input: 0 }, "8": { sales: 0, output: 0, input: 0 } };
  for (const s of sales) if (s.rate !== 0) byRate[String(s.rate) as "10" | "8"].sales += s.gross;
  for (const r of RATES) byRate[`${r}`].output = taxIncluded(byRate[`${r}`].sales, r); // 税率ごとに1回だけ端数処理
  const output = byRate["10"].output + byRate["8"].output;

  if (method === "honsoku") {
    for (const p of purchases) {
      if (p.rate === 0) continue;
      byRate[String(p.rate) as "10" | "8"].input += Math.floor((taxIncluded(p.gross, p.rate) * inputCreditRatio(p.day, p.qualified)) / 100);
    }
  }
  const honsokuInput = byRate["10"].input + byRate["8"].input;
  const { input, payable } = settle(output, honsokuInput, method, o);
  return { output, input, payable, byRate, method };
}

/** 登録番号のない課税仕入れの控除割合別内訳（Python transitional_breakdown と同じ）。 */
export function transitionalBreakdown(purchases: Purchase[]): Transitional[] {
  const groups = new Map<number, Transitional>();
  for (const p of purchases) {
    if (p.qualified || p.rate === 0) continue;
    const ratio = inputCreditRatio(p.day, false);
    if (ratio === 100) continue;
    const tax = taxIncluded(p.gross, p.rate);
    const g = groups.get(ratio) ?? { ratio, gross: 0, tax: 0, credited: 0 };
    g.gross += p.gross;
    g.tax += tax;
    g.credited += Math.floor((tax * ratio) / 100);
    groups.set(ratio, g);
  }
  return [...groups.values()].sort((a, b) => b.ratio - a.ratio);
}
