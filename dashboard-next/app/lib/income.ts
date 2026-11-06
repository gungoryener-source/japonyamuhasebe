/** 所得税の概算（bot/tax/income.py と同じ規則, docs/TAX_RULES.md §2）。デモ表示用。 */
const BRACKETS: [number, number, number][] = [
  [1_950_000, 5, 0], [3_300_000, 10, 97_500], [6_950_000, 20, 427_500], [9_000_000, 23, 636_000],
  [18_000_000, 33, 1_536_000], [40_000_000, 40, 2_796_000], [Infinity, 45, 4_796_000],
];
const BASIC_2025: [number, number][] = [
  [1_320_000, 950_000], [3_360_000, 880_000], [4_890_000, 680_000], [6_550_000, 630_000],
  [23_500_000, 580_000], [24_000_000, 480_000], [24_500_000, 320_000], [25_000_000, 160_000], [Infinity, 0],
];

export function incomeTaxOn(taxable: number): number {
  const t = Math.floor(Math.max(0, taxable) / 1000) * 1000;
  const [, r, d] = BRACKETS.find(([lim]) => t <= lim)!;
  return Math.max(0, Math.floor((t * r) / 100) - d);
}

export function estimateIncomeTax(revenue: number, expenses: number, year: number, blue: number, social: number, other: number) {
  if (year !== 2025) return null; // 令和8年分の基礎控除は未確定（tasks/QUESTIONS.md Q-03）
  const profit = revenue - expenses;
  const blueUsed = Math.min(blue, Math.max(0, profit));
  const business = profit - blueUsed;
  const total = Math.max(0, business);
  const basic = BASIC_2025.find(([lim]) => total <= lim)![1];
  const taxable = Math.floor(Math.max(0, total - basic - social - other) / 1000) * 1000;
  const base = incomeTaxOn(taxable);
  const recon = Math.floor((base * 21) / 1000);
  return { business_income: business, blue_deduction: blueUsed, basic_deduction: basic, taxable, base_tax: base, reconstruction: recon, total: Math.floor((base + recon) / 100) * 100 };
}
