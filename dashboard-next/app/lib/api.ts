/**
 * J-SaaS 会計 API istemcisi (bot/api.py → docs/API.md).
 * Token tarayıcıda saklanır (`/connect#tk_...` ile gelir). Token veya API adresi yoksa panel demo verisiyle çalışır.
 */

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "https://tegaru-line-bot.onrender.com").replace(/\/$/, "");
const TOKEN_KEY = "jsaas.token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: session-only */
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  if (!token) throw new ApiError(401, "no token");
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Token gerektirmeyen uçlar (kayıt / giriş / parola sıfırlama). Ağ hatası → ApiError(0). */
async function publicCall<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1${path}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, NETWORK_ERROR);
  }
  if (!res.ok) throw new ApiError(res.status, await errorDetail(res));
  return res.json() as Promise<T>;
}

export const NETWORK_ERROR = "サーバーに接続できません。時間をおいて再度お試しください。";

/** FastAPI hata gövdesinden kullanıcıya gösterilecek metin (`detail` string ya da 422 listesi). */
async function errorDetail(res: Response): Promise<string> {
  try {
    const d = (await res.json()).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return "入力内容を確認してください。";
  } catch {
    /* non-JSON error */
  }
  return res.statusText || `HTTP ${res.status}`;
}

/** Yetkili dosya indirme (PDF / CSV): blob olarak alır. */
export async function fetchBlob(path: string): Promise<Blob> {
  const token = getToken();
  if (!token) throw new ApiError(401, "no token");
  const res = await fetch(`${API_BASE}/api/v1${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return res.blob();
}

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export function openBlob(blob: Blob) {
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/* ---------- response types ---------- */
export type ApiSummary = {
  month: string; revenue: number; expenses: number; profit: number;
  revenue_change_pct: number | null; expenses_change_pct: number | null; profit_change_pct: number | null;
  expenses_without_invoice_no: number; receivables: number; unpaid_invoices: number;
};
export type ApiCashflow = { month: string; income: number; expense: number; net: number }[];
export type ApiRate = { sales: number; output: number; input: number };
export type ApiTax = {
  year: number; method: string; output_tax: number; input_tax: number; payable: number; by_rate: Record<"10" | "8", ApiRate>;
  /** 登録番号なし仕入の控除割合別内訳（古いサーバーでは無い） */
  unqualified?: { ratio: number; gross: number; tax: number; credited: number }[];
};
export type ApiInvoice = {
  no: string; client: string; issued: string; due: string; total: number;
  subtotal10: number; subtotal8: number; tax10: number; tax8: number;
  status: "paid" | "unpaid"; overdue: boolean;
};
export type ApiProfile = { user_id: string; business_name: string; registration_no: string; individual: number };

export type ApiEntry = {
  id: number; user_id?: string; d: string; kind: "inc" | "exp"; store: string; amount: number; category: string;
  rate: number; invoice_no: string; source: string; image_path?: string; created_at?: string;
};
export type EntryDraft = { date: string; kind: "inc" | "exp"; store: string; amount: number; category: string; rate: number; invoice_no: string };
export type ApiOcr = { ok: boolean; error?: string; partial?: { date?: string; store?: string; invoice_no?: string }; entries: EntryDraft[] };
export type ApiBankTx = {
  id: number; d: string; description: string; amount: number; balance: number | null; account: string;
  invoice_no: string; entry_id: number | null;
};
export type ApiSuggestion = { tx_id: number; invoice_no: string; client: string; amount: number; date: string };
export type ApiPL = { year: number; revenue: number; expenses: { category: string; amount: number }[]; expenses_total: number; income_before_blue: number; note: string };
export type ApiIncomeTax = {
  year: number; revenue: number; expenses: number; business_income: number; blue_deduction: number; basic_deduction: number;
  taxable: number; base_tax: number; reconstruction: number; total: number; disclaimer: string;
};
export type ApiAuth = { account: { id: number; email: string }; user_id: string; token: string };
/** `role` T-041 ile geldi; eski sunucuda yoksa owner sayılır (lib/team.ts `parseRole`). */
export type ApiMe = { user_id: string; role?: string; account: { id: number; email: string; email_verified: boolean } | null };

/** Ekip (T-041, docs/API.md `/team/*`). */
export type ApiMember = { account_id: number; email: string; role: "owner" | "accountant" | "viewer"; joined_at?: string };
export type ApiInvite = { id: string; role: "accountant" | "viewer"; created_at: string; expires_at: string };
export type ApiNewInvite = { code: string; role: "accountant" | "viewer"; expires_at: string };
export type ApiSession = { user_id: string; role: string; token: string };

/** Abonelik (T-042, docs/API.md). Fiyatlar Q-11 cevaplanana kadar yer tutucu. */
export type ApiPlan = {
  id: "free" | "personal" | "business"; name: string; price_jpy: number;
  receipts_per_month: number | null; invoices_per_month: number | null; placeholder: boolean; available: boolean;
  tax_excluded?: boolean; interval?: "month";
};
export type ApiBillingStatus = {
  plan: ApiPlan["id"]; plan_name: string;
  limits: { receipts_per_month: number | null; invoices_per_month: number | null };
  usage: { month: string; receipts: number; invoices: number };
  payments_enabled: boolean; limits_enforced: boolean;
  subscription: { plan: string; status: string; current_period_end: string; cancel_at_period_end: boolean } | null;
};

export type ApiChannels = {
  line: { configured: boolean; webhook: string; linked: boolean };
  whatsapp: { configured: boolean; webhook: string };
  ocr: { engine: string; tesseract: boolean; ai_fallback: boolean };
  categories: string[];
};

const qs = (o: Record<string, string | number | undefined | null>) => {
  const p = Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return p.length ? "?" + p.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&") : "";
};

export const api = {
  summary: (month?: string) => call<ApiSummary>(`/summary${month ? `?month=${month}` : ""}`),
  cashflow: (months = 6, end?: string) => call<ApiCashflow>(`/cashflow?months=${months}${end ? `&end=${end}` : ""}`),
  tax: (year: number) => call<ApiTax>(`/tax/consumption?year=${year}`),
  invoices: () => call<ApiInvoice[]>("/invoices"),
  profile: () => call<ApiProfile>("/profile"),
  createInvoice: (body: { client: string; due: string; items: { name: string; qty: number; unit_price: number; rate: 10 | 8 }[] }) =>
    call<ApiInvoice>("/invoices", { method: "POST", body: JSON.stringify(body) }),
  payInvoice: (no: string) => call<ApiInvoice>(`/invoices/${encodeURIComponent(no)}/paid`, { method: "POST" }),
  pdfUrl: (no: string) => `${API_BASE}/api/v1/invoices/${encodeURIComponent(no)}/pdf`,
  pdf: (no: string) => fetchBlob(`/invoices/${encodeURIComponent(no)}/pdf`),
  createInvoiceFull: (body: { client: string; issued?: string; due: string; items: { name: string; qty: number; unit_price: number; rate: 10 | 8 }[] }) =>
    call<ApiInvoice & { items: { name: string; qty: number; unit_price: number; rate: number; amount: number }[] }>("/invoices", { method: "POST", body: JSON.stringify(body) }),
  putProfile: (body: { business_name: string; registration_no: string; individual: boolean }) =>
    call<ApiProfile>("/profile", { method: "PUT", body: JSON.stringify(body) }),
  entries: (f: { date_from?: string; date_to?: string; q?: string; amount_min?: number; amount_max?: number; kind?: string; limit?: number } = {}) =>
    call<ApiEntry[]>(`/entries${qs(f)}`),
  createEntry: (e: EntryDraft) => call<ApiEntry & { id: number }>("/entries", { method: "POST", body: JSON.stringify(e) }),
  patchEntry: (id: number, e: Partial<EntryDraft>) => call<ApiEntry>(`/entries/${id}`, { method: "PATCH", body: JSON.stringify(e) }),
  deleteEntry: (id: number) => call<void>(`/entries/${id}`, { method: "DELETE" }),
  ocr: (file: Blob) => call<ApiOcr>("/receipts/ocr", { method: "POST", body: file, headers: { "Content-Type": file.type || "application/octet-stream" } }),
  bankImport: (file: Blob, account = "") =>
    call<{ parsed: number; imported: number; duplicates: number; suggestions: ApiSuggestion[] }>(`/bank/import${qs({ account })}`, {
      method: "POST", body: file, headers: { "Content-Type": "text/csv" },
    }),
  bank: () => call<{ transactions: ApiBankTx[]; suggestions: ApiSuggestion[] }>("/bank/transactions"),
  bankMatch: (tx_id: number, invoice_no: string) => call<ApiInvoice>("/bank/match", { method: "POST", body: JSON.stringify({ tx_id, invoice_no }) }),
  bankToEntry: (tx_id: number, category: string, rate: number) =>
    call<ApiEntry>(`/bank/${tx_id}/entry`, { method: "POST", body: JSON.stringify({ category, rate }) }),
  pl: (year: number) => call<ApiPL>(`/pl?year=${year}`),
  incomeTax: (year: number, p: { blue?: number; social_insurance?: number; other_deductions?: number }) => call<ApiIncomeTax>(`/tax/income${qs({ year, ...p })}`),
  consumption: (year: number, method = "honsoku", kani_type?: number) => call<ApiTax>(`/tax/consumption${qs({ year, method, kani_type })}`),
  exportCsv: (format: "freee" | "mf" | "yayoi", year: number) => fetchBlob(`/export.csv${qs({ format, year })}`),
  /** T-045: 青色申告決算書（損益計算書）転記用 PDF */
  blueReturnPdf: (year: number, blue: number) => fetchBlob(`/reports/blue-return.pdf${qs({ year, blue })}`),
  channels: () => call<ApiChannels>("/channels"),
  revoke: () => call<void>("/tokens/current", { method: "DELETE" }),
  me: () => call<ApiMe>("/auth/me"),
  billingPlans: () => call<{ plans: ApiPlan[]; payments_enabled: boolean }>("/billing/plans"),
  billingStatus: () => call<ApiBillingStatus>("/billing/status"),
  checkout: (plan: "personal" | "business") => call<{ url: string }>("/billing/checkout", { method: "POST", body: JSON.stringify({ plan }) }),
  cancelPlan: () => call<ApiBillingStatus>("/billing/cancel", { method: "POST" }),
  linkLine: (code: string) => call<ApiAuth>("/auth/link-line", { method: "POST", body: JSON.stringify({ code }) }),
  teamMembers: () => call<{ members: ApiMember[]; invites: ApiInvite[] }>("/team/members"),
  teamInvite: (role: "accountant" | "viewer") => call<ApiNewInvite>("/team/invites", { method: "POST", body: JSON.stringify({ role }) }),
  teamRevokeInvite: (id: string) => call<void>(`/team/invites/${encodeURIComponent(id)}`, { method: "DELETE" }),
  teamSetRole: (account_id: number, role: "accountant" | "viewer") =>
    call<{ account_id: number; role: string }>(`/team/members/${account_id}`, { method: "PATCH", body: JSON.stringify({ role }) }),
  teamRemove: (account_id: number) => call<void>(`/team/members/${account_id}`, { method: "DELETE" }),
  teamJoin: (code: string) => call<ApiSession>("/team/join", { method: "POST", body: JSON.stringify({ code }) }),
  teamLedgers: () => call<{ current: string; ledgers: { user_id: string; role: string; business_name: string }[] }>("/team/ledgers"),
  teamSwitch: (user_id: string) => call<ApiSession>("/team/switch", { method: "POST", body: JSON.stringify({ user_id }) }),
};

/**
 * Oturumu yeni token'a geçirir (davet katılımı / defter değiştirme): eski token sunucuda iptal edilir
 * (en iyi çaba; böylece hesap başına token sınırı dolmaz), yenisi kaydedilir.
 */
export async function replaceSession(newToken: string) {
  try { await api.revoke(); } catch { /* eski token zaten geçersiz olabilir */ }
  setToken(newToken);
}

/** Hesap uçları (T-040, docs/API.md). Başarılı giriş/kayıtta token kaydedilir. */
export const auth = {
  signup: (email: string, password: string) => publicCall<ApiAuth>("/auth/signup", { email, password }),
  login: (email: string, password: string) => publicCall<ApiAuth>("/auth/login", { email, password }),
  resetRequest: (email: string) => publicCall<{ ok: boolean }>("/auth/password-reset/request", { email }),
  resetConfirm: (token: string, password: string) => publicCall<{ ok: boolean }>("/auth/password-reset/confirm", { token, password }),
};

/** Parola kuralı: sunucu ile aynı (bot/accounts.py, 10〜128 文字). */
export const PASSWORD_MIN = 10;
export const PASSWORD_MAX = 128;

export const CATEGORIES = ["売上高", "旅費交通費", "消耗品費", "会議費", "接待交際費", "通信費", "地代家賃", "水道光熱費",
  "外注工賃", "新聞図書費", "広告宣伝費", "支払手数料", "雑費"];
export const EXPENSE_CATEGORIES = CATEGORIES.filter((c) => c !== "売上高");

/** Asia/Tokyo bugünü (YYYY-MM-DD) */
export const todayJST = () => new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });

/** "2026-10" → "10月" */
export const monthLabel = (ym: string) => `${Number(ym.slice(5, 7))}月`;
