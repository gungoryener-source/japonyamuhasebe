"use client";

/** 請求書管理 — 適格請求書の一覧・作成（複数明細・税率別集計）・入金消込・PDF */
import { useMemo, useState } from "react";
import { FileDown, Plus, Search, Trash2 } from "lucide-react";
import { api, openBlob, todayJST, type ApiInvoice } from "../lib/api";
import { MOCK } from "../lib/demo";
import { AppShell, useShell } from "../components/shell";
import { Badge, Btn, Card, Empty, Field, inputCls, selectCls, Stat, cx, yen } from "../components/ui";
import { useLoad } from "../components/useLoad";
import { T } from "../lib/i18n";

type Row = ApiInvoice & { items?: { name: string; qty: number; unit_price: number; rate: number; amount: number }[] };
type Line = { name: string; qty: string; unit_price: string; rate: 10 | 8 };
type Filter = "all" | "unpaid" | "overdue" | "paid";

const DEMO: Row[] = MOCK.invoices.map((i) => {
  const sub = Math.round(i.amount / (1 + i.rate / 100));
  return {
    no: i.no, client: i.client, issued: i.issued, due: i.due, total: i.amount,
    subtotal10: i.rate === 10 ? sub : 0, subtotal8: i.rate === 8 ? sub : 0,
    tax10: i.rate === 10 ? i.amount - sub : 0, tax8: i.rate === 8 ? i.amount - sub : 0,
    status: i.status === "paid" ? "paid" : "unpaid", overdue: i.status === "overdue",
  };
});

const statusOf = (r: Row) => (r.status === "paid" ? "paid" : r.overdue ? "overdue" : "unpaid");
const STATUS = { paid: { ja: "支払済", tone: "ok" }, unpaid: { ja: "未入金", tone: "warn" }, overdue: { ja: "期日超過", tone: "bad" } } as const;

export default function InvoicesPage() {
  return (
    <AppShell title="請求書管理" en="Invoices" sub="適格請求書（インボイス）の発行・入金管理">
      <Invoices />
    </AppShell>
  );
}

