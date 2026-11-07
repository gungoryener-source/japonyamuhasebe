"use client";

/** 経費精算 — 領収書アップロード（OCR）・手入力・電子帳簿保存法の検索・修正/削除 */
import { useEffect, useRef, useState } from "react";
import { Camera, History, Image as ImageIcon, LoaderCircle, Plus, Search, Trash2, Upload } from "lucide-react";
import { api, CATEGORIES, EXPENSE_CATEGORIES, openBlob, todayJST, type ApiAuditRow, type ApiEntry, type EntryDraft } from "../lib/api";
import { DEMO_ENTRIES } from "../lib/demo";
import { AppShell, useShell } from "../components/shell";
import { Badge, Btn, Card, creditRatio, cx, Empty, Field, inputCls, ReadOnlyNote, registrationOk, selectCls, Stat, yen } from "../components/ui";
import { useLoad } from "../components/useLoad";
import { T } from "../lib/i18n";
import { ROLE_LABEL, type Role } from "../lib/team";

type Filters = { date_from: string; date_to: string; q: string; amount_min: string; amount_max: string; kind: string };
const EMPTY_F: Filters = { date_from: "", date_to: "", q: "", amount_min: "", amount_max: "", kind: "" };
const blank = (): EntryDraft => ({ date: todayJST(), kind: "exp", store: "", amount: 0, category: "消耗品費", rate: 10, invoice_no: "" });

export default function ExpensesPage() {
  return (
    <AppShell title="経費精算" en="Expenses" sub="領収書の読み取り・登録・検索（電子帳簿保存法の検索要件に対応）">
      <Expenses />
    </AppShell>
  );
}

