"use client";

/** T-060: 仕切書（買取伝票）の確認・承認。LINE で送られた伝票を画像と並べて確認し、承認で売上に記録。 */
import { useEffect, useRef, useState } from "react";
import { CircleCheck, FileText, History, FileUp, LoaderCircle, Plus, Trash2, TriangleAlert, X } from "lucide-react";
import { api, ApiError, openBlob, type ApiAuditRow, type ApiSlip, type ApiSlipList, type SlipLine } from "../lib/api";
import { AppShell, useShell } from "../components/shell";
import HistoryDrawer from "../components/HistoryDrawer";
import { Badge, Btn, Card, Empty, Field, inputCls, ReadOnlyNote, selectCls, Stat, yen } from "../components/ui";
import { useLoad } from "../components/useLoad";
import { T } from "../lib/i18n";

type Status = "pending" | "approved" | "rejected";

const DEMO: ApiSlipList = {
  ai_enabled: true,
  counts: { pending: 2, approved: 1, rejected: 0 },
  slips: [
    { id: 3, status: "pending", kind: "inc", d: "2026-06-02", issuer: "株式会社 三通", registration_no: "", total: 37705,
      lines: [{ item: "ステンレス", qty: 45, unit_price: 196, amount: 8820 }, { item: "鉄A", qty: 530, unit_price: 545, amount: 28885 }],
      image_path: "", source: "LINE", reader: "ai", entry_id: null, note: "", duplicate_of: null, created_at: "",
      issues: ["2行目: 数量×単価（288,850.0）と金額（28,885）が一致しません"] },
    { id: 2, status: "pending", kind: "inc", d: "2026-05-14", issuer: "(株)丸野商事", registration_no: "", total: 50820,
      lines: [{ item: "スクラップ", qty: 1210, unit_price: 42, amount: 50820 }],
      image_path: "", source: "LINE", reader: "ai", entry_id: null, note: "", duplicate_of: null, created_at: "", issues: [] },
    { id: 1, status: "approved", kind: "inc", d: "2026-04-28", issuer: "株式会社ECO瀬戸", registration_no: "T4180001153800", total: 118250,
      lines: [{ item: "鉄", qty: 450, unit_price: 50, amount: 22500 }, { item: "アルミ", qty: 70, unit_price: 455, amount: 31850 },
              { item: "工雑A", qty: 210, unit_price: 250, amount: 52500 }, { item: "給湯器", qty: 30, unit_price: 380, amount: 11400 }],
      image_path: "", source: "LINE", reader: "ai", entry_id: 10, note: "", duplicate_of: null, created_at: "", issues: [] },
  ],
};

const STATUS_LABEL: Record<Status, string> = { pending: "確認待ち", approved: "承認済み", rejected: "却下済み" };

/** サーバーと同じ検証（数量×単価=金額 ±1円、明細合計=伝票合計）。編集中に即時表示する。 */
function checkSlip(s: ApiSlip): string[] {
  const out: string[] = [];
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s.d)) out.push(T("日付がありません"));
  if (!s.issuer.trim()) out.push(T("発行元がありません"));
  if (!s.lines.length) out.push(T("明細がありません"));
  s.lines.forEach((l, i) => {
    if (l.amount == null) out.push(T("{a}行目: 金額がありません", { a: i + 1 }));
    else if (l.qty != null && l.unit_price != null && Math.abs(l.qty * l.unit_price - l.amount) > 1)
      out.push(T("{a}行目: 数量×単価と金額が一致しません", { a: i + 1 }));
  });
  const sum = s.lines.reduce((a, l) => a + (l.amount ?? 0), 0);
  if (s.lines.length && sum !== s.total) out.push(T("明細の合計（{a}）と伝票合計（{b}）が一致しません", { a: yen(sum), b: yen(s.total) }));
  if (s.registration_no && !/^T\d{13}$/.test(s.registration_no)) out.push(T("登録番号は T + 13桁 です"));
  return out;
}

const num = (v: string): number | null => {
  const n = Number(v.replace(/[,¥\s]/g, ""));
  return v.trim() === "" || Number.isNaN(n) ? null : n;
};

