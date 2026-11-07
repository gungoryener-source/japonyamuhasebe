"use client";

/**
 * J-SaaS 会計 — ダッシュボード (app/page.tsx)
 * Kabuk (menü/üst çubuk) components/shell.tsx'te; ortak UI components/ui.tsx'te; demo veri lib/demo.ts'te.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, getToken, monthLabel, setToken, type ApiInvoice } from "./lib/api";
import {
  compute, KANI_LABEL, KANI_RATIO, METHOD_LABEL, methodUnavailable, settle, TRANSITIONAL_CREDIT, transitionalBreakdown,
  type Method, type Purchase, type Sale, type Transitional,
} from "./lib/tax";
import {
  ArrowDownRight, ArrowUpRight, Calculator, Camera, ChevronRight, CircleCheck, Clock, FileText,
  LoaderCircle, Plus, Receipt, ShieldCheck, Upload, Wallet, X,
} from "lucide-react";
import { parseRole, type Role } from "./lib/team";
import { MOCK, type Company, type Invoice, type InvoiceStatus } from "./lib/demo";
import { Badge, Card, cx, daysUntil, pct, ReadOnlyNote, taxIn, yen } from "./components/ui";
import { AppShell, useShell } from "./components/shell";
import { currentLang, T } from "./lib/i18n";

/* ============================================================
 * DATA (live API or demo)
 * ============================================================ */

type CashMonth = { m: string; income: number; expense: number };
/** 消費税カードの入力: 本則課税の税率別集計（API by_rate と同じ）+ 経過措置の内訳。方式の切替はカード内で settle() する。 */
type TaxView = {
  out10: number; out8: number; in10: number; in8: number; unqualified: Transitional[];
  interimPaid: number; nextDeadline: string | null; taxYear: number; individual: boolean;
};
type Mode = "loading" | "live" | "demo";