function Expenses() {
  const { mode, live, toast, canEdit } = useShell();
  const [f, setF] = useState<Filters>(EMPTY_F);
  const [applied, setApplied] = useState<Filters>(EMPTY_F);
  const load = () => api.entries({
    date_from: applied.date_from || undefined, date_to: applied.date_to || undefined, q: applied.q || undefined,
    amount_min: applied.amount_min ? Number(applied.amount_min) : undefined,
    amount_max: applied.amount_max ? Number(applied.amount_max) : undefined,
    kind: applied.kind || undefined, limit: 1000,
  }).then((r) => [...r].sort((a, b) => (b.d + b.id).localeCompare(a.d + a.id)));
  const { data: rows, setData: setRows, loading, reload } = useLoad<ApiEntry[]>(mode, load, DEMO_ENTRIES as unknown as ApiEntry[], [applied]);
  const [historyOf, setHistoryOf] = useState<ApiEntry | null>(null);

  const exp = rows.filter((r) => r.kind === "exp");
  const noReg = exp.filter((r) => r.rate && !r.invoice_no);
  const save = async (d: EntryDraft) => {
    if (!d.store.trim() || d.amount <= 0) { toast(T("取引先と金額を入力してください")); return false; }
    if (d.invoice_no && !/^T\d{13}$/.test(d.invoice_no)) { toast(T("登録番号は T + 13桁 です")); return false; }
    if (!live) {
      setRows((p) => [{ id: Date.now(), d: d.date, kind: d.kind, store: d.store, amount: d.amount, category: d.category, rate: d.rate, invoice_no: d.invoice_no, source: "WEB" }, ...p]);
      toast(T("登録しました（デモ）"));
      return true;
    }
    try {
      await api.createEntry(d);
      toast(T("登録しました: {a} {b}", { a: d.store, b: yen(d.amount) }));
      reload();
      return true;
    } catch (e) {
      toast(T("登録に失敗しました: {a}", { a: e instanceof Error ? e.message : e }));
      return false;
    }
  };

  const showImage = async (r: ApiEntry) => {
    if (!live) return toast(T("デモでは画像は表示されません"));
    try {
      openBlob(await api.entryImage(r.id));
    } catch {
      toast(T("画像が見つかりません（保存期間外、または保存先の設定前の画像です）"));
    }
  };

  const patch = async (r: ApiEntry, p: Partial<EntryDraft>) => {
    setRows((prev) => prev.map((x) => (x.id === r.id ? { ...x, ...(p.category ? { category: p.category } : {}), ...(p.rate !== undefined ? { rate: p.rate } : {}) } : x)));
    if (!live) return;
    try {
      await api.patchEntry(r.id, p);
    } catch (e) {
      toast(T("更新に失敗しました: {a}", { a: e instanceof Error ? e.message : e }));
      reload();
    }
  };

  const remove = async (r: ApiEntry) => {
    setRows((prev) => prev.filter((x) => x.id !== r.id));
    if (!live) return toast(T("削除しました（デモ）"));
    try {
      await api.deleteEntry(r.id);
      toast(T("削除しました: {a}", { a: r.store }));
    } catch (e) {
      toast(T("削除に失敗しました: {a}", { a: e instanceof Error ? e.message : e }));
      reload();
    }
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label={T("表示中の経費")} value={yen(exp.reduce((s, r) => s + r.amount, 0))} />
        <Stat label={T("件数")} value={T("{a} 件", { a: exp.length })} />
        <Stat label={T("登録番号なし")} value={T("{a} 件", { a: noReg.length })} tone={noReg.length ? "warn" : "ok"} />
        <Stat label={T("売上（表示中）")} value={yen(rows.filter((r) => r.kind === "inc").reduce((s, r) => s + r.amount, 0))} tone="ok" />
      </div>

      {canEdit ? (
        <div className="grid gap-3 lg:grid-cols-2">
          <ReceiptUpload onSave={save} />
          <ManualEntry onSave={save} />
        </div>
      ) : (
        <ReadOnlyNote />
      )}

      <Card title="取引一覧・検索" en="Search (電帳法: 日付・金額・取引先)">
        <form
          onSubmit={(e) => { e.preventDefault(); setApplied(f); }}
          className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7"
        >
          <input id="f-from" type="date" value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} className={inputCls} aria-label={T("開始日")} />
          <input id="f-to" type="date" value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} className={inputCls} aria-label={T("終了日")} />
          <input id="f-q" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} placeholder={T("取引先")} className={inputCls + " col-span-2 sm:col-span-1 lg:col-span-2"} />
          <input id="f-min" value={f.amount_min} onChange={(e) => setF({ ...f, amount_min: e.target.value.replace(/\D/g, "") })} inputMode="numeric" placeholder={T("金額 下限")} className={inputCls + " font-mono"} />
          <input id="f-max" value={f.amount_max} onChange={(e) => setF({ ...f, amount_max: e.target.value.replace(/\D/g, "") })} inputMode="numeric" placeholder={T("金額 上限")} className={inputCls + " font-mono"} />
          <div className="col-span-2 flex gap-2 sm:col-span-4 lg:col-span-1">
            <select id="f-kind" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })} className={selectCls}>
              <option value="">{T("すべて")}</option><option value="exp">{T("経費")}</option><option value="inc">{T("売上")}</option>
            </select>
            <Btn type="submit" kind="primary" className="h-9"><Search size={13} /></Btn>
          </div>
        </form>
        {!live && <p className="text-[11px] text-slate-400">{T("デモでは検索条件は適用されません。")}</p>}
        {loading && <p className="text-xs text-slate-400">{T("読み込み中…")}</p>}
        {rows.length === 0 ? (
          <Empty>{T("該当する取引はありません。")}</Empty>
        ) : (
          <div className="-mx-4 overflow-x-auto">
            <table className="w-full min-w-[820px] text-xs">
              <thead>
                <tr className="border-y border-slate-100 bg-slate-50 text-left text-[10px] uppercase tracking-wider text-slate-400">
                  <th className="px-4 py-2 font-medium">{T("日付")}</th>
                  <th className="px-2 py-2 font-medium">{T("取引先")}</th>
                  <th className="px-2 py-2 font-medium">{T("勘定科目")}</th>
                  <th className="px-2 py-2 font-medium">{T("税率")}</th>
                  <th className="px-2 py-2 text-right font-medium">{T("金額（税込）")}</th>
                  <th className="px-2 py-2 font-medium">{T("インボイス")}</th>
                  <th className="px-2 py-2 font-medium">{T("入力元")}</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70">
                    <td className="whitespace-nowrap px-4 py-1.5 font-mono text-slate-500 tabular">{r.d.replaceAll("-", "/")}</td>
                    <td className="max-w-[200px] truncate px-2 py-1.5 text-slate-700">{r.store}</td>
                    <td className="px-2 py-1.5">
                      <select value={r.category} onChange={(e) => patch(r, { category: e.target.value })} aria-label={T("勘定科目")} disabled={!canEdit}
                        className="rounded border border-transparent bg-transparent py-0.5 text-xs hover:border-slate-200">
                        {(r.kind === "inc" ? ["売上高"] : EXPENSE_CATEGORIES).map((c) => <option key={c}>{c}</option>)}
                      </select>
                    </td>
                    <td className="px-2 py-1.5">
                      <select value={r.rate} onChange={(e) => patch(r, { rate: Number(e.target.value) })} aria-label={T("税率")} disabled={!canEdit}
                        className={cx("rounded border border-transparent bg-transparent py-0.5 font-mono text-xs hover:border-slate-200", r.rate === 8 && "text-mint-700")}>
                        <option value={10}>10%</option><option value={8}>8%</option><option value={0}>{T("対象外")}</option>
                      </select>
                    </td>
                    <td className={cx("whitespace-nowrap px-2 py-1.5 text-right font-mono font-semibold tabular", r.kind === "inc" ? "text-mint-600" : "text-navy")}>
                      {r.kind === "inc" ? "+" : ""}{yen(r.amount)}
                    </td>
                    <td className="px-2 py-1.5">
                      {r.kind === "inc" || r.rate === 0 ? <span className="text-slate-300">—</span>
                        : r.invoice_no ? <Badge tone="ok">{T("適格")}</Badge>
                          : <Badge tone="warn">{T("番号なし・控除")}{creditRatio(r.d)}%</Badge>}
                    </td>
                    <td className="px-2 py-1.5 text-[11px] text-slate-400">
                      <span className="flex items-center gap-1.5">{r.source}
                        {r.image_path && <button onClick={() => showImage(r)} title={T("領収書の画像を表示")} aria-label={T("領収書の画像を表示")}
                          className="text-slate-400 hover:text-navy"><ImageIcon size={13} /></button>}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-1.5 text-right">
                      <span className="inline-flex items-center gap-2">
                        <button onClick={() => setHistoryOf(r)} className="text-slate-300 hover:text-navy" aria-label={T("履歴")} title={T("訂正・削除の履歴")}><History size={14} /></button>
                        {canEdit && <button onClick={() => remove(r)} className="text-slate-300 hover:text-rose-500" aria-label={T("削除")} title={T("削除")}><Trash2 size={14} /></button>}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {historyOf && <HistoryPanel entry={historyOf} onClose={() => setHistoryOf(null)} />}
    </div>
  );
}

