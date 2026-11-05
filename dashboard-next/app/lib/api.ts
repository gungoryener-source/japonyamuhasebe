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
  return res.json() as Promise<T>;
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
};

/** "2026-10" → "10月" */
export const monthLabel = (ym: string) => `${Number(ym.slice(5, 7))}月`;
