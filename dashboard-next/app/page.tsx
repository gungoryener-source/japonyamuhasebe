"use client";

/**
 * J-SaaS 会計 — ダッシュボード (app/page.tsx)
 * Next.js App Router + Tailwind CSS + lucide-react. Tek dosya, mock veri ile çalışır.
 * Gerçek API'ye geçerken yalnızca `MOCK` bölümünü fetch çağrılarıyla değiştirin.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, getToken, monthLabel, setToken, type ApiInvoice } from "./lib/api";
import {
  ArrowDownRight, ArrowUpRight, Bell, Building2, Calculator, Camera, Check, ChevronDown,
  ChevronRight, CircleCheck, Clock, FileText, Home, Landmark, LoaderCircle, Menu, Plus,
  LogOut, Receipt, RefreshCw, Search, Settings, ShieldCheck, TriangleAlert, Upload, Wallet, X,
} from "lucide-react";

/* ============================================================
 * MOCK DATA
 * ============================================================ */

type InvoiceStatus = "paid" | "unpaid" | "overdue";
type Invoice = { no: string; client: string; issued: string; due: string; amount: number; rate: 10 | 8; status: InvoiceStatus };
type Company = { id: string; name: string; reg: string; fiscal: string };

const MOCK = {
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
  // 今期累計（4月〜10月）の税込金額
  tax: {
    sales10: 24_640_000,
    sales8: 1_296_000,
    purchase10: 9_350_000,
    purchase8: 972_000,
    interimPaid: 520_000,
    nextDeadline: "2026-11-30",
  },
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
    { type: "請求書", label: "INV-2026-0418 株式会社サクラ製作所", sub: "¥1,320,000 ・ 未入金" },
    { type: "請求書", label: "INV-2026-0412 有限会社カエデフーズ", sub: "¥432,000 ・ 期日超過" },
    { type: "取引先", label: "株式会社アオイ商事 (A001)", sub: "T5010401111111 ・ 適格" },
    { type: "取引先", label: "株式会社サクラ製作所", sub: "T6010001054321 ・ 適格" },
    { type: "領収書", label: "JR東日本 新幹線 東京→大阪", sub: "¥14,720 ・ 旅費交通費 ・ 10/14" },
    { type: "領収書", label: "ローソン 会議用飲料", sub: "¥648 ・ 会議費 ・ 軽減8%" },
    { type: "書類", label: "2025年度 青色申告決算書", sub: "PDF ・ e-Tax 送信済" },
  ],
};

/* ============================================================
 * HELPERS
 * ============================================================ */