/** T-065b: 訂正・削除の履歴（電子帳簿保存法）。誰が・いつ・何を変えたか。 */
const FIELD_LABEL: Record<string, string> = {
  d: "日付", store: "取引先", amount: "金額（税込）", category: "勘定科目", rate: "税率", invoice_no: "登録番号", kind: "区分",
};
const ACTION_LABEL: Record<ApiAuditRow["action"], string> = { create: "登録", update: "訂正", delete: "削除" };
const KIND_LABEL: Record<string, string> = { line: "LINE", whatsapp: "WhatsApp", bank: "銀行明細", web: "Web" };

function fmtValue(k: string, v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (k === "amount" && typeof v === "number") return yen(v);
  if (k === "rate") return v === 0 ? T("対象外") : `${v}%`;
  if (k === "kind") return v === "inc" ? T("売上") : T("経費");
  return String(v);
}

function actorText(r: ApiAuditRow): string {
  if (r.actor_kind !== "web") return KIND_LABEL[r.actor_kind] ?? r.actor ?? "—";
  const role = r.actor_role in ROLE_LABEL ? T(ROLE_LABEL[r.actor_role as Role]) : r.actor_role;
  if (r.actor_former) return T("{a}（退出したメンバー）", { a: role });
  const who = r.actor_is_me ? T("あなた") : r.actor_email;
  return who ? `${who}（${role}）` : role;
}

