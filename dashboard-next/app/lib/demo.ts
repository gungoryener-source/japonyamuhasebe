/** Demo verisi (token yokken panel bununla çalışır). */
import TAX_EXAMPLE from "./tax-example.json";
import type { Purchase, Sale } from "./tax";

/* ============================================================
 * MOCK DATA
 * ============================================================ */

export type InvoiceStatus = "paid" | "unpaid" | "overdue";
export type Invoice = { no: string; client: string; issued: string; due: string; amount: number; rate: 10 | 8; status: InvoiceStatus };
export type Company = { id: string; name: string; reg: string; fiscal: string };

export const MOCK = {
  today: "2026-11-05",
  companies: [
    { id: "c1", name: "合同会社ミナト", reg: "T3010001222222", fiscal: "第8期 2026/04–2027/03" },
    { id: "c2", name: "株式会社ミナト商事", reg: "T8011101333333", fiscal: "第3期 2026/01–2026/12" },
  ] as Company[],
  // 直近6ヶ月（確定月）。最終月 = 今月の比較対象
  cashflow: [
    { m: "5月", income: 3_420_000, expense: 1_710_000 },
    { m: "6月", income: 3_880_000, expense: 1_950_000 },
    { m: "7月", income: 3_560_000, expense: 1_790_000 },
    { m: "8月", income: 3_210_000, expense: 1_840_000 },
    { m: "9月", income: 3_795_000, expense: 1_876_000 },
    { m: "10月", income: 4_250_000, expense: 1_820_000 },
  ],
  // 消費税カードのデモ: Python エンジンと共通の例（lib/tax-example.json, 2026年分の税込金額）
  tax: TAX_EXAMPLE as unknown as { taxYear: number; individual: boolean; interimPaid: number; nextDeadline: string; sales: Sale[]; purchases: Purchase[] },
  banks: [
    { name: "三菱UFJ銀行", acct: "普通 ****4821", synced: "09:12", ok: true },
    { name: "三井住友銀行", acct: "当座 ****0937", synced: "09:12", ok: true },
    { name: "法人カード", acct: "Visa ****7713", synced: "08:55", ok: true },
  ],
  invoices: [
    { no: "INV-2026-0418", client: "株式会社サクラ製作所", issued: "2026-10-31", due: "2026-11-30", amount: 1_320_000, rate: 10, status: "unpaid" },
    { no: "INV-2026-0417", client: "A001 株式会社アオイ商事", issued: "2026-10-31", due: "2026-11-30", amount: 990_000, rate: 10, status: "unpaid" },
    { no: "INV-2026-0412", client: "有限会社カエデフーズ", issued: "2026-09-30", due: "2026-10-31", amount: 432_000, rate: 8, status: "overdue" },
    { no: "INV-2026-0409", client: "合同会社ヒカリデザイン", issued: "2026-09-30", due: "2026-10-31", amount: 550_000, rate: 10, status: "paid" },
  ] as Invoice[],
  notifications: [
    { t: "源泉所得税（10月分）の納付期限は 11/10 です", time: "1時間前", kind: "warn" as const },
    { t: "三菱UFJ銀行の明細 18件を取り込みました", time: "3時間前", kind: "ok" as const },
    { t: "INV-2026-0412 が支払期日を超過しています", time: "昨日", kind: "warn" as const },
  ],
  searchIndex: [
    { type: "請求書", label: "INV-2026-0418 株式会社サクラ製作所", sub: "¥1,320,000 ・ 未入金", href: "/invoices/" },
    { type: "請求書", label: "INV-2026-0412 有限会社カエデフーズ", sub: "¥432,000 ・ 期日超過", href: "/invoices/" },
    { type: "取引先", label: "株式会社アオイ商事 (A001)", sub: "T5010401111111 ・ 適格", href: "/invoices/" },
    { type: "取引先", label: "株式会社サクラ製作所", sub: "T6010001054321 ・ 適格", href: "/invoices/" },
    { type: "領収書", label: "JR東日本 新幹線 東京→大阪", sub: "¥14,720 ・ 旅費交通費 ・ 10/14", href: "/expenses/" },
    { type: "領収書", label: "ローソン 会議用飲料", sub: "¥648 ・ 会議費 ・ 軽減8%", href: "/expenses/" },
    { type: "書類", label: "2025年度 青色申告決算書", sub: "PDF ・ e-Tax 送信済", href: "/tax/" },
    { type: "メニュー", label: "銀行明細の取込", sub: "CSV ・ 自動消込", href: "/bank/" },
    { type: "メニュー", label: "事業者情報・登録番号", sub: "設定", href: "/settings/" },
  ],
};

export const DEMO_ENTRIES = [
  { id: 1, d: "2026-10-28", kind: "exp", store: "ローソン", amount: 648, category: "会議費", rate: 8, invoice_no: "T3011001000001", source: "LINE" },
  { id: 2, d: "2026-10-14", kind: "exp", store: "JR東日本", amount: 14_720, category: "旅費交通費", rate: 10, invoice_no: "T7011001666666", source: "LINE" },
  { id: 3, d: "2026-10-12", kind: "exp", store: "居酒屋たぬき", amount: 12_800, category: "接待交際費", rate: 10, invoice_no: "", source: "WEB" },
  { id: 4, d: "2026-10-09", kind: "exp", store: "楽天モバイル", amount: 3_278, category: "通信費", rate: 10, invoice_no: "T9010001888888", source: "WEB" },
  { id: 5, d: "2026-10-05", kind: "exp", store: "東京シェアオフィス", amount: 66_000, category: "地代家賃", rate: 10, invoice_no: "T9010001444444", source: "WEB" },
  { id: 6, d: "2026-09-30", kind: "inc", store: "合同会社ヒカリデザイン", amount: 550_000, category: "売上高", rate: 10, invoice_no: "", source: "INVOICE" },
] as const;