function demoTax(): TaxView {
  const t = MOCK.tax;
  const r = compute(t.sales, t.purchases, "honsoku");
  return {
    out10: r.byRate["10"].output, out8: r.byRate["8"].output, in10: r.byRate["10"].input, in8: r.byRate["8"].input,
    unqualified: transitionalBreakdown(t.purchases), interimPaid: t.interimPaid, nextDeadline: t.nextDeadline,
    taxYear: t.taxYear, individual: t.individual,
  };
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
  const [email, setEmail] = useState<string | null>(null);
  const [role, setRole] = useState<Role>("owner");

  const load = useCallback(async () => {
    if (!getToken()) { setMode("demo"); return; }
    // Rol (T-041) "live"dan önce çözülür: viewer'a düzenleme düğmeleri bir an bile görünmesin.
    const me = api.me().catch(() => null);
    try {
      const now = new Date();
      const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const end = `${lastMonth.getFullYear()}-${String(lastMonth.getMonth() + 1).padStart(2, "0")}`;
      const [cf, tx, inv, prof, m] = await Promise.all([api.cashflow(6, end), api.tax(now.getFullYear()), api.invoices(), api.profile(), me]);
      setEmail(m?.account?.email ?? null);
      setRole(parseRole(m?.role));
      setCashflow(cf.map((c) => ({ m: monthLabel(c.month), income: c.income, expense: c.expense })));
      setTax({
        out10: tx.by_rate["10"].output, out8: tx.by_rate["8"].output, in10: tx.by_rate["10"].input, in8: tx.by_rate["8"].input,
        unqualified: tx.unqualified ?? [], interimPaid: 0, nextDeadline: null, taxYear: tx.year, individual: Boolean(prof.individual),
      });
      setInvoices(inv.map(toInvoice));
      setCompany({ id: prof.user_id, name: prof.business_name || T("事業者名未設定"), reg: prof.registration_no || T("登録番号未設定"), fiscal: T("{a}年分", { a: now.getFullYear() }) });
      setError(null);
      setMode("live");
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setToken(null);
      setError(e instanceof Error ? e.message : String(e));
      setMode("demo");
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { mode, cashflow, tax, invoices, setInvoices, company, setCompany, error, email, role, reload: load };
}


/* ============================================================
 * WIDGETS
 * ============================================================ */

function KpiCards({ cashflow }: { cashflow: CashMonth[] }) {
  const cf = cashflow.length >= 2 ? cashflow : [{ m: "", income: 0, expense: 0 }, ...cashflow, { m: "", income: 0, expense: 0 }].slice(-2);
  const cur = cf[cf.length - 1], prev = cf[cf.length - 2];
  const items = [
    { ja: T("売上高"), en: "Monthly Revenue", v: cur.income, d: pct(cur.income, prev.income), goodWhenUp: true, icon: Wallet },
    { ja: T("経費総額"), en: "Total Expenses", v: cur.expense, d: pct(cur.expense, prev.expense), goodWhenUp: false, icon: Receipt },
    { ja: T("差引利益"), en: "Est. Net Profit", v: cur.income - cur.expense, d: pct(cur.income - cur.expense, prev.income - prev.expense), goodWhenUp: true, icon: Calculator },
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
              <span className="font-bold text-slate-600">{T(k.ja)}</span>
              <span className="text-[10px] text-slate-400">{k.en}</span>
              <span className="ml-auto text-[10px] text-slate-400">{cur.m}</span>
            </div>
            <p className="truncate font-mono text-2xl font-semibold tracking-tight text-navy tabular">{yen(k.v)}</p>
            <p className={cx("flex items-center gap-1 text-xs font-bold", good ? "text-mint-600" : "text-rose-600")}>
              <Arrow size={14} />
              {d >= 0 ? "+" : "−"}{Math.abs(d).toFixed(0)}%
              <span className="font-normal text-slate-400">{T("前月比")}</span>
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
      title={T("キャッシュフロー推移")}
      en="Cash Flow · 6 months"
      className="sm:col-span-6 lg:col-span-8"
      right={
        <div className="flex items-center gap-3 text-[11px] text-slate-500">
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-mint" />{T("入金")}</span>
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-slate-300" />{T("出金")}</span>
        </div>
      }
    >
      <div className="flex gap-2">
        {/* y axis */}
        <div className="flex h-48 flex-col justify-between pb-5 text-right font-mono text-[10px] text-slate-400 tabular">
          {ticks.map((t) => <span key={t} className="-translate-y-1/2 leading-none">{currentLang() === "ja" ? `${t / 10_000}万` : `${(t / 1_000_000).toLocaleString("en-US", { maximumFractionDigits: 1 })}M`}</span>)}
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
                aria-label={T("{a} 入金 {b} 出金 {c}", { a: d.m, b: yen(d.income), c: yen(d.expense) })}
              >
                <div className="w-[26%] max-w-5 rounded-t bg-mint transition-all" style={{ height: `${(d.income / max) * 100}%` }} />
                <div className="w-[26%] max-w-5 rounded-t bg-slate-300 transition-all" style={{ height: `${(d.expense / max) * 100}%` }} />
                {hover === i && (
                  <div className={cx(
                    "pointer-events-none absolute bottom-full z-10 mb-1 whitespace-nowrap rounded-lg bg-navy px-3 py-2 text-[11px] text-white shadow-lg",
                    i === 0 ? "left-0" : i === data.length - 1 ? "right-0" : "left-1/2 -translate-x-1/2",
                  )}>
                    <p className="mb-1 font-bold">{d.m}</p>
                    <p className="flex justify-between gap-4"><span className="text-slate-300">{T("入金")}</span><span className="font-mono tabular">{yen(d.income)}</span></p>
                    <p className="flex justify-between gap-4"><span className="text-slate-300">{T("出金")}</span><span className="font-mono tabular">{yen(d.expense)}</span></p>
                    <p className="mt-1 flex justify-between gap-4 border-t border-white/15 pt-1"><span className="text-slate-300">{T("収支")}</span><span className="font-mono text-mint tabular">{yen(d.income - d.expense)}</span></p>
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
        <div><dt className="text-slate-400">{T("6ヶ月 入金計")}</dt><dd className="font-mono text-sm font-semibold text-mint-600 tabular">{yen(totalIn)}</dd></div>
        <div><dt className="text-slate-400">{T("6ヶ月 出金計")}</dt><dd className="font-mono text-sm font-semibold text-navy tabular">{yen(totalOut)}</dd></div>
        <div><dt className="text-slate-400">{T("純キャッシュフロー")}</dt><dd className="font-mono text-sm font-semibold text-navy tabular">{yen(totalIn - totalOut)}</dd></div>
      </dl>
    </Card>
  );
}

function QuickActions({ onInvoice, toast, canEdit = true }: { onInvoice: () => void; toast: (m: string) => void; canEdit?: boolean }) {
  const [ocr, setOcr] = useState<"idle" | "reading" | "done">("idle");
  const [last, setLast] = useState<{ store: string; amount: number; rate: number } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const onFiles = (files: FileList | null) => {
    if (!files?.length) return;
    setOcr("reading");
    setTimeout(() => {
      setLast({ store: "ファミリーマート 新宿店", amount: 756, rate: 8 });
      setOcr("done");
      toast(T("{a}件の領収書を読み取りました", { a: files.length }));
    }, 1500);
  };

  return (
    <Card title="クイックアクション" en="Quick Actions" className="sm:col-span-6 lg:col-span-4">
      {!canEdit ? <ReadOnlyNote /> : <>
      <div className="grid grid-cols-2 gap-2">
        <button onClick={onInvoice} className="flex flex-col items-start gap-2 rounded-lg bg-navy p-3 text-left text-white transition hover:bg-navy-700">
          <FileText size={20} className="text-mint" />
          <span className="text-sm font-bold">{T("請求書作成")}</span>
          <span className="text-[10px] text-slate-300">{T("適格請求書（インボイス）")}</span>
        </button>
        <button onClick={() => fileRef.current?.click()} className="flex flex-col items-start gap-2 rounded-lg border border-slate-200 p-3 text-left transition hover:border-mint hover:bg-mint-50">
          {ocr === "reading" ? <LoaderCircle size={20} className="animate-spin text-mint-600" /> : <Camera size={20} className="text-navy" />}
          <span className="text-sm font-bold text-navy">{T("領収書OCR回収")}</span>
          <span className="text-[10px] text-slate-400">{ocr === "reading" ? T("AIが読み取り中…") : T("撮影 / PDF をアップロード")}</span>
        </button>
        <input ref={fileRef} type="file" accept="image/*,application/pdf" multiple hidden onChange={(e) => { onFiles(e.target.files); e.target.value = ""; }} />
      </div>

      {last && ocr === "done" ? (
        <div className="rounded-lg border border-mint-100 bg-mint-50/60 p-3 text-xs">
          <p className="mb-1 flex items-center gap-1.5 font-bold text-mint-700"><CircleCheck size={14} />{T("読み取り結果（確認待ち）")}</p>
          <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-slate-600">
            <span className="text-slate-400">{T("取引先")}</span><span>{last.store}</span>
            <span className="text-slate-400">{T("金額")}</span><span className="font-mono tabular">{yen(last.amount)}{T("（税率")}{last.rate}%）</span>
            <span className="text-slate-400">{T("勘定科目")}</span><span>{T("会議費")}</span>
          </div>
        </div>
      ) : (
        <label
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); onFiles(e.dataTransfer.files); }}
          className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 py-3 text-[11px] text-slate-400 hover:border-mint hover:text-mint-600"
          onClick={() => fileRef.current?.click()}
        >
          <Upload size={14} />{T("領収書をここにドロップ")}
        </label>
      )}
      </>}

      <ul className="space-y-1.5 text-xs">
        {[
          { n: 12, t: T("未処理の領収書"), tone: "text-rose-600" },
          { n: 3, t: T("登録番号未確認の取引先"), tone: "text-amber-600" },
          { n: 5, t: T("未消込の入金"), tone: "text-navy" },
        ].map((x) => (
          <li key={x.t}>
            <button onClick={() => toast(T("{x}を開きます", { x: T(x.t) }))} className="flex w-full items-center gap-3 rounded-lg border border-slate-100 px-3 py-1.5 hover:bg-slate-50">
              <span className={cx("w-6 text-right font-mono text-base font-semibold tabular", x.tone)}>{x.n}</span>
              <span className="flex-1 text-left text-slate-600">{T(x.t)}</span>
              <ChevronRight size={14} className="text-slate-300" />
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}

/** 経過措置の控除割合 → 適用期間ラベル（TRANSITIONAL_CREDIT から生成） */
function ratioPeriod(ratio: number): string {
  const i = TRANSITIONAL_CREDIT.findIndex(([, p]) => p === ratio);
  if (i < 0) return "";
  const ym = (iso: string) => `${iso.slice(0, 4)}/${Number(iso.slice(5, 7))}`;
  const from = ym(TRANSITIONAL_CREDIT[i][0]);
  const next = TRANSITIONAL_CREDIT[i + 1]?.[0];
  if (!next) return `${from}〜`;
  const last = new Date(`${next}T00:00:00Z`); last.setUTCDate(0); // 前月末
  return `${from}〜${ym(last.toISOString().slice(0, 10))}`;
}

const METHODS: Method[] = ["honsoku", "kani", "niwari", "sanwari"];

function ConsumptionTax({ tax: t }: { tax: TaxView }) {
  const [method, setMethod] = useState<Method>("honsoku");
  const [kaniType, setKaniType] = useState(5);
  const opts = { kaniType, individual: t.individual, taxYear: t.taxYear };
  const unavailable = (m: Method) => methodUnavailable(m, { ...opts, kaniType: m === "kani" ? kaniType : null });
  const active: Method = unavailable(method) ? "honsoku" : method;

  const { out10, out8, in10, in8 } = t;
  const output = out10 + out8;
  const { input, payable } = settle(output, in10 + in8, active, opts);
  const honsoku = active === "honsoku";
  // 本則: 税率別の差引税額 / 簡易・特例: 税率別の売上税額（控除は売上税額から一括計算）
  const rows = [
    { label: T("標準税率 10%"), sub: "Standard", rate: 10, out: out10, inp: in10, bar: "bg-navy" },
    { label: T("軽減税率 8%"), sub: T("Reduced · 飲食料品"), rate: 8, out: out8, inp: in8, bar: "bg-mint" },
  ].map((r) => ({ ...r, net: honsoku ? r.out - r.inp : r.out }));
  const total = rows.reduce((a, r) => a + r.net, 0);
  const share = (n: number) => (total > 0 ? Math.max(0, Math.min(100, (n / total) * 100)) : 0);
  const due = payable - t.interimPaid;
  const d = t.nextDeadline ? daysUntil(t.nextDeadline) : null;
  const deductionLabel = { honsoku: T("控除対象仕入税額"), kani: T("みなし仕入税額（{a}%）", { a: KANI_RATIO[kaniType] }), niwari: T("特例控除（売上税額×80%）"), sanwari: T("特例控除（売上税額×70%）") }[active];

  return (
    <Card title="消費税管理" en="Consumption Tax" className="sm:col-span-3 lg:col-span-4" right={<Badge tone="info" icon={false}>{t.taxYear}年分 ・ {T(METHOD_LABEL[active])}</Badge>}>
      <div role="radiogroup" aria-label={T("課税方式")} className="grid grid-cols-4 gap-1 rounded-lg bg-slate-100 p-0.5 text-[11px] font-bold">
        {METHODS.map((m) => {
          const why = unavailable(m);
          return (
            <button key={m} role="radio" aria-checked={active === m} disabled={!!why} title={T(why ?? METHOD_LABEL[m])} onClick={() => setMethod(m)}
              className={cx("rounded-md px-1 py-1", active === m ? "bg-white text-navy shadow-sm" : "text-slate-500 hover:text-navy", why && "cursor-not-allowed opacity-40 hover:text-slate-500")}>
              {T(METHOD_LABEL[m])}
            </button>
          );
        })}
      </div>
      {active === "kani" && (
        <label className="flex items-center gap-2 text-[11px] text-slate-500">
          {T("事業区分")}
          <select value={kaniType} onChange={(e) => setKaniType(Number(e.target.value))} className="flex-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-navy">
            {Object.keys(KANI_RATIO).map(Number).map((k) => <option key={k} value={k}>{KANI_LABEL[k]}{T("（みなし仕入率")} {KANI_RATIO[k]}%）</option>)}
          </select>
        </label>
      )}

      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.rate}>
            <div className="mb-1 flex items-baseline justify-between text-xs">
              <span className="font-bold text-navy">{T(r.label)} <span className="text-[10px] font-normal text-slate-400">{r.sub}</span></span>
              <span className="font-mono font-semibold text-navy tabular">{yen(r.net)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={Math.round(share(r.net))} aria-valuemin={0} aria-valuemax={100} aria-label={T("{a} の構成比", { a: r.label })}>
              <div className={cx("h-full rounded-full", r.bar)} style={{ width: `${share(r.net)}%` }} />
            </div>
            <div className="mt-1 flex justify-between font-mono text-[10px] text-slate-400 tabular">
              <span>{T("仮受")} {yen(r.out)}</span>
              {honsoku && <span>{T("仮払 −")}{yen(r.inp).slice(1)}</span>}
              <span>{share(r.net).toFixed(1)}%</span>
            </div>
          </div>
        ))}
      </div>

      {t.unqualified.length > 0 && (
        <div className={cx("rounded-lg border border-slate-100 px-2.5 py-2", !honsoku && "opacity-50")}>
          <p className="mb-1 text-[11px] font-bold text-navy">{T("登録番号のない仕入（経過措置）")}</p>
          <table className="w-full font-mono text-[10px] text-slate-500 tabular">
            <thead><tr className="text-slate-400"><th className="text-left font-medium">{T("期間・控除割合")}</th><th className="text-right font-medium">{T("消費税額")}</th><th className="text-right font-medium">{T("控除額")}</th></tr></thead>
            <tbody>
              {t.unqualified.map((u) => (
                <tr key={u.ratio}>
                  <td className="py-0.5 font-sans">{ratioPeriod(u.ratio)} <span className="font-bold text-navy">{u.ratio}%</span></td>
                  <td className="text-right">{yen(u.tax)}</td>
                  <td className="text-right text-navy">{yen(u.credited)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!honsoku && <p className="mt-1 text-[10px] text-slate-400">{METHOD_LABEL[active]}{T("では仕入税額を使わないため計算に影響しません")}</p>}
        </div>
      )}

      <dl className="mt-auto space-y-1 border-t border-slate-100 pt-3 text-xs">
        <div className="flex justify-between"><dt className="text-slate-500">{T("売上税額")}</dt><dd className="font-mono tabular">{yen(output)}</dd></div>
        <div className="flex justify-between"><dt className="text-slate-500">{deductionLabel}</dt><dd className="font-mono tabular">−{yen(input).slice(1)}</dd></div>
        <div className="flex justify-between"><dt className="text-slate-500">{T("差引税額（100円未満切捨て）")}</dt><dd className="font-mono tabular">{yen(payable)}</dd></div>
        <div className="flex justify-between"><dt className="text-slate-500">{T("中間納付済")}</dt><dd className="font-mono tabular">−{yen(t.interimPaid).slice(1)}</dd></div>
        <div className="flex justify-between text-sm font-bold text-navy"><dt>{due < 0 ? T("還付見込額") : T("納付見込額")}</dt><dd className="font-mono tabular">{yen(Math.abs(due))}</dd></div>
      </dl>
      {t.nextDeadline && d !== null && (
        <p className="flex items-center gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-800">
          <Clock size={13} />{T("次回 中間申告")} {t.nextDeadline.slice(5).replace("-", "/")}{T("（あと")}{d}{T("日）")}
        </p>
      )}
      <p className="text-[10px] leading-relaxed text-slate-400">
        {active === "kani" ? T("簡易課税のみなし仕入率は第1種90%〜第6種40%（基準期間の課税売上高5,000万円以下・事前の届出が必要）。")
          : active === "niwari" ? T("2割特例は免税事業者からインボイス登録した事業者が対象（令和8年分まで）。")
          : active === "sanwari" ? T("3割特例は個人事業者の令和9・10年分が対象（令和8年度改正）。")
          : T("登録番号のない仕入は 2026/10〜2028/9 の間 70% 控除（令和8年度改正）。個人は令和9・10年分に3割特例あり。")}
      </p>
    </Card>
  );
}

function Compliance({ reg }: { reg: string }) {
  const items = [
    { ja: T("青色申告"), en: "Aoiro Shinkoku", detail: T("複式簿記・e-Tax 65万円控除要件"), ok: true },
    { ja: T("インボイス制度"), en: "Qualified Invoice System", detail: T("登録番号 {a} ・ 請求書記載要件", { a: reg }), ok: true },
    { ja: T("電子帳簿保存法"), en: "Electronic Book Preservation", detail: T("タイムスタンプ・訂正削除履歴・検索要件"), ok: true },
    { ja: T("電子取引データ保存"), en: "e-Transaction Records", detail: T("取引日・金額・取引先で検索可能"), ok: true },
  ];
  return (
    <Card title="法令対応ステータス" en="Compliance" className="sm:col-span-3 lg:col-span-4" right={<ShieldCheck size={16} className="text-mint" />}>
      <ul className="divide-y divide-slate-100">
        {items.map((i) => (
          <li key={i.ja} className="flex items-center gap-3 py-2 first:pt-0 last:pb-0">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-mint-50"><CircleCheck size={16} className="text-mint-600" /></span>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-navy">{T(i.ja)} <span className="text-[10px] font-normal text-slate-400">{i.en}</span></p>
              <p className="truncate text-[11px] text-slate-400">{T(i.detail)}</p>
            </div>
            <Badge tone="ok">{T("適合")}</Badge>
          </li>
        ))}
      </ul>
      <p className="mt-auto text-[10px] text-slate-400">{T("最終チェック 2026/11/05 09:00 JST")}</p>
    </Card>
  );
}

const STATUS: Record<InvoiceStatus, { ja: string; tone: "ok" | "warn" | "bad" }> = {
  paid: { ja: "支払済", tone: "ok" },
  unpaid: { ja: "未入金", tone: "warn" },
  overdue: { ja: "期日超過", tone: "bad" },
};

function InvoiceTable({ invoices, onPaid, live }: { invoices: Invoice[]; onPaid?: (no: string) => void; live: boolean }) {
  const [filter, setFilter] = useState<"all" | InvoiceStatus>("all");
  const rows = invoices.filter((i) => filter === "all" || i.status === filter).slice(0, 6);
  const open = invoices.filter((i) => i.status !== "paid").reduce((s, i) => s + i.amount, 0);

  const markPaid = onPaid;

  return (
    <Card
      title={T("最近の請求書")}
      en="Recent Invoices"
      className="sm:col-span-6 lg:col-span-12"
      right={<span className="text-[11px] text-slate-500">{T("未回収合計")} <span className="font-mono font-bold text-navy tabular">{yen(open)}</span></span>}
    >
      <div className="flex flex-wrap gap-1">
        {(["all", "unpaid", "overdue", "paid"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            aria-pressed={filter === f}
            className={cx("rounded-full px-2.5 py-0.5 text-[11px] ring-1 ring-inset", filter === f ? "bg-navy text-white ring-navy" : "text-slate-500 ring-slate-200 hover:bg-slate-50")}
          >
            {f === "all" ? T("すべて") : T(STATUS[f].ja)}
          </button>
        ))}
      </div>
      <div className="-mx-4 overflow-x-auto">
        <table className="w-full min-w-[640px] text-xs">
          <thead>
            <tr className="border-y border-slate-100 bg-slate-50 text-left text-[10px] uppercase tracking-wider text-slate-400">
              <th className="px-4 py-2 font-medium">{T("請求書番号")}</th>
              <th className="px-2 py-2 font-medium">{T("取引先")}</th>
              <th className="px-2 py-2 font-medium">{T("発行日")}</th>
              <th className="px-2 py-2 font-medium">{T("支払期日")}</th>
              <th className="px-2 py-2 text-right font-medium">{T("金額（税込）")}</th>
              <th className="px-2 py-2 text-right font-medium">{T("うち消費税")}</th>
              <th className="px-2 py-2 font-medium">{T("状態")}</th>
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
                <td className="px-2 py-2"><Badge tone={STATUS[i.status].tone}>{T(STATUS[i.status].ja)}</Badge></td>
                <td className="whitespace-nowrap px-4 py-2 text-right">
                  {i.status !== "paid" && markPaid ? (
                    <button onClick={() => markPaid(i.no)} className="rounded-md border border-slate-200 px-2 py-0.5 text-[11px] text-slate-600 hover:border-mint hover:text-mint-700">{T("消込")}</button>
                  ) : (
                    <span className="text-[11px] text-slate-300">—</span>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-6 text-center text-slate-400">{T("該当する請求書はありません")}</td></tr>
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
      <form onSubmit={submit} onMouseDown={(e) => e.stopPropagation()} className="flex h-full w-full max-w-md flex-col bg-white shadow-2xl" aria-label={T("請求書作成")}>
        <div className="flex h-14 items-center border-b border-slate-200 px-5">
          <h3 className="text-sm font-bold text-navy">{T("請求書作成")} <span className="text-[10px] font-normal text-slate-400">New Qualified Invoice</span></h3>
          <button type="button" onClick={onClose} className="ml-auto rounded p-1 text-slate-400 hover:text-navy" aria-label={T("閉じる")}><X size={18} /></button>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto p-5 text-xs">
          <label className="block space-y-1">
            <span className="font-bold text-slate-600">{T("取引先")}</span>
            <input id="inv-client" value={client} onChange={(e) => setClient(e.target.value)} required placeholder={T("株式会社〇〇")} className="h-9 w-full rounded-lg border border-slate-200 px-3 outline-none focus:border-navy" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block space-y-1">
              <span className="font-bold text-slate-600">{T("金額（税込・円）")}</span>
              <input id="inv-amount" inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^\d,]/g, ""))} required placeholder="1,100,000" className="h-9 w-full rounded-lg border border-slate-200 px-3 font-mono outline-none focus:border-navy" />
            </label>
            <label className="block space-y-1">
              <span className="font-bold text-slate-600">{T("支払期日")}</span>
              <input id="inv-due" type="date" value={due} onChange={(e) => setDue(e.target.value)} className="h-9 w-full rounded-lg border border-slate-200 px-3 outline-none focus:border-navy" />
            </label>
          </div>
          <fieldset className="space-y-1">
            <legend className="font-bold text-slate-600">{T("税率")}</legend>
            <div className="grid grid-cols-2 gap-2">
              {([10, 8] as const).map((r) => (
                <button key={r} type="button" onClick={() => setRate(r)} aria-pressed={rate === r}
                  className={cx("rounded-lg border px-3 py-2 text-left", rate === r ? "border-navy bg-slate-50" : "border-slate-200")}>
                  <span className="block font-bold text-navy">{r}%</span>
                  <span className="text-[10px] text-slate-400">{r === 10 ? T("標準税率") : T("軽減税率（飲食料品等）")}</span>
                </button>
              ))}
            </div>
          </fieldset>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">{T("適格請求書 記載事項プレビュー")}</p>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
              <dt className="text-slate-400">{T("登録番号")}</dt><dd className="font-mono">T3010001222222</dd>
              <dt className="text-slate-400">{T("税率ごとの対価")}</dt><dd className="font-mono tabular">{yen(gross)}（{rate}{T("%対象）")}</dd>
              <dt className="text-slate-400">{T("消費税額")}</dt><dd className="font-mono tabular">{yen(tax)}</dd>
              <dt className="text-slate-400">{T("税抜金額")}</dt><dd className="font-mono tabular">{yen(gross - tax)}</dd>
            </dl>
          </div>
        </div>
        <div className="flex gap-2 border-t border-slate-200 p-4">
          <button type="button" onClick={onClose} className="h-9 flex-1 rounded-lg border border-slate-200 text-xs text-slate-600">{T("キャンセル")}</button>
          <button type="submit" className="flex h-9 flex-1 items-center justify-center gap-1.5 rounded-lg bg-navy text-xs font-bold text-white hover:bg-navy-700"><Plus size={14} />{T("発行する")}</button>
        </div>
      </form>
    </div>
  );
}

/* ============================================================
 * PAGE
 * ============================================================ */

export default function DashboardPage() {
  const data = useDashboardData();
  const conn = { mode: data.mode, company: data.company, setCompany: data.setCompany, error: data.error, email: data.email, role: data.role };
  return (
    <AppShell title="ダッシュボード" sub={T("{a} ・ {b}", { a: data.company.name, b: T(data.company.fiscal) })} conn={conn}>
      <Dashboard data={data} />
    </AppShell>
  );
}

function Dashboard({ data }: { data: ReturnType<typeof useDashboardData> }) {
  const [invOpen, setInvOpen] = useState(false);
  const { mode, invoices, setInvoices, company } = data;
  const live = mode === "live";
  const { toast, canEdit } = useShell();

  const onPaid = async (no: string) => {
    if (!live) {
      setInvoices((p) => p.map((i) => (i.no === no ? { ...i, status: "paid" } : i)));
      toast(T("{a} を入金消込しました（デモ）", { a: no }));
      return;
    }
    try {
      const r = await api.payInvoice(no);
      setInvoices((p) => p.map((i) => (i.no === no ? toInvoice({ ...r, overdue: false }) : i)));
      toast(T("{a} を入金消込しました", { a: no }));
      data.reload();
    } catch (e) {
      toast(T("消込に失敗しました: {a}", { a: e instanceof Error ? e.message : e }));
    }
  };

  const onCreate = async (i: Invoice) => {
    setInvOpen(false);
    if (!live) {
      setInvoices((p) => [i, ...p]);
      toast(T("{a} を発行しました（デモ）", { a: i.no }));
      return;
    }
    try {
      const unit = i.amount - taxIn(i.amount, i.rate); // 税込 → 税抜
      const r = await api.createInvoice({ client: i.client, due: i.due, items: [{ name: "ご請求分", qty: 1, unit_price: unit, rate: i.rate }] });
      setInvoices((p) => [toInvoice({ ...r, overdue: false }), ...p]);
      toast(T("{a} を発行しました", { a: r.no }));
    } catch (e) {
      toast(T("発行に失敗しました: {a}", { a: e instanceof Error ? e.message : e }));
    }
  };

  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-6 lg:grid-cols-12">
        <KpiCards cashflow={data.cashflow} />
        <CashFlowChart cashflow={data.cashflow} />
        <QuickActions onInvoice={() => setInvOpen(true)} toast={toast} canEdit={canEdit} />
        <ConsumptionTax tax={data.tax} />
        <Compliance reg={company.reg} />
        <BankSync />
        <InvoiceTable invoices={invoices} onPaid={canEdit ? onPaid : undefined} live={live} />
      </div>
      <InvoiceDrawer open={invOpen} onClose={() => setInvOpen(false)} onCreate={onCreate} />
    </>
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
    <Card title="銀行連携" en="Bank Accounts" className="sm:col-span-6 lg:col-span-4" right={<Badge tone="ok">{T("全口座 接続済")}</Badge>}>
      <ul className="divide-y divide-slate-100">
        {MOCK.banks.map((b) => (
          <li key={b.name} className="flex items-center gap-3 py-2 first:pt-0">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-slate-100 text-xs font-bold text-navy">{b.name[0]}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-bold text-navy">{b.name}</p>
              <p className="font-mono text-[10px] text-slate-400">{b.acct} {T("・ 最終同期")} {b.synced}</p>
            </div>
            <Badge tone="ok">{T("連携中")}</Badge>
          </li>
        ))}
      </ul>
      <p className="mt-auto rounded-lg bg-slate-50 px-2.5 py-1.5 text-[11px] text-slate-500">{T("銀行API（参照系・電子決済等代行業）・ 15分ごとに自動取得")}</p>
    </Card>
  );
}