export default function SlipsPage() {
  const { mode, live, toast, canEdit } = useShell();
  const [status, setStatus] = useState<Status | "">("pending");
  const { data, setData, loading, reload } = useLoad(mode, () => api.slips(status), DEMO, [status]);
  const [selId, setSelId] = useState<number | null>(null);
  const year = new Date().getFullYear();
  const [from, setFrom] = useState(`${year}-01-01`);
  const [to, setTo] = useState(`${year}-12-31`);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const rows = live ? data.slips : data.slips.filter((s) => !status || s.status === status);
  const sel = rows.find((s) => s.id === selId) ?? rows[0] ?? null;

  const replace = (s: ApiSlip) =>
    setData((d) => ({ ...d, slips: d.slips.map((x) => (x.id === s.id ? { ...s, duplicate_of: x.duplicate_of } : x)) }));

  const upload = async (f: File | undefined) => {
    if (!f) return;
    if (!live) return toast(T("デモでは表示のみです"));
    if (f.size > 10 * 1024 * 1024) return toast(T("10MB以下の画像を選んでください"));
    setUploading(true);
    try {
      const s = await api.slipUpload(f);
      toast(s.reader === "ai" ? T("読み取りました。内容を確認して承認してください") : T("受け付けました。金額を入力してください"));
      setStatus("pending");
      await reload();
      setSelId(s.id);
    } catch (e) {
      toast(T("失敗しました: {a}", { a: e instanceof Error ? e.message : String(e) }));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const pdf = async () => {
    if (!live) return toast(T("PDFは帳簿に接続すると表示できます"));
    try {
      openBlob(await api.slipsPdf(from, to, "approved"));
    } catch (e) {
      toast(T("PDFを取得できませんでした") + `: ${e instanceof ApiError ? e.message : e}`);
    }
  };

  const approvedTotal = data.slips.filter((s) => s.status === "approved").reduce((a, s) => a + s.total, 0);

  return (
    <AppShell title="仕切書の確認" en="Scrap Slips"
      sub="LINE で送られた仕切書（買取伝票）を確認・修正し、承認すると売上として記録します"
      actions={canEdit ? (
        <>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => upload(e.target.files?.[0])} />
          <Btn kind="primary" onClick={() => fileRef.current?.click()} disabled={uploading}>
            {uploading ? <LoaderCircle size={14} className="animate-spin" /> : <FileUp size={14} />}{T("仕切書を追加")}
          </Btn>
        </>
      ) : undefined}>
      {!canEdit && <ReadOnlyNote />}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label={T("確認待ち")} value={`${data.counts.pending}${T("件")}`} tone={data.counts.pending ? "warn" : undefined} />
        <Stat label={T("承認済み")} value={`${data.counts.approved}${T("件")}`} tone="ok" />
        <Stat label={T("承認済みの売上")} value={yen(approvedTotal)} />
        <Stat label={T("読み取り")} value={data.ai_enabled ? T("AI（手書き対応）") : T("手入力")} />
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card title="伝票一覧" en="Slips" className="lg:col-span-4"
          right={<div className="flex gap-1 text-[11px]">
            {(["pending", "approved", "rejected", ""] as const).map((st) => (
              <button key={st || "all"} onClick={() => { setStatus(st); setSelId(null); }}
                className={"rounded-md px-2 py-1 font-bold " + (status === st ? "bg-navy text-white" : "text-slate-500 hover:bg-slate-100")}>
                {st ? T(STATUS_LABEL[st]) : T("すべて")}
              </button>))}
          </div>}>
          {loading ? <p className="flex items-center gap-2 text-xs text-slate-400"><LoaderCircle size={14} className="animate-spin" />{T("読み込み中…")}</p>
            : rows.length === 0 ? <Empty>{T("伝票はありません。LINE で「仕切書」と送ってから写真を送るか、「仕切書を追加」から画像をアップロードしてください。")}</Empty>
            : <ul className="flex flex-col divide-y divide-slate-100">
                {rows.map((s) => (
                  <li key={s.id}>
                    <button onClick={() => setSelId(s.id)}
                      className={"flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs " + (sel?.id === s.id ? "bg-mint/10" : "hover:bg-slate-50")}>
                      <span className="w-20 shrink-0 tabular-nums text-slate-500">{s.d || "—"}</span>
                      <span className="min-w-0 flex-1 truncate font-bold text-navy">{s.issuer || T("発行元未読取")}</span>
                      <span className="tabular-nums">{yen(s.total)}</span>
                      {s.status === "pending" && (s.issues.length || s.duplicate_of)
                        ? <TriangleAlert size={14} className="shrink-0 text-amber-500" />
                        : s.status === "approved" ? <CircleCheck size={14} className="shrink-0 text-mint" /> : <span className="w-[14px]" />}
                    </button>
                  </li>))}
              </ul>}
          <div className="mt-2 flex flex-wrap items-end gap-2 border-t border-slate-100 pt-3 text-xs">
            <Field label={T("開始日")}><input type="date" className={inputCls} value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
            <Field label={T("終了日")}><input type="date" className={inputCls} value={to} onChange={(e) => setTo(e.target.value)} /></Field>
            <Btn onClick={pdf}><FileText size={13} />{T("仕切書一覧PDF")}</Btn>
          </div>
        </Card>

        <div className="lg:col-span-8">
          {sel ? <SlipEditor key={sel.id} slip={sel} live={live} canEdit={canEdit} toast={toast} onChange={replace} onDone={reload} />
            : <Card title="伝票の確認" en="Review"><Empty>{T("左の一覧から伝票を選んでください")}</Empty></Card>}
        </div>
      </div>
    </AppShell>
  );
}

const SLIP_FIELDS: Record<string, string> = { d: "日付", issuer: "発行元", registration_no: "登録番号", kind: "区分", total: "合計", status: "状態", note: "備考" };
function fmtSlip(k: string, v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (k === "total" && typeof v === "number") return yen(v);
  if (k === "kind") return v === "inc" ? T("売上") : T("仕入");
  if (k === "status") return T(STATUS_LABEL[v as Status] ?? String(v));
  return String(v);
}

function SlipEditor({ slip, live, canEdit, toast, onChange, onDone }: {
  slip: ApiSlip; live: boolean; canEdit: boolean; toast: (m: string) => void;
  onChange: (s: ApiSlip) => void; onDone: () => Promise<void>;
}) {
  const [s, setS] = useState<ApiSlip>(slip);
  const [img, setImg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const editable = canEdit && s.status === "pending";
  const problems = checkSlip(s);

  useEffect(() => {
    if (!live || !slip.image_path) return;
    let url: string | null = null;
    api.slipImage(slip.id).then((b) => { url = URL.createObjectURL(b); setImg(url); }).catch(() => setImg(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [live, slip.id, slip.image_path]);

  const setLine = (i: number, patch: Partial<SlipLine>) =>
    setS((x) => ({ ...x, lines: x.lines.map((l, j) => (j === i ? { ...l, ...patch } : l)) }));
  const recalc = (i: number) =>
    setS((x) => ({ ...x, lines: x.lines.map((l, j) => (j === i && l.qty != null && l.unit_price != null
      ? { ...l, amount: Math.floor(l.qty * l.unit_price + 0.5) } : l)) }));
  const sumLines = () => setS((x) => ({ ...x, total: x.lines.reduce((a, l) => a + (l.amount ?? 0), 0) }));

  const save = async (): Promise<ApiSlip | null> => {
    if (!live) { toast(T("保存しました（デモ）")); onChange(s); return s; }
    try {
      const r = await api.slipPatch(s.id, { d: s.d, issuer: s.issuer, registration_no: s.registration_no, kind: s.kind, total: s.total, lines: s.lines });
      setS(r); onChange(r); return r;
    } catch (e) {
      toast(T("保存に失敗しました: {e}", { e: e instanceof Error ? e.message : String(e) })); return null;
    }
  };

  const approve = async () => {
    if (problems.length) return toast(problems[0]);
    setBusy(true);
    try {
      if (!(await save())) return;
      if (live) {
        const r = await api.slipApprove(s.id);
        setS(r); onChange(r);
      } else { setS({ ...s, status: "approved" }); }
      toast(T("承認しました。{a} を売上として記録しました", { a: yen(s.total) }));
      await onDone();
    } catch (e) {
      toast(T("失敗しました: {a}", { a: e instanceof Error ? e.message : String(e) }));
    } finally { setBusy(false); }
  };

  const reject = async () => {
    setBusy(true);
    try {
      if (live) { const r = await api.slipReject(s.id); setS(r); onChange(r); } else setS({ ...s, status: "rejected" });
      toast(T("却下しました"));
      await onDone();
    } catch (e) {
      toast(T("失敗しました: {a}", { a: e instanceof Error ? e.message : String(e) }));
    } finally { setBusy(false); }
  };

  return (
    <Card title="伝票の確認" en="Review"
      right={<div className="flex items-center gap-2">
        <Badge tone={s.status === "approved" ? "ok" : s.status === "rejected" ? "muted" : "warn"}>{T(STATUS_LABEL[s.status])}</Badge>
        <Badge tone="info" icon={false}>{s.reader === "ai" ? T("AI読取") : T("手入力")}</Badge>
        <button type="button" onClick={() => setShowHistory(true)} className="text-slate-300 hover:text-navy" title={T("履歴")} aria-label={T("履歴")}><History size={14} /></button>
      </div>}>
      {showHistory && <HistoryDrawer onClose={() => setShowHistory(false)} load={() => api.slipHistory(s.id)}
        demo={[{ id: 1, entity: "slip", entity_id: String(s.id), action: "create", actor: "LINE", created_at: `${s.d || "2026-01-01"}T09:00:00+09:00`, before: null, after: null,
          changed: [], actor_kind: "line", actor_role: "", actor_email: null, actor_is_me: false, actor_former: false }]}
        fieldLabels={SLIP_FIELDS} fmt={fmtSlip} emptyText={T("この伝票には記録された履歴がありません。")}
        subtitle={<><span className="font-mono tabular">{s.d.replaceAll("-", "/")}</span>　{s.issuer}　<span className="font-mono font-semibold tabular text-navy">{yen(s.total)}</span></>} />}
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="min-w-0 rounded-lg border border-slate-200 bg-slate-50">
          {img ? <a href={img} target="_blank" rel="noreferrer"><img src={img} alt={T("仕切書の画像")} className="max-h-[560px] w-full object-contain" /></a>
            : <p className="p-6 text-center text-xs text-slate-400">{live ? T("画像はありません") : T("デモでは画像は表示されません")}</p>}
        </div>

        <div className="flex min-w-0 flex-col gap-3 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <Field label={T("日付")}><input type="date" disabled={!editable} className={inputCls} value={s.d} onChange={(e) => setS({ ...s, d: e.target.value })} /></Field>
            <Field label={T("区分")}>
              <select disabled={!editable} className={selectCls} value={s.kind} onChange={(e) => setS({ ...s, kind: e.target.value as "inc" | "exp" })}>
                <option value="inc">{T("売上（買取代金の入金）")}</option>
                <option value="exp">{T("仕入（こちらが買取）")}</option>
              </select>
            </Field>
            <Field label={T("発行元（買取業者）")} className="col-span-2"><input disabled={!editable} className={inputCls} value={s.issuer} onChange={(e) => setS({ ...s, issuer: e.target.value })} /></Field>
            <Field label={T("登録番号")} className="col-span-2"><input disabled={!editable} className={inputCls} placeholder={T("T + 13桁（なければ空欄）")} value={s.registration_no} onChange={(e) => setS({ ...s, registration_no: e.target.value.trim() })} /></Field>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] text-xs">
              <thead><tr className="border-b border-slate-200 text-left text-[11px] text-slate-500">
                <th className="py-1.5 font-bold">{T("品名")}</th><th className="text-right font-bold">{T("数量(kg)")}</th>
                <th className="text-right font-bold">{T("単価")}</th><th className="text-right font-bold">{T("金額")}</th><th />
              </tr></thead>
              <tbody>
                {s.lines.map((l, i) => {
                  const bad = l.amount != null && l.qty != null && l.unit_price != null && Math.abs(l.qty * l.unit_price - l.amount) > 1;
                  return (
                    <tr key={i} className={"border-b border-slate-100 " + (bad ? "bg-amber-50" : "")}>
                      <td className="py-1 pr-1"><input disabled={!editable} className={inputCls} value={l.item} onChange={(e) => setLine(i, { item: e.target.value })} /></td>
                      <td className="px-1"><input disabled={!editable} inputMode="decimal" className={inputCls + " text-right tabular-nums"} value={l.qty ?? ""} onChange={(e) => setLine(i, { qty: num(e.target.value) })} onBlur={() => l.amount == null && recalc(i)} /></td>
                      <td className="px-1"><input disabled={!editable} inputMode="decimal" className={inputCls + " text-right tabular-nums"} value={l.unit_price ?? ""} onChange={(e) => setLine(i, { unit_price: num(e.target.value) })} /></td>
                      <td className="px-1"><input disabled={!editable} inputMode="numeric" className={inputCls + " text-right tabular-nums" + (bad ? " border-amber-400" : "")} value={l.amount ?? ""} onChange={(e) => setLine(i, { amount: num(e.target.value) })} /></td>
                      <td className="w-14 text-right">
                        {editable && <>
                          <button title={T("数量×単価で計算")} onClick={() => recalc(i)} className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-navy">=</button>
                          <button title={T("明細を削除")} onClick={() => setS({ ...s, lines: s.lines.filter((_, j) => j !== i) })} className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600"><Trash2 size={13} /></button>
                        </>}
                      </td>
                    </tr>);
                })}
              </tbody>
            </table>
          </div>
          {editable && <button onClick={() => setS({ ...s, lines: [...s.lines, { item: "", qty: null, unit_price: null, amount: null }] })}
            className="flex w-fit items-center gap-1 text-[11px] font-bold text-navy hover:underline"><Plus size={13} />{T("明細を追加")}</button>}

          <div className="flex items-end justify-between gap-2 rounded-lg bg-slate-50 p-3">
            <Field label={T("伝票合計（税込）")}>
              <input disabled={!editable} inputMode="numeric" className={inputCls + " w-40 text-right text-sm font-bold tabular-nums"} value={s.total || ""} onChange={(e) => setS({ ...s, total: num(e.target.value) ?? 0 })} />
            </Field>
            {editable && <Btn onClick={sumLines}>{T("明細の合計を入れる")}</Btn>}
          </div>

          {s.duplicate_of && s.status === "pending" && (
            <p className="flex items-center gap-1.5 rounded-lg bg-amber-50 p-2 text-amber-700"><TriangleAlert size={14} />
              {T("同じ発行元・日付・合計の伝票がすでにあります（No.{a}）。二重取込でないか確認してください。", { a: s.duplicate_of })}</p>)}
          {s.status === "pending" && (problems.length
            ? <ul className="flex flex-col gap-1 rounded-lg bg-red-50 p-2 text-red-700">{problems.map((p) => <li key={p} className="flex gap-1.5"><X size={13} className="mt-0.5 shrink-0" />{p}</li>)}</ul>
            : <p className="flex items-center gap-1.5 rounded-lg bg-mint/10 p-2 text-mint-700"><CircleCheck size={14} />{T("チェックOK。承認すると売上（10%・税込）として帳簿に記録されます。")}</p>)}

          {editable && (
            <div className="flex flex-wrap justify-end gap-2">
              <Btn onClick={reject} disabled={busy}><X size={13} />{T("却下")}</Btn>
              <Btn onClick={save} disabled={busy}>{T("保存")}</Btn>
              <Btn kind="primary" onClick={approve} disabled={busy || problems.length > 0}>
                {busy ? <LoaderCircle size={13} className="animate-spin" /> : <CircleCheck size={13} />}{T("承認して記帳")}
              </Btn>
            </div>)}
        </div>
      </div>
    </Card>
  );
}