function Invoices() {
  const { mode, live, toast, canEdit } = useShell();
  const { data: rows, setData: setRows, loading, reload } = useLoad<Row[]>(mode, api.invoices, DEMO);
  const [filter, setFilter] = useState<Filter>("all");
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);

  const shown = useMemo(
    () => rows.filter((r) => (filter === "all" || statusOf(r) === filter) && (!q || (r.client + r.no).includes(q))),
    [rows, filter, q],
  );
  const open = rows.filter((r) => r.status !== "paid");
  const month = todayJST().slice(0, 7);
  const stats = {
    receivable: open.reduce((s, r) => s + r.total, 0),
    overdue: rows.filter((r) => statusOf(r) === "overdue").length,
    issuedThisMonth: rows.filter((r) => r.issued.startsWith(month)).reduce((s, r) => s + r.total, 0),
    paid: rows.filter((r) => r.status === "paid").length,
  };

  const pay = async (no: string) => {
    if (!live) {
      setRows((p) => p.map((r) => (r.no === no ? { ...r, status: "paid", overdue: false } : r)));
      return toast(T("{a} を入金消込しました（デモ）", { a: no }));
    }
    try {
      await api.payInvoice(no);
      toast(T("{a} を入金消込しました。売上として帳簿に記録しました", { a: no }));
      reload();
    } catch (e) {
      toast(T("消込に失敗しました: {a}", { a: e instanceof Error ? e.message : e }));
    }
  };

  const pdf = async (no: string) => {
    if (!live) return toast(T("PDFは帳簿に接続すると表示できます"));
    try {
      openBlob(await api.pdf(no));
    } catch {
      toast(T("PDFを取得できませんでした"));
    }
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label={T("未回収合計")} value={yen(stats.receivable)} tone="warn" />
        <Stat label={T("期日超過")} value={T("{a} 件", { a: stats.overdue })} tone={stats.overdue ? "bad" : undefined} />
        <Stat label={T("今月の発行額")} value={yen(stats.issuedThisMonth)} />
        <Stat label={T("支払済")} value={T("{a} 件", { a: stats.paid })} tone="ok" />
      </div>

      <Card
        title={T("請求書一覧")}
        en="All Invoices"
        right={canEdit ? <Btn kind="primary" onClick={() => setCreating(true)}><Plus size={14} />{T("請求書作成")}</Btn> : <Badge tone="muted" icon={false}>{T("閲覧専用")}</Badge>}
      >
        <div className="flex flex-wrap items-center gap-2">
          {(["all", "unpaid", "overdue", "paid"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)} aria-pressed={filter === f}
              className={cx("rounded-full px-2.5 py-0.5 text-[11px] ring-1 ring-inset", filter === f ? "bg-navy text-white ring-navy" : "text-slate-500 ring-slate-200 hover:bg-slate-50")}>
              {f === "all" ? T("{a} ({b})", { a: T("すべて"), b: rows.length }) : T(STATUS[f].ja)}
            </button>
          ))}
          <div className="relative ml-auto w-full sm:w-64">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input id="inv-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={T("取引先・請求書番号で検索")} className={inputCls + " pl-7"} />
          </div>
        </div>
        {loading && <p className="text-xs text-slate-400">{T("読み込み中…")}</p>}
        {shown.length === 0 ? (
          <Empty>{T("該当する請求書はありません。「請求書作成」から発行できます。")}</Empty>
        ) : (
          <div className="-mx-4 overflow-x-auto">
            <table className="w-full min-w-[760px] text-xs">
              <thead>
                <tr className="border-y border-slate-100 bg-slate-50 text-left text-[10px] uppercase tracking-wider text-slate-400">
                  <th className="px-4 py-2 font-medium">{T("請求書番号")}</th>
                  <th className="px-2 py-2 font-medium">{T("取引先")}</th>
                  <th className="px-2 py-2 font-medium">{T("発行日")}</th>
                  <th className="px-2 py-2 font-medium">{T("支払期日")}</th>
                  <th className="px-2 py-2 text-right font-medium">{T("10%対象")}</th>
                  <th className="px-2 py-2 text-right font-medium">{T("8%対象")}</th>
                  <th className="px-2 py-2 text-right font-medium">{T("合計（税込）")}</th>
                  <th className="px-2 py-2 font-medium">{T("状態")}</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {shown.map((r) => {
                  const st = statusOf(r);
                  return (
                    <tr key={r.no} className="hover:bg-slate-50/70">
                      <td className="whitespace-nowrap px-4 py-2 font-mono">
                        <button onClick={() => pdf(r.no)} className="flex items-center gap-1 text-navy hover:underline" title={T("PDFを開く")}>
                          <FileDown size={12} />{r.no}
                        </button>
                      </td>
                      <td className="max-w-[220px] truncate px-2 py-2 text-slate-700">{r.client}</td>
                      <td className="whitespace-nowrap px-2 py-2 font-mono text-slate-500 tabular">{r.issued.replaceAll("-", "/")}</td>
                      <td className={cx("whitespace-nowrap px-2 py-2 font-mono tabular", st === "overdue" ? "font-bold text-rose-600" : "text-slate-500")}>{r.due.replaceAll("-", "/")}</td>
                      <td className="whitespace-nowrap px-2 py-2 text-right font-mono text-slate-500 tabular">{r.subtotal10 ? yen(r.subtotal10 + r.tax10) : "—"}</td>
                      <td className="whitespace-nowrap px-2 py-2 text-right font-mono text-slate-500 tabular">{r.subtotal8 ? yen(r.subtotal8 + r.tax8) : "—"}</td>
                      <td className="whitespace-nowrap px-2 py-2 text-right font-mono font-semibold text-navy tabular">{yen(r.total)}</td>
                      <td className="px-2 py-2"><Badge tone={STATUS[st].tone}>{T(STATUS[st].ja)}</Badge></td>
                      <td className="whitespace-nowrap px-4 py-2 text-right">
                        {r.status !== "paid" && canEdit ? <Btn onClick={() => pay(r.no)}>{T("入金消込")}</Btn> : <span className="text-[11px] text-slate-300">—</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {creating && (
        <CreateInvoice
          onClose={() => setCreating(false)}
          onCreated={(r) => { setRows((p) => [r, ...p]); setCreating(false); toast(T("{a} を発行しました", { a: r.no })); if (live) reload(); }}
        />
      )}
    </div>
  );
}

function CreateInvoice({ onClose, onCreated }: { onClose: () => void; onCreated: (r: Row) => void }) {
  const { live, company, toast } = useShell();
  const today = todayJST();
  const endOfNextMonth = (() => {
    const d = new Date(today + "T00:00:00");
    return new Date(d.getFullYear(), d.getMonth() + 2, 0).toLocaleDateString("sv-SE");
  })();
  const [client, setClient] = useState("");
  const [issued, setIssued] = useState(today);
  const [due, setDue] = useState(endOfNextMonth);   // 月末締め翌月末払い
  const [lines, setLines] = useState<Line[]>([{ name: "", qty: "1", unit_price: "", rate: 10 }]);
  const [busy, setBusy] = useState(false);

  const items = lines
    .map((l) => ({ name: l.name.trim(), qty: Number(l.qty) || 0, unit_price: Number(l.unit_price.replace(/,/g, "")) || 0, rate: l.rate }))
    .filter((l) => l.name && l.qty > 0);
  const sub10 = items.filter((i) => i.rate === 10).reduce((s, i) => s + i.qty * i.unit_price, 0);
  const sub8 = items.filter((i) => i.rate === 8).reduce((s, i) => s + i.qty * i.unit_price, 0);
  const tax10 = Math.floor(sub10 * 0.1), tax8 = Math.floor(sub8 * 0.08);   // 税率ごとに1回端数処理
  const total = sub10 + sub8 + tax10 + tax8;
  const set = (i: number, patch: Partial<Line>) => setLines((p) => p.map((l, j) => (j === i ? { ...l, ...patch } : l)));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!client.trim() || !items.length) return toast(T("取引先と明細を入力してください"));
    if (due < issued) return toast(T("支払期日は発行日以降にしてください"));
    setBusy(true);
    try {
      if (live) {
        onCreated(await api.createInvoiceFull({ client: client.trim(), issued, due, items }));
      } else {
        onCreated({ no: `INV-DEMO-${Date.now().toString().slice(-4)}`, client, issued, due, total, subtotal10: sub10, subtotal8: sub8, tax10, tax8, status: "unpaid", overdue: false });
      }
    } catch (err) {
      toast(T("発行に失敗しました: {a}", { a: err instanceof Error ? err.message : err }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[65] flex justify-end bg-slate-900/40" onMouseDown={onClose}>
      <form onSubmit={submit} onMouseDown={(e) => e.stopPropagation()} className="flex h-full w-full max-w-2xl flex-col bg-white shadow-2xl" aria-label={T("請求書作成")}>
        <div className="flex h-14 items-center border-b border-slate-200 px-5">
          <h3 className="text-sm font-bold text-navy">{T("請求書作成")} <span className="text-[10px] font-normal text-slate-400">Qualified Invoice</span></h3>
          <button type="button" onClick={onClose} className="ml-auto text-xs text-slate-400 hover:text-navy">{T("閉じる")}</button>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label={T("取引先（交付先）")} className="sm:col-span-3">
              <input id="ci-client" value={client} onChange={(e) => setClient(e.target.value)} placeholder={T("株式会社〇〇 御中")} className={inputCls} required />
            </Field>
            <Field label={T("発行日")}><input id="ci-issued" type="date" value={issued} onChange={(e) => setIssued(e.target.value)} className={inputCls} /></Field>
            <Field label={T("支払期日")}><input id="ci-due" type="date" value={due} onChange={(e) => setDue(e.target.value)} className={inputCls} /></Field>
          </div>

          <div>
            <p className="mb-1 text-xs font-bold text-slate-600">{T("明細（税抜単価）")}</p>
            <div className="space-y-2">
              {lines.map((l, i) => (
                <div key={i} className="grid grid-cols-12 gap-2">
                  <input id={`ci-name-${i}`} value={l.name} onChange={(e) => set(i, { name: e.target.value })} placeholder={T("品目")} className={inputCls + " col-span-12 sm:col-span-5"} />
                  <input id={`ci-qty-${i}`} value={l.qty} onChange={(e) => set(i, { qty: e.target.value.replace(/\D/g, "") })} inputMode="numeric" placeholder={T("数量")} className={inputCls + " col-span-3 sm:col-span-2 text-right font-mono"} />
                  <input id={`ci-price-${i}`} value={l.unit_price} onChange={(e) => set(i, { unit_price: e.target.value.replace(/[^\d,]/g, "") })} inputMode="numeric" placeholder={T("単価")} className={inputCls + " col-span-4 sm:col-span-2 text-right font-mono"} />
                  <select id={`ci-rate-${i}`} value={l.rate} onChange={(e) => set(i, { rate: Number(e.target.value) as 10 | 8 })} className={selectCls + " col-span-3 sm:col-span-2"}>
                    <option value={10}>10%</option>
                    <option value={8}>{T("8%（軽減）")}</option>
                  </select>
                  <button type="button" onClick={() => setLines((p) => (p.length > 1 ? p.filter((_, j) => j !== i) : p))}
                    className="col-span-2 grid place-items-center rounded-lg text-slate-300 hover:text-rose-500 sm:col-span-1" aria-label={T("明細を削除")}>
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
            <button type="button" onClick={() => setLines((p) => [...p, { name: "", qty: "1", unit_price: "", rate: 10 }])}
              className="mt-2 flex items-center gap-1 text-[11px] font-bold text-navy hover:underline"><Plus size={12} />{T("明細を追加")}</button>
          </div>

          <div className="rounded-lg bg-slate-50 p-3 text-xs">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">{T("適格請求書 記載事項")}</p>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
              <dt className="text-slate-400">{T("発行者")}</dt><dd>{company.name}{T("（登録番号")} <span className="font-mono">{company.reg}</span>）</dd>
              <dt className="text-slate-400">{T("10%対象")}</dt><dd className="font-mono tabular">{yen(sub10)}{T("（消費税")} {yen(tax10)}）</dd>
              <dt className="text-slate-400">{T("8%対象")}</dt><dd className="font-mono tabular">{yen(sub8)}{T("（消費税")} {yen(tax8)}）</dd>
              <dt className="font-bold text-navy">{T("ご請求金額")}</dt><dd className="font-mono text-sm font-bold text-navy tabular">{yen(total)}</dd>
            </dl>
            {!/^T\d{13}$/.test(company.reg) && (
              <p className="mt-2 text-[11px] text-amber-700">{T("登録番号が未設定です。「設定」で登録すると請求書に記載されます。")}</p>
            )}
          </div>
        </div>
        <div className="flex gap-2 border-t border-slate-200 p-4">
          <Btn onClick={onClose} className="h-9 flex-1">{T("キャンセル")}</Btn>
          <Btn type="submit" kind="primary" disabled={busy || !items.length} className="h-9 flex-1"><Plus size={14} />{busy ? T("発行中…") : T("発行する")}</Btn>
        </div>
      </form>
    </div>
  );
}