function HistoryPanel({ entry, onClose }: { entry: ApiEntry; onClose: () => void }) {
  const { live } = useShell();
  const [rows, setRows] = useState<ApiAuditRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!live) {
      setRows([{ id: 1, entity: "entry", entity_id: String(entry.id), action: "create", actor: entry.source, created_at: `${entry.d}T09:00:00+09:00`,
        before: null, after: null, changed: [], actor_kind: entry.source.toLowerCase(), actor_role: "", actor_email: null, actor_is_me: false, actor_former: false }]);
      return;
    }
    api.entryHistory(entry.id).then(setRows).catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, [entry, live]);

  return (
    <div className="fixed inset-0 z-[65] flex justify-end bg-slate-900/40" onMouseDown={onClose}>
      <div onMouseDown={(e) => e.stopPropagation()} className="flex h-full w-full max-w-lg flex-col bg-white shadow-2xl" role="dialog" aria-label={T("訂正・削除の履歴")}>
        <div className="flex h-14 items-center border-b border-slate-200 px-5">
          <h3 className="text-sm font-bold text-navy">{T("訂正・削除の履歴")} <span className="text-[10px] font-normal text-slate-400">History</span></h3>
          <button type="button" onClick={onClose} className="ml-auto text-xs text-slate-400 hover:text-navy">{T("閉じる")}</button>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto p-5 text-xs">
          <p className="text-slate-500">
            <span className="font-mono tabular">{entry.d.replaceAll("-", "/")}</span>　{entry.store}　<span className="font-mono font-semibold tabular text-navy">{yen(entry.amount)}</span>
          </p>
          {!live && <p className="text-[11px] text-slate-400">{T("デモでは登録の記録のみ表示されます。")}</p>}
          {err && <p className="rounded-lg bg-rose-50 px-3 py-2 text-rose-700">{T("履歴を読み込めませんでした: {a}", { a: err })}</p>}
          {!rows && !err && <p className="text-slate-400">{T("読み込み中…")}</p>}
          {rows && rows.length === 0 && <Empty>{T("この取引には記録された履歴がありません（履歴機能の導入前に登録された取引です）。")}</Empty>}
          <ol className="space-y-2">
            {rows?.map((h) => (
              <li key={h.id} className="rounded-lg border border-slate-100 p-3">
                <div className="flex items-center gap-2">
                  <Badge tone={h.action === "delete" ? "bad" : h.action === "update" ? "warn" : "ok"} icon={false}>{T(ACTION_LABEL[h.action])}</Badge>
                  <span className="font-mono text-[11px] text-slate-500 tabular">{h.created_at.slice(0, 16).replace("T", " ")}</span>
                  <span className="ml-auto truncate text-[11px] text-slate-500">{actorText(h)}</span>
                </div>
                {h.action === "update" && h.changed.filter((k) => FIELD_LABEL[k]).length > 0 && (
                  <table className="mt-2 w-full text-[11px]">
                    <tbody>
                      {h.changed.filter((k) => FIELD_LABEL[k]).map((k) => (
                        <tr key={k}>
                          <td className="w-24 py-0.5 text-slate-400">{T(FIELD_LABEL[k])}</td>
                          <td className="py-0.5 text-slate-500 line-through">{fmtValue(k, h.before?.[k])}</td>
                          <td className="px-1 text-slate-300">→</td>
                          <td className="py-0.5 font-semibold text-navy">{fmtValue(k, h.after?.[k])}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </li>
            ))}
          </ol>
          <p className="text-[10px] text-slate-400">{T("訂正・削除の記録は消去できません（電子帳簿保存法）。")}</p>
        </div>
      </div>
    </div>
  );
}

function DraftEditor({ d, onChange }: { d: EntryDraft; onChange: (d: EntryDraft) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <Field label={T("日付")}><input type="date" value={d.date} onChange={(e) => onChange({ ...d, date: e.target.value })} className={inputCls} /></Field>
      <Field label={T("取引先")} className="sm:col-span-2"><input value={d.store} onChange={(e) => onChange({ ...d, store: e.target.value })} className={inputCls} placeholder={T("店名・会社名")} /></Field>
      <Field label={T("金額（税込）")}><input value={d.amount || ""} onChange={(e) => onChange({ ...d, amount: Number(e.target.value.replace(/\D/g, "")) || 0 })} inputMode="numeric" className={inputCls + " text-right font-mono"} placeholder="1,100" /></Field>
      <Field label={T("区分")}>
        <select value={d.kind} onChange={(e) => { const kind = e.target.value as "inc" | "exp"; onChange({ ...d, kind, category: kind === "inc" ? "売上高" : (d.category === "売上高" ? "消耗品費" : d.category) }); }} className={selectCls}>
          <option value="exp">{T("経費")}</option><option value="inc">{T("売上")}</option>
        </select>
      </Field>
      <Field label={T("勘定科目")}>
        <select value={d.category} onChange={(e) => onChange({ ...d, category: e.target.value })} className={selectCls}>
          {(d.kind === "inc" ? ["売上高"] : CATEGORIES.filter((c) => c !== "売上高")).map((c) => <option key={c}>{c}</option>)}
        </select>
      </Field>
      <Field label={T("税率")}>
        <select value={d.rate} onChange={(e) => onChange({ ...d, rate: Number(e.target.value) })} className={selectCls}>
          <option value={10}>{T("10%（標準）")}</option><option value={8}>{T("8%（軽減）")}</option><option value={0}>{T("対象外")}</option>
        </select>
      </Field>
      <Field label={T("登録番号")} className="col-span-2">
        <input value={d.invoice_no} onChange={(e) => onChange({ ...d, invoice_no: e.target.value.toUpperCase().replace(/[^T\d]/g, "") })} className={inputCls + " font-mono"} placeholder={T("T + 13桁（なければ空欄）")} />
        {d.invoice_no && !registrationOk(d.invoice_no) && <span className="text-[10px] text-amber-600">{T("形式またはチェックデジットを確認してください")}</span>}
      </Field>
    </div>
  );
}

function ManualEntry({ onSave }: { onSave: (d: EntryDraft) => Promise<boolean> }) {
  const [d, setD] = useState<EntryDraft>(blank());
  return (
    <Card title="手入力" en="Manual Entry">
      <DraftEditor d={d} onChange={setD} />
      <div className="flex justify-end">
        <Btn kind="primary" onClick={async () => { if (await onSave(d)) setD(blank()); }}><Plus size={14} />{T("登録する")}</Btn>
      </div>
    </Card>
  );
}

function ReceiptUpload({ onSave }: { onSave: (d: EntryDraft) => Promise<boolean> }) {
  const { live, toast } = useShell();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<EntryDraft[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const onFile = async (file?: File | null) => {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) return toast(T("10MB以下の画像を選んでください"));
    setPreview((p) => { if (p) URL.revokeObjectURL(p); return URL.createObjectURL(file); });
    setDrafts([]); setMsg(null); setBusy(true);
    try {
      if (!live) {
        await new Promise((r) => setTimeout(r, 900));
        setDrafts([
          { date: todayJST(), kind: "exp", store: "ファミリーマート 新宿西口店", amount: 550, category: "消耗品費", rate: 10, invoice_no: "T4013301012345" },
          { date: todayJST(), kind: "exp", store: "ファミリーマート 新宿西口店", amount: 300, category: "消耗品費", rate: 8, invoice_no: "T4013301012345" },
        ]);
        setMsg(T("デモ: 税率ごとに2件に分けて読み取りました"));
        return;
      }
      const r = await api.ocr(file);
      if (r.ok && r.entries.length) {
        setDrafts(r.entries.map((e) => ({ ...e, image_path: r.image_path ?? "" })));   // T-034: 画像を記録に紐付け
        setMsg(r.entries.length > 1 ? T("税率ごとに{a}件に分けて読み取りました。内容を確認して登録してください", { a: r.entries.length }) : T("読み取りました。内容を確認して登録してください"));
      } else {
        const p = r.partial ?? {};
        setDrafts([{ ...blank(), date: p.date ?? todayJST(), store: p.store ?? "", invoice_no: p.invoice_no ?? "", image_path: r.image_path ?? "" }]);
        setMsg(T("金額を読み取れませんでした（{a}）。読み取れた項目を入れたので、金額を入力してください", { a: r.error ?? T("不明") }));
      }
    } catch (e) {
      setMsg(T("読み取りに失敗しました: {a}", { a: e instanceof Error ? e.message : e }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="領収書を読み取る" en="Receipt OCR">
      <label
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); onFile(e.dataTransfer.files?.[0]); }}
        className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-slate-300 p-3 hover:border-mint hover:bg-mint-50/40"
      >
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt={T("領収書")} className="h-20 w-16 rounded object-cover ring-1 ring-slate-200" />
        ) : (
          <span className="grid h-20 w-16 place-items-center rounded bg-slate-50 text-slate-400"><Camera size={22} /></span>
        )}
        <span className="text-xs text-slate-500">
          {busy ? <span className="flex items-center gap-1.5 text-navy"><LoaderCircle size={14} className="animate-spin" />{T("読み取り中…（数十秒かかることがあります）")}</span>
            : <><span className="flex items-center gap-1 font-bold text-navy"><Upload size={13} />{T("写真を選ぶ・ドロップ")}</span>{T("JPEG / PNG・10MBまで。日付・金額・税率・登録番号を自動入力します")}</>}
        </span>
        <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }} />
      </label>
      {msg && <p className={cx("rounded-lg px-3 py-2 text-[11px]", drafts.some((d) => d.amount) ? "bg-mint-50 text-mint-700" : "bg-amber-50 text-amber-800")}>{msg}</p>}
      {drafts.map((d, i) => (
        <div key={i} className="space-y-2 rounded-lg border border-slate-100 p-3">
          <DraftEditor d={d} onChange={(nd) => setDrafts((p) => p.map((x, j) => (j === i ? nd : x)))} />
          <div className="flex justify-end">
            <Btn kind="mint" onClick={async () => { if (await onSave(d)) setDrafts((p) => p.filter((_, j) => j !== i)); }}>{T("この内容で登録")}</Btn>
          </div>
        </div>
      ))}
    </Card>
  );
}