const yen = (n: number) => `${n < 0 ? "−" : ""}¥${Math.abs(Math.round(n)).toLocaleString("ja-JP")}`;
const pct = (cur: number, prev: number) => ((cur - prev) / Math.abs(prev)) * 100;
const taxIn = (gross: number, rate: number) => Math.floor((gross * rate) / (100 + rate));
const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");
const daysUntil = (iso: string) => Math.ceil((new Date(iso + "T00:00:00+09:00").getTime() - new Date(new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" }) + "T00:00:00+09:00").getTime()) / 86_400_000);

/* ============================================================
 * DATA (live API or demo)
 * ============================================================ */

type CashMonth = { m: string; income: number; expense: number };
type TaxView = { out10: number; out8: number; in10: number; in8: number; interimPaid: number; nextDeadline: string | null };
type Mode = "loading" | "live" | "demo";

function demoTax(): TaxView {
  const t = MOCK.tax;
  return { out10: taxIn(t.sales10, 10), out8: taxIn(t.sales8, 8), in10: taxIn(t.purchase10, 10), in8: taxIn(t.purchase8, 8), interimPaid: t.interimPaid, nextDeadline: t.nextDeadline };
}

function toInvoice(i: ApiInvoice): Invoice {
  return {
    no: i.no, client: i.client, issued: i.issued, due: i.due, amount: i.total,
    rate: i.subtotal8 > i.subtotal10 ? 8 : 10,
    status: i.status === "paid" ? "paid" : i.overdue ? "overdue" : "unpaid",
  };
}

function useDashboardData() {
  const [mode, setMode] = useState<Mode>("loading");
  const [cashflow, setCashflow] = useState<CashMonth[]>(MOCK.cashflow);
  const [tax, setTax] = useState<TaxView>(demoTax());
  const [invoices, setInvoices] = useState<Invoice[]>(MOCK.invoices);
  const [company, setCompany] = useState<Company>(MOCK.companies[0]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getToken()) { setMode("demo"); return; }
    try {
      const now = new Date();
      const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const end = `${lastMonth.getFullYear()}-${String(lastMonth.getMonth() + 1).padStart(2, "0")}`;
      const [cf, tx, inv, prof] = await Promise.all([api.cashflow(6, end), api.tax(now.getFullYear()), api.invoices(), api.profile()]);
      setCashflow(cf.map((c) => ({ m: monthLabel(c.month), income: c.income, expense: c.expense })));
      setTax({ out10: tx.by_rate["10"].output, out8: tx.by_rate["8"].output, in10: tx.by_rate["10"].input, in8: tx.by_rate["8"].input, interimPaid: 0, nextDeadline: null });
      setInvoices(inv.map(toInvoice));
      setCompany({ id: prof.user_id, name: prof.business_name || "事業者名未設定", reg: prof.registration_no || "登録番号未設定", fiscal: `${now.getFullYear()}年分` });
      setError(null);
      setMode("live");
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setToken(null);
      setError(e instanceof Error ? e.message : String(e));
      setMode("demo");
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { mode, cashflow, tax, invoices, setInvoices, company, setCompany, error, reload: load };
}

/* ============================================================
 * SMALL UI PRIMITIVES
 * ============================================================ */

function Card({ title, en, right, className, children }: { title: string; en?: string; right?: React.ReactNode; className?: string; children: React.ReactNode }) {
  return (
    <section className={cx("flex min-w-0 flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]", className)}>
      <header className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <h2 className="text-[13px] font-bold text-navy">{title}</h2>
        {en && <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">{en}</span>}
        {right && <div className="ml-auto">{right}</div>}
      </header>
      {children}
    </section>
  );
}

function Badge({ tone, children, icon = true }: { tone: "ok" | "warn" | "bad" | "info" | "muted"; children: React.ReactNode; icon?: boolean }) {
  const tones = {
    ok: "bg-mint-50 text-mint-700 ring-mint-100",
    warn: "bg-amber-50 text-amber-700 ring-amber-100",
    bad: "bg-rose-50 text-rose-700 ring-rose-100",
    info: "bg-slate-100 text-navy ring-slate-200",
    muted: "bg-slate-50 text-slate-500 ring-slate-200",
  };
  return (
    <span className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-bold ring-1 ring-inset", tones[tone])}>
      {icon && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

function useToast() {
  const [msg, setMsg] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const show = (m: string) => {
    setMsg(m);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(null), 2600);
  };
  const node = msg ? (
    <div role="status" className="fixed bottom-5 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-navy px-4 py-2 text-xs text-white shadow-lg">
      {msg}
    </div>
  ) : null;
  return { show, node };
}

function useClickOutside(ref: React.RefObject<HTMLElement | null>, onOut: () => void) {
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && onOut();
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [ref, onOut]);
}

/* ============================================================
 * SIDEBAR
 * ============================================================ */

const NAV = [
  { ja: "ホーム", en: "Home", icon: Home, badge: 0 },
  { ja: "請求書管理", en: "Invoices", icon: FileText, badge: 3 },
  { ja: "経費精算", en: "Expenses", icon: Receipt, badge: 12 },
  { ja: "銀行連携", en: "Bank Sync", icon: Landmark, badge: 0 },
  { ja: "確定申告 / 税務", en: "Tax Reporting", icon: Calculator, badge: 0 },
  { ja: "設定", en: "Settings", icon: Settings, badge: 0 },
];

function Sidebar({ open, onClose, company }: { open: boolean; onClose: () => void; company: Company }) {
  const [active, setActive] = useState(0);
  return (
    <>
      <div className={cx("fixed inset-0 z-40 bg-slate-900/40 lg:hidden", open ? "block" : "hidden")} onClick={onClose} aria-hidden />
      <aside
        className={cx(
          "fixed inset-y-0 left-0 z-50 flex w-56 flex-col bg-navy text-slate-300 transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="メインメニュー"
      >
        <div className="flex h-14 items-center gap-2.5 border-b border-white/10 px-4">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-mint text-sm font-black text-navy-900">J</div>
          <div className="leading-tight">
            <p className="text-sm font-bold text-white">J-SaaS 会計</p>
            <p className="text-[10px] text-slate-400">Cloud Accounting</p>
          </div>
          <button className="ml-auto rounded p-1 text-slate-400 hover:text-white lg:hidden" onClick={onClose} aria-label="メニューを閉じる">
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
          {NAV.map((n, i) => (
            <button
              key={n.en}
              onClick={() => { setActive(i); onClose(); }}
              aria-current={active === i ? "page" : undefined}
              className={cx(
                "group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors",
                active === i ? "bg-white/10 text-white" : "hover:bg-white/5 hover:text-white",
              )}
            >
              <n.icon size={17} className={active === i ? "text-mint" : "text-slate-400 group-hover:text-slate-200"} />
              <span className="min-w-0 flex-1">
                <span className="block text-[13px] font-bold leading-tight">{n.ja}</span>
                <span className="block text-[10px] leading-tight text-slate-500">{n.en}</span>
              </span>
              {n.badge > 0 && <span className="rounded-full bg-mint px-1.5 text-[10px] font-bold text-navy-900 tabular">{n.badge}</span>}
            </button>
          ))}
        </nav>

        <div className="space-y-1 border-t border-white/10 p-4 text-[11px]">
          <p className="text-slate-400">適格請求書発行事業者</p>
          <p className="font-mono text-slate-200 tabular">{company.reg}</p>
          <p className="pt-1 text-slate-500">{company.fiscal}</p>
        </div>
      </aside>
    </>
  );
}

/* ============================================================
 * TOPBAR (command search, bank sync, notifications, company switcher)
 * ============================================================ */

function CommandPalette({ open, onClose, onPick }: { open: boolean; onClose: () => void; onPick: (label: string) => void }) {
  const [q, setQ] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const results = useMemo(() => {
    const k = q.trim().toLowerCase();
    return k ? MOCK.searchIndex.filter((r) => (r.label + r.sub + r.type).toLowerCase().includes(k)) : MOCK.searchIndex;
  }, [q]);

  useEffect(() => {
    if (open) { setQ(""); setCursor(0); setTimeout(() => inputRef.current?.focus(), 0); }
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-slate-900/40 px-4 pt-[12vh]" onMouseDown={onClose}>
      <div className="w-full max-w-xl overflow-hidden rounded-xl bg-white shadow-2xl ring-1 ring-slate-200" onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label="検索">
        <div className="flex items-center gap-2 border-b border-slate-200 px-4">
          <Search size={16} className="text-slate-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => { setQ(e.target.value); setCursor(0); }}
            onKeyDown={(e) => {
              if (e.key === "Escape") onClose();
              if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, results.length - 1)); }
              if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
              if (e.key === "Enter" && results[cursor]) onPick(results[cursor].label);
            }}
            placeholder="請求書・取引先・領収書・書類を検索…"
            className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
          />
          <kbd className="rounded border border-slate-200 px-1.5 text-[10px] text-slate-400">ESC</kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto p-1.5">
          {results.length === 0 && <li className="px-3 py-6 text-center text-xs text-slate-400">該当する結果がありません</li>}
          {results.map((r, i) => (
            <li key={r.label}>
              <button
                onMouseEnter={() => setCursor(i)}
                onClick={() => onPick(r.label)}
                className={cx("flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left", i === cursor && "bg-slate-100")}
              >
                <span className="w-12 shrink-0 rounded bg-slate-100 py-0.5 text-center text-[10px] font-bold text-slate-500">{r.type}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] text-navy">{r.label}</span>
                  <span className="block truncate text-[11px] text-slate-400">{r.sub}</span>
                </span>
                <ChevronRight size={14} className="text-slate-300" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Topbar({ onMenu, onSearch, company, setCompany, toast }: {
  onMenu: () => void; onSearch: () => void; company: Company; setCompany: (c: Company) => void; toast: (m: string) => void;
}) {
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState("09:12");
  const [bellOpen, setBellOpen] = useState(false);
  const [coOpen, setCoOpen] = useState(false);
  const [unread, setUnread] = useState(MOCK.notifications.length);
  const bellRef = useRef<HTMLDivElement>(null);
  const coRef = useRef<HTMLDivElement>(null);
  useClickOutside(bellRef, () => setBellOpen(false));
  useClickOutside(coRef, () => setCoOpen(false));

  const sync = () => {
    if (syncing) return;
    setSyncing(true);
    setTimeout(() => {
      setSyncing(false);
      setLastSync(new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Tokyo" }));
      toast("銀行明細を同期しました ・ 新規 18件");
    }, 1400);
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-slate-200 bg-white/90 px-3 backdrop-blur sm:gap-3 sm:px-5">
      <button onClick={onMenu} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden" aria-label="メニューを開く">
        <Menu size={18} />
      </button>

      <button
        onClick={onSearch}
        className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-left text-[13px] text-slate-400 hover:border-slate-300 sm:max-w-md"
      >
        <Search size={15} className="shrink-0" />
        <span className="truncate">書類・請求書・取引先を検索</span>
        <kbd className="ml-auto hidden rounded border border-slate-200 bg-white px-1.5 text-[10px] text-slate-400 sm:block">⌘K</kbd>
      </button>

      <div className="ml-auto flex items-center gap-1 sm:gap-2">
        {/* Bank sync status */}
        <button
          onClick={sync}
          title="今すぐ同期"
          className="hidden items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] hover:bg-slate-50 md:flex"
        >
          <Landmark size={14} className="text-slate-500" />
          <span className="text-slate-500">銀行API</span>
          {syncing ? (
            <Badge tone="info" icon={false}><LoaderCircle size={11} className="animate-spin" />同期中</Badge>
          ) : (
            <Badge tone="ok">接続済</Badge>
          )}
          <span className="font-mono text-slate-400 tabular">{lastSync}</span>
          <RefreshCw size={12} className={cx("text-slate-400", syncing && "animate-spin")} />
        </button>
        <button onClick={sync} className="rounded-lg p-2 md:hidden" aria-label="銀行API 接続済・同期">
          <span className="relative block">
            <Landmark size={18} className="text-slate-500" />
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-mint ring-2 ring-white" />
          </span>
        </button>

        {/* Notifications */}
        <div ref={bellRef} className="relative">
          <button onClick={() => { setBellOpen((o) => !o); setUnread(0); }} className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="通知">
            <Bell size={18} />
            {unread > 0 && <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[9px] font-bold text-white">{unread}</span>}
          </button>
          {bellOpen && (
            <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-24px)] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
              <p className="border-b border-slate-100 px-4 py-2.5 text-xs font-bold text-navy">お知らせ</p>
              <ul>
                {MOCK.notifications.map((n) => (
                  <li key={n.t} className="flex gap-3 border-b border-slate-100 px-4 py-2.5 last:border-0">
                    {n.kind === "warn" ? <TriangleAlert size={15} className="mt-0.5 shrink-0 text-amber-500" /> : <CircleCheck size={15} className="mt-0.5 shrink-0 text-mint" />}
                    <div className="min-w-0">
                      <p className="text-xs text-slate-700">{n.t}</p>
                      <p className="text-[10px] text-slate-400">{n.time}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Company / profile switcher */}
        <div ref={coRef} className="relative">
          <button onClick={() => setCoOpen((o) => !o)} className="flex items-center gap-2 rounded-lg p-1 pr-2 hover:bg-slate-100">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-navy text-xs font-bold text-white">佐</span>
            <span className="hidden text-left leading-tight sm:block">
              <span className="block max-w-[140px] truncate text-xs font-bold text-navy">{company.name}</span>
              <span className="block text-[10px] text-slate-400">経理担当 佐藤</span>
            </span>
            <ChevronDown size={14} className="text-slate-400" />
          </button>
          {coOpen && (
            <div className="absolute right-0 mt-2 w-64 overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-xl">
              <p className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">事業所を切り替え</p>
              {MOCK.companies.map((c) => (
                <button
                  key={c.id}
                  onClick={() => { setCompany(c); setCoOpen(false); toast(`${c.name} に切り替えました`); }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left hover:bg-slate-50"
                >
                  <Building2 size={15} className="text-slate-400" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-bold text-navy">{c.name}</span>
                    <span className="block font-mono text-[10px] text-slate-400">{c.reg}</span>
                  </span>
                  {c.id === company.id && <Check size={14} className="text-mint" />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

/* ============================================================
 * WIDGETS
 * ============================================================ */

function KpiCards({ cashflow }: { cashflow: CashMonth[] }) {
  const cf = cashflow.length >= 2 ? cashflow : [{ m: "", income: 0, expense: 0 }, ...cashflow, { m: "", income: 0, expense: 0 }].slice(-2);
  const cur = cf[cf.length - 1], prev = cf[cf.length - 2];
  const items = [
    { ja: "売上高", en: "Monthly Revenue", v: cur.income, d: pct(cur.income, prev.income), goodWhenUp: true, icon: Wallet },
    { ja: "経費総額", en: "Total Expenses", v: cur.expense, d: pct(cur.expense, prev.expense), goodWhenUp: false, icon: Receipt },
    { ja: "差引利益", en: "Est. Net Profit", v: cur.income - cur.expense, d: pct(cur.income - cur.expense, prev.income - prev.expense), goodWhenUp: true, icon: Calculator },
  ];
  return (
    <>
      {items.map((k) => {
        const d = Number.isFinite(k.d) ? k.d : 0;
        const good = k.goodWhenUp ? d >= 0 : d <= 0;
        const Arrow = d >= 0 ? ArrowUpRight : ArrowDownRight;
        return (
          <section key={k.ja} className="flex min-w-0 flex-col gap-1 rounded-xl border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)] sm:col-span-2 lg:col-span-4">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <k.icon size={14} className="text-slate-400" />
              <span className="font-bold text-slate-600">{k.ja}</span>
              <span className="text-[10px] text-slate-400">{k.en}</span>
              <span className="ml-auto text-[10px] text-slate-400">{cur.m}</span>
            </div>
            <p className="truncate font-mono text-2xl font-semibold tracking-tight text-navy tabular">{yen(k.v)}</p>
            <p className={cx("flex items-center gap-1 text-xs font-bold", good ? "text-mint-600" : "text-rose-600")}>
              <Arrow size={14} />
              {d >= 0 ? "+" : "−"}{Math.abs(d).toFixed(0)}%
              <span className="font-normal text-slate-400">前月比</span>
            </p>
          </section>
        );
      })}
    </>
  );
}

function CashFlowChart({ cashflow }: { cashflow: CashMonth[] }) {
  const data = cashflow;
  const [hover, setHover] = useState<number | null>(null);
  const step = 1_000_000;
  const max = Math.max(step, Math.ceil(Math.max(0, ...data.flatMap((d) => [d.income, d.expense])) / step) * step);
  const ticks = Array.from({ length: max / step + 1 }, (_, i) => max - i * step);
  const totalIn = data.reduce((s, d) => s + d.income, 0);
  const totalOut = data.reduce((s, d) => s + d.expense, 0);

  return (
    <Card
      title="キャッシュフロー推移"
      en="Cash Flow · 6 months"
      className="sm:col-span-6 lg:col-span-8"
      right={
        <div className="flex items-center gap-3 text-[11px] text-slate-500">
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-mint" />入金</span>
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-slate-300" />出金</span>
        </div>
      }
    >
      <div className="flex gap-2">
        {/* y axis */}
        <div className="flex h-48 flex-col justify-between pb-5 text-right font-mono text-[10px] text-slate-400 tabular">
          {ticks.map((t) => <span key={t} className="-translate-y-1/2 leading-none">{t / 10_000}万</span>)}
        </div>
        {/* plot */}
        <div className="relative h-48 flex-1">
          <div className="absolute inset-x-0 top-0 bottom-5 flex flex-col justify-between">
            {ticks.map((t) => <div key={t} className="border-t border-dashed border-slate-200" />)}
          </div>
          <div className="absolute inset-x-0 top-0 bottom-5 grid" style={{ gridTemplateColumns: `repeat(${data.length}, minmax(0, 1fr))` }}>
            {data.map((d, i) => (
              <div
                key={d.m}
                className={cx("relative flex items-end justify-center gap-1 rounded-md transition-colors", hover === i && "bg-slate-50")}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                tabIndex={0}
                aria-label={`${d.m} 入金 ${yen(d.income)} 出金 ${yen(d.expense)}`}
              >
                <div className="w-[26%] max-w-5 rounded-t bg-mint transition-all" style={{ height: `${(d.income / max) * 100}%` }} />
                <div className="w-[26%] max-w-5 rounded-t bg-slate-300 transition-all" style={{ height: `${(d.expense / max) * 100}%` }} />
                {hover === i && (
                  <div className={cx(
                    "pointer-events-none absolute bottom-full z-10 mb-1 whitespace-nowrap rounded-lg bg-navy px-3 py-2 text-[11px] text-white shadow-lg",
                    i === 0 ? "left-0" : i === data.length - 1 ? "right-0" : "left-1/2 -translate-x-1/2",
                  )}>
                    <p className="mb-1 font-bold">{d.m}</p>
                    <p className="flex justify-between gap-4"><span className="text-slate-300">入金</span><span className="font-mono tabular">{yen(d.income)}</span></p>
                    <p className="flex justify-between gap-4"><span className="text-slate-300">出金</span><span className="font-mono tabular">{yen(d.expense)}</span></p>
                    <p className="mt-1 flex justify-between gap-4 border-t border-white/15 pt-1"><span className="text-slate-300">収支</span><span className="font-mono text-mint tabular">{yen(d.income - d.expense)}</span></p>
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="absolute inset-x-0 bottom-0 grid h-5 text-center text-[11px] text-slate-500" style={{ gridTemplateColumns: `repeat(${data.length}, minmax(0, 1fr))` }}>
            {data.map((d, i) => <span key={d.m} className={cx("pt-1", i === data.length - 1 && "font-bold text-navy")}>{d.m}</span>)}
          </div>
        </div>
      </div>
      <dl className="grid grid-cols-3 gap-2 border-t border-slate-100 pt-3 text-[11px]">
        <div><dt className="text-slate-400">6ヶ月 入金計</dt><dd className="font-mono text-sm font-semibold text-mint-600 tabular">{yen(totalIn)}</dd></div>
        <div><dt className="text-slate-400">6ヶ月 出金計</dt><dd className="font-mono text-sm font-semibold text-navy tabular">{yen(totalOut)}</dd></div>
        <div><dt className="text-slate-400">純キャッシュフロー</dt><dd className="font-mono text-sm font-semibold text-navy tabular">{yen(totalIn - totalOut)}</dd></div>
      </dl>
    </Card>
  );
}

function QuickActions({ onInvoice, toast }: { onInvoice: () => void; toast: (m: string) => void }) {
  const [ocr, setOcr] = useState<"idle" | "reading" | "done">("idle");
  const [last, setLast] = useState<{ store: string; amount: number; rate: number } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const onFiles = (files: FileList | null) => {
    if (!files?.length) return;
    setOcr("reading");
    setTimeout(() => {
      setLast({ store: "ファミリーマート 新宿店", amount: 756, rate: 8 });
      setOcr("done");
      toast(`${files.length}件の領収書を読み取りました`);
    }, 1500);
  };

  return (
    <Card title="クイックアクション" en="Quick Actions" className="sm:col-span-6 lg:col-span-4">
      <div className="grid grid-cols-2 gap-2">
        <button onClick={onInvoice} className="flex flex-col items-start gap-2 rounded-lg bg-navy p-3 text-left text-white transition hover:bg-navy-700">
          <FileText size={20} className="text-mint" />
          <span className="text-sm font-bold">請求書作成</span>
          <span className="text-[10px] text-slate-300">適格請求書（インボイス）</span>
        </button>
        <button onClick={() => fileRef.current?.click()} className="flex flex-col items-start gap-2 rounded-lg border border-slate-200 p-3 text-left transition hover:border-mint hover:bg-mint-50">
          {ocr === "reading" ? <LoaderCircle size={20} className="animate-spin text-mint-600" /> : <Camera size={20} className="text-navy" />}
          <span className="text-sm font-bold text-navy">領収書OCR回収</span>
          <span className="text-[10px] text-slate-400">{ocr === "reading" ? "AIが読み取り中…" : "撮影 / PDF をアップロード"}</span>
        </button>
        <input ref={fileRef} type="file" accept="image/*,application/pdf" multiple hidden onChange={(e) => { onFiles(e.target.files); e.target.value = ""; }} />
      </div>

      {last && ocr === "done" ? (
        <div className="rounded-lg border border-mint-100 bg-mint-50/60 p-3 text-xs">
          <p className="mb-1 flex items-center gap-1.5 font-bold text-mint-700"><CircleCheck size={14} />読み取り結果（確認待ち）</p>
          <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-slate-600">
            <span className="text-slate-400">取引先</span><span>{last.store}</span>
            <span className="text-slate-400">金額</span><span className="font-mono tabular">{yen(last.amount)}（税率{last.rate}%）</span>
            <span className="text-slate-400">勘定科目</span><span>会議費</span>
          </div>
        </div>
      ) : (
        <label
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); onFiles(e.dataTransfer.files); }}
          className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 py-3 text-[11px] text-slate-400 hover:border-mint hover:text-mint-600"
          onClick={() => fileRef.current?.click()}
        >
          <Upload size={14} />領収書をここにドロップ
        </label>
      )}

      <ul className="space-y-1.5 text-xs">
        {[
          { n: 12, t: "未処理の領収書", tone: "text-rose-600" },
          { n: 3, t: "登録番号未確認の取引先", tone: "text-amber-600" },
          { n: 5, t: "未消込の入金", tone: "text-navy" },
        ].map((x) => (
          <li key={x.t}>
            <button onClick={() => toast(`${x.t}を開きます`)} className="flex w-full items-center gap-3 rounded-lg border border-slate-100 px-3 py-1.5 hover:bg-slate-50">
              <span className={cx("w-6 text-right font-mono text-base font-semibold tabular", x.tone)}>{x.n}</span>
              <span className="flex-1 text-left text-slate-600">{x.t}</span>
              <ChevronRight size={14} className="text-slate-300" />
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function ConsumptionTax({ tax: t }: { tax: TaxView }) {
  const { out10, out8, in10, in8 } = t;
  const net10 = out10 - in10, net8 = out8 - in8;
  const net = net10 + net8;
  const share = (n: number) => (net > 0 ? Math.max(0, Math.min(100, (n / net) * 100)) : 0);
  const due = Math.floor(net / 100) * 100 - t.interimPaid;
  const rows = [
    { label: "標準税率 10%", sub: "Standard", rate: 10, out: out10, inp: in10, net: net10, bar: "bg-navy" },
    { label: "軽減税率 8%", sub: "Reduced · 飲食料品", rate: 8, out: out8, inp: in8, net: net8, bar: "bg-mint" },
  ];
  const d = t.nextDeadline ? daysUntil(t.nextDeadline) : null;

  return (
    <Card title="消費税管理" en="Consumption Tax" className="sm:col-span-3 lg:col-span-4" right={<Badge tone="info" icon={false}>本則課税</Badge>}>
      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.rate}>
            <div className="mb-1 flex items-baseline justify-between text-xs">
              <span className="font-bold text-navy">{r.label} <span className="text-[10px] font-normal text-slate-400">{r.sub}</span></span>
              <span className="font-mono font-semibold text-navy tabular">{yen(r.net)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={Math.round(share(r.net))} aria-valuemin={0} aria-valuemax={100} aria-label={`${r.label} 納付見込の構成比`}>
              <div className={cx("h-full rounded-full", r.bar)} style={{ width: `${share(r.net)}%` }} />
            </div>
            <div className="mt-1 flex justify-between font-mono text-[10px] text-slate-400 tabular">
              <span>仮受 {yen(r.out)}</span>
              <span>仮払 −{yen(r.inp).slice(1)}</span>
              <span>{share(r.net).toFixed(1)}%</span>
            </div>
          </div>
        ))}
      </div>
      <dl className="mt-auto space-y-1 border-t border-slate-100 pt-3 text-xs">
        <div className="flex justify-between"><dt className="text-slate-500">差引税額（今期累計）</dt><dd className="font-mono tabular">{yen(Math.floor(net / 100) * 100)}</dd></div>
        <div className="flex justify-between"><dt className="text-slate-500">中間納付済</dt><dd className="font-mono tabular">−{yen(t.interimPaid).slice(1)}</dd></div>
        <div className="flex justify-between text-sm font-bold text-navy"><dt>納付見込額</dt><dd className="font-mono tabular">{yen(due)}</dd></div>
      </dl>
      {t.nextDeadline && d !== null && (
        <p className="flex items-center gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-800">
          <Clock size={13} />次回 中間申告 {t.nextDeadline.slice(5).replace("-", "/")}（あと{d}日）
        </p>
      )}
      <p className="text-[10px] text-slate-400">登録番号のない仕入は 2026/10〜2028/9 の間 70% 控除（令和8年度改正）</p>
    </Card>
  );
}

function Compliance({ reg }: { reg: string }) {
  const items = [
    { ja: "青色申告", en: "Aoiro Shinkoku", detail: "複式簿記・e-Tax 65万円控除要件", ok: true },
    { ja: "インボイス制度", en: "Qualified Invoice System", detail: `登録番号 ${reg} ・ 請求書記載要件`, ok: true },
    { ja: "電子帳簿保存法", en: "Electronic Book Preservation", detail: "タイムスタンプ・訂正削除履歴・検索要件", ok: true },
    { ja: "電子取引データ保存", en: "e-Transaction Records", detail: "取引日・金額・取引先で検索可能", ok: true },
  ];
  return (
    <Card title="法令対応ステータス" en="Compliance" className="sm:col-span-3 lg:col-span-4" right={<ShieldCheck size={16} className="text-mint" />}>
      <ul className="divide-y divide-slate-100">
        {items.map((i) => (
          <li key={i.ja} className="flex items-center gap-3 py-2 first:pt-0 last:pb-0">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-mint-50"><CircleCheck size={16} className="text-mint-600" /></span>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-navy">{i.ja} <span className="text-[10px] font-normal text-slate-400">{i.en}</span></p>
              <p className="truncate text-[11px] text-slate-400">{i.detail}</p>
            </div>
            <Badge tone="ok">適合</Badge>
          </li>
        ))}
      </ul>
      <p className="mt-auto text-[10px] text-slate-400">最終チェック 2026/11/05 09:00 JST</p>
    </Card>
  );
}

const STATUS: Record<InvoiceStatus, { ja: string; tone: "ok" | "warn" | "bad" }> = {
  paid: { ja: "支払済", tone: "ok" },
  unpaid: { ja: "未入金", tone: "warn" },
  overdue: { ja: "期日超過", tone: "bad" },
};

function InvoiceTable({ invoices, onPaid, live }: { invoices: Invoice[]; onPaid: (no: string) => void; live: boolean }) {
  const [filter, setFilter] = useState<"all" | InvoiceStatus>("all");
  const rows = invoices.filter((i) => filter === "all" || i.status === filter).slice(0, 6);
  const open = invoices.filter((i) => i.status !== "paid").reduce((s, i) => s + i.amount, 0);

  const markPaid = onPaid;

  return (
    <Card
      title="最近の請求書"
      en="Recent Invoices"
      className="sm:col-span-6 lg:col-span-12"
      right={<span className="text-[11px] text-slate-500">未回収合計 <span className="font-mono font-bold text-navy tabular">{yen(open)}</span></span>}
    >
      <div className="flex flex-wrap gap-1">
        {(["all", "unpaid", "overdue", "paid"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            aria-pressed={filter === f}
            className={cx("rounded-full px-2.5 py-0.5 text-[11px] ring-1 ring-inset", filter === f ? "bg-navy text-white ring-navy" : "text-slate-500 ring-slate-200 hover:bg-slate-50")}
          >
            {f === "all" ? "すべて" : STATUS[f].ja}
          </button>
        ))}
      </div>
      <div className="-mx-4 overflow-x-auto">
        <table className="w-full min-w-[640px] text-xs">
          <thead>
            <tr className="border-y border-slate-100 bg-slate-50 text-left text-[10px] uppercase tracking-wider text-slate-400">
              <th className="px-4 py-2 font-medium">請求書番号</th>
              <th className="px-2 py-2 font-medium">取引先</th>
              <th className="px-2 py-2 font-medium">発行日</th>
              <th className="px-2 py-2 font-medium">支払期日</th>
              <th className="px-2 py-2 text-right font-medium">金額（税込）</th>
              <th className="px-2 py-2 text-right font-medium">うち消費税</th>
              <th className="px-2 py-2 font-medium">状態</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((i) => (
              <tr key={i.no} className="hover:bg-slate-50/70">
                <td className="whitespace-nowrap px-4 py-2 font-mono text-navy">
                  {live ? <a href={api.pdfUrl(i.no)} className="hover:underline" onClick={(e) => { e.preventDefault(); openPdf(i.no); }}>{i.no}</a> : i.no}
                </td>
                <td className="max-w-[220px] truncate px-2 py-2 text-slate-700">{i.client}</td>
                <td className="whitespace-nowrap px-2 py-2 font-mono text-slate-500 tabular">{i.issued.replaceAll("-", "/")}</td>
                <td className="whitespace-nowrap px-2 py-2 font-mono text-slate-500 tabular">{i.due.replaceAll("-", "/")}</td>
                <td className="whitespace-nowrap px-2 py-2 text-right font-mono font-semibold text-navy tabular">{yen(i.amount)}</td>
                <td className="whitespace-nowrap px-2 py-2 text-right font-mono text-slate-500 tabular">
                  <span className={cx("mr-1 rounded px-1 text-[9px] font-bold", i.rate === 8 ? "bg-mint-50 text-mint-700" : "bg-slate-100 text-navy")}>{i.rate}%</span>
                  {yen(taxIn(i.amount, i.rate))}
                </td>
                <td className="px-2 py-2"><Badge tone={STATUS[i.status].tone}>{STATUS[i.status].ja}</Badge></td>
                <td className="whitespace-nowrap px-4 py-2 text-right">
                  {i.status !== "paid" ? (
                    <button onClick={() => markPaid(i.no)} className="rounded-md border border-slate-200 px-2 py-0.5 text-[11px] text-slate-600 hover:border-mint hover:text-mint-700">消込</button>
                  ) : (
                    <span className="text-[11px] text-slate-300">—</span>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-6 text-center text-slate-400">該当する請求書はありません</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/* ============================================================
 * INVOICE CREATE DRAWER (qualified invoice fields)
 * ============================================================ */

function InvoiceDrawer({ open, onClose, onCreate }: { open: boolean; onClose: () => void; onCreate: (i: Invoice) => void }) {
  const [client, setClient] = useState("");
  const [amount, setAmount] = useState("");
  const [rate, setRate] = useState<10 | 8>(10);
  const [due, setDue] = useState("2026-12-31");
  const gross = Number(amount.replace(/,/g, "")) || 0;
  const tax = taxIn(gross, rate);

  useEffect(() => { if (open) { setClient(""); setAmount(""); setRate(10); } }, [open]);
  if (!open) return null;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!client || gross <= 0) return;
    onCreate({ no: `INV-DEMO-${Date.now().toString().slice(-4)}`, client, issued: new Date().toISOString().slice(0, 10), due, amount: gross, rate, status: "unpaid" });
  };

  return (
    <div className="fixed inset-0 z-[65] flex justify-end bg-slate-900/40" onMouseDown={onClose}>
      <form onSubmit={submit} onMouseDown={(e) => e.stopPropagation()} className="flex h-full w-full max-w-md flex-col bg-white shadow-2xl" aria-label="請求書作成">
        <div className="flex h-14 items-center border-b border-slate-200 px-5">
          <h3 className="text-sm font-bold text-navy">請求書作成 <span className="text-[10px] font-normal text-slate-400">New Qualified Invoice</span></h3>
          <button type="button" onClick={onClose} className="ml-auto rounded p-1 text-slate-400 hover:text-navy" aria-label="閉じる"><X size={18} /></button>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto p-5 text-xs">
          <label className="block space-y-1">
            <span className="font-bold text-slate-600">取引先</span>
            <input id="inv-client" value={client} onChange={(e) => setClient(e.target.value)} required placeholder="株式会社〇〇" className="h-9 w-full rounded-lg border border-slate-200 px-3 outline-none focus:border-navy" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block space-y-1">
              <span className="font-bold text-slate-600">金額（税込・円）</span>
              <input id="inv-amount" inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^\d,]/g, ""))} required placeholder="1,100,000" className="h-9 w-full rounded-lg border border-slate-200 px-3 font-mono outline-none focus:border-navy" />
            </label>
            <label className="block space-y-1">
              <span className="font-bold text-slate-600">支払期日</span>
              <input id="inv-due" type="date" value={due} onChange={(e) => setDue(e.target.value)} className="h-9 w-full rounded-lg border border-slate-200 px-3 outline-none focus:border-navy" />
            </label>
          </div>
          <fieldset className="space-y-1">
            <legend className="font-bold text-slate-600">税率</legend>
            <div className="grid grid-cols-2 gap-2">
              {([10, 8] as const).map((r) => (
                <button key={r} type="button" onClick={() => setRate(r)} aria-pressed={rate === r}
                  className={cx("rounded-lg border px-3 py-2 text-left", rate === r ? "border-navy bg-slate-50" : "border-slate-200")}>
                  <span className="block font-bold text-navy">{r}%</span>
                  <span className="text-[10px] text-slate-400">{r === 10 ? "標準税率" : "軽減税率（飲食料品等）"}</span>
                </button>
              ))}
            </div>
          </fieldset>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">適格請求書 記載事項プレビュー</p>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
              <dt className="text-slate-400">登録番号</dt><dd className="font-mono">T3010001222222</dd>
              <dt className="text-slate-400">税率ごとの対価</dt><dd className="font-mono tabular">{yen(gross)}（{rate}%対象）</dd>
              <dt className="text-slate-400">消費税額</dt><dd className="font-mono tabular">{yen(tax)}</dd>
              <dt className="text-slate-400">税抜金額</dt><dd className="font-mono tabular">{yen(gross - tax)}</dd>
            </dl>
          </div>
        </div>
        <div className="flex gap-2 border-t border-slate-200 p-4">
          <button type="button" onClick={onClose} className="h-9 flex-1 rounded-lg border border-slate-200 text-xs text-slate-600">キャンセル</button>
          <button type="submit" className="flex h-9 flex-1 items-center justify-center gap-1.5 rounded-lg bg-navy text-xs font-bold text-white hover:bg-navy-700"><Plus size={14} />発行する</button>
        </div>
      </form>
    </div>
  );
}

/* ============================================================
 * PAGE
 * ============================================================ */

export default function DashboardPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [invOpen, setInvOpen] = useState(false);
  const data = useDashboardData();
  const { mode, invoices, setInvoices, company, setCompany } = data;
  const live = mode === "live";
  const { show: toast, node: toastNode } = useToast();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setSearchOpen(true); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const onPaid = async (no: string) => {
    if (!live) {
      setInvoices((p) => p.map((i) => (i.no === no ? { ...i, status: "paid" } : i)));
      toast(`${no} を入金消込しました（デモ）`);
      return;
    }
    try {
      const r = await api.payInvoice(no);
      setInvoices((p) => p.map((i) => (i.no === no ? toInvoice({ ...r, overdue: false }) : i)));
      toast(`${no} を入金消込しました`);
      data.reload();
    } catch (e) {
      toast(`消込に失敗しました: ${e instanceof Error ? e.message : e}`);
    }
  };

  const onCreate = async (i: Invoice) => {
    setInvOpen(false);
    if (!live) {
      setInvoices((p) => [i, ...p]);
      toast(`${i.no} を発行しました（デモ）`);
      return;
    }
    try {
      const unit = i.amount - taxIn(i.amount, i.rate); // 税込 → 税抜
      const r = await api.createInvoice({ client: i.client, due: i.due, items: [{ name: "ご請求分", qty: 1, unit_price: unit, rate: i.rate }] });
      setInvoices((p) => [toInvoice({ ...r, overdue: false }), ...p]);
      toast(`${r.no} を発行しました`);
    } catch (e) {
      toast(`発行に失敗しました: ${e instanceof Error ? e.message : e}`);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} company={company} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenu={() => setMenuOpen(true)} onSearch={() => setSearchOpen(true)} company={company} setCompany={setCompany} toast={toast} />

        <main className="mx-auto w-full max-w-[1400px] flex-1 p-3 sm:p-5">
          <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1">
            <h1 className="text-lg font-bold text-navy">ダッシュボード</h1>
            <p className="text-xs text-slate-400">{company.name} ・ {company.fiscal}</p>
            <div className="ml-auto flex items-center gap-2">
              {mode === "loading" && <Badge tone="info" icon={false}><LoaderCircle size={11} className="animate-spin" />読み込み中</Badge>}
              {mode === "demo" && (
                <>
                  <Badge tone="warn">デモデータ</Badge>
                  <a href="/connect" className="text-[11px] font-bold text-navy underline-offset-2 hover:underline">自分の帳簿に接続</a>
                </>
              )}
              {live && (
                <>
                  <Badge tone="ok">ライブ</Badge>
                  <button onClick={() => { setToken(null); location.reload(); }} className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-navy">
                    <LogOut size={12} />切断
                  </button>
                </>
              )}
            </div>
          </div>
          {data.error && mode === "demo" && (
            <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">サーバーに接続できなかったため、デモデータを表示しています（{data.error}）。</p>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-6 lg:grid-cols-12">
            <KpiCards cashflow={data.cashflow} />
            <CashFlowChart cashflow={data.cashflow} />
            <QuickActions onInvoice={() => setInvOpen(true)} toast={toast} />
            <ConsumptionTax tax={data.tax} />
            <Compliance reg={company.reg} />
            <BankSync />
            <InvoiceTable invoices={invoices} onPaid={onPaid} live={live} />
          </div>
        </main>
      </div>

      <CommandPalette open={searchOpen} onClose={() => setSearchOpen(false)} onPick={(l) => { setSearchOpen(false); toast(`「${l}」を開きます`); }} />
      <InvoiceDrawer open={invOpen} onClose={() => setInvOpen(false)} onCreate={onCreate} />
      {toastNode}
    </div>
  );
}

async function openPdf(no: string) {
  // PDF uç noktası Bearer token ister: blob olarak alıp yeni sekmede aç
  const token = getToken();
  if (!token) return;
  const res = await fetch(api.pdfUrl(no), { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) return;
  const url = URL.createObjectURL(await res.blob());
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/* Banka bağlantı kartı (bento'yu 3 sütunda tamamlar) */
function BankSync() {
  return (
    <Card title="銀行連携" en="Bank Accounts" className="sm:col-span-6 lg:col-span-4" right={<Badge tone="ok">全口座 接続済</Badge>}>
      <ul className="divide-y divide-slate-100">
        {MOCK.banks.map((b) => (
          <li key={b.name} className="flex items-center gap-3 py-2 first:pt-0">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-slate-100 text-xs font-bold text-navy">{b.name[0]}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-bold text-navy">{b.name}</p>
              <p className="font-mono text-[10px] text-slate-400">{b.acct} ・ 最終同期 {b.synced}</p>
            </div>
            <Badge tone="ok">連携中</Badge>
          </li>
        ))}
      </ul>
      <p className="mt-auto rounded-lg bg-slate-50 px-2.5 py-1.5 text-[11px] text-slate-500">銀行API（参照系・電子決済等代行業）・ 15分ごとに自動取得</p>
    </Card>
  );
}
