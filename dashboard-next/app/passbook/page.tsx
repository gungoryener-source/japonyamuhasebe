"use client";

/** T-062: 通帳の確認。通帳スキャン（AI 読取）・ネットバンキング CSV の明細に取引先・登録番号・勘定科目を付け、確認して記帳する。 */
import { useRef, useState } from "react";
import { BookOpenCheck, CircleCheck, Download, FileSpreadsheet, FileUp, LoaderCircle, Search, TriangleAlert } from "lucide-react";
import { api, saveBlob, type ApiReview, type ApiReviewRow } from "../lib/api";
import { AppShell, useShell } from "../components/shell";
import { Badge, Btn, Card, Empty, Field, inputCls, ReadOnlyNote, selectCls, Stat, yen } from "../components/ui";
import { useLoad } from "../components/useLoad";
import { T } from "../lib/i18n";

const CATS = ["売上高", "受取利息", "雑収入", "外注工賃", "地代家賃", "支払手数料", "旅費交通費", "通信費", "水道光熱費",
  "消耗品費", "租税公課", "損害保険料", "車両費", "仕入高", "給料賃金", "雑費", "現金", "事業主貸", "事業主借"];
const TRANSFER = ["現金", "現金引出", "現金預入", "事業主貸", "事業主借", "繰越"];

const cpd = (name: string, reg: string) => ({ id: 0, name, registration_no: reg, corporate_number: reg.slice(1) });
const DEMO: ApiReview = {
  nta_enabled: false, ai_enabled: true,
  counts: { total: 6, open: 5, unknown: 1, balance_errors: 1 },
  rows: [
    { id: 1, d: "2024-11-06", description: "ATM手数料", amount: -220, balance: 834325, account: "名古屋銀行 五月通支店", src: "passbook", balance_ok: 1, status: "", entry_id: null, category: "支払手数料", counterparty: null, match: "rule", book: true, candidates: [] },
    { id: 2, d: "2024-11-07", description: "ﾌﾙﾊｼｲｰﾋﾟｰｵｰ(ｶ", amount: -200000, balance: 634325, account: "名古屋銀行 五月通支店", src: "passbook", balance_ok: 1, status: "", entry_id: null, category: "外注工賃", counterparty: cpd("フルハシEPO株式会社", "T1234567890123"), match: "name", book: true, candidates: [] },
    { id: 3, d: "2024-11-07", description: "ATM支払", amount: -200000, balance: 434325, account: "名古屋銀行 五月通支店", src: "passbook", balance_ok: 1, status: "", entry_id: null, category: "現金", counterparty: null, match: "rule", book: false, candidates: [] },
    { id: 4, d: "2024-11-15", description: "振込ｶ)ｴﾑｱｰﾙｴﾌ", amount: 4300000, balance: 4734325, account: "名古屋銀行 五月通支店", src: "passbook", balance_ok: 1, status: "confirmed", entry_id: 9, category: "売上高", counterparty: cpd("株式会社ＭＲＦ", "T6180001147206"), match: "learned", book: true, candidates: [] },
    { id: 5, d: "2024-11-20", description: "EB基本手数料", amount: -3300, balance: 4730000, account: "名古屋銀行 五月通支店", src: "passbook", balance_ok: 0, status: "", entry_id: null, category: "支払手数料", counterparty: null, match: "rule", book: true, candidates: [] },
    { id: 6, d: "2024-11-21", description: "ｾﾞﾝﾎﾟﾚﾝ(ｶ", amount: -46200, balance: 4684125, account: "名古屋銀行 五月通支店", src: "passbook", balance_ok: null, status: "", entry_id: null, category: "", counterparty: null, match: "", book: true, candidates: [] },
  ],
};

type Edit = { name: string; reg: string; category: string; book: boolean };

export default function PassbookPage() {
  const { mode, live, toast, canEdit } = useShell();
  const y = new Date().getFullYear();
  const [from, setFrom] = useState(`${y - 1}-01-01`);
  const [to, setTo] = useState(`${y}-12-31`);
  const [onlyOpen, setOnlyOpen] = useState(true);
  const { data, loading, reload } = useLoad(mode, () => api.bankReview(from, to), DEMO, [from, to]);
  const [edits, setEdits] = useState<Record<number, Edit>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const pbRef = useRef<HTMLInputElement>(null);
  const xlRef = useRef<HTMLInputElement>(null);

  const rows = data.rows.filter((r) => !onlyOpen || !r.status);
  const edit = (r: ApiReviewRow): Edit => edits[r.id] ?? {
    name: r.counterparty?.name ?? "", reg: r.counterparty?.registration_no ?? "", category: r.category, book: r.book,
  };
  const setEdit = (r: ApiReviewRow, p: Partial<Edit>) => setEdits((e) => ({ ...e, [r.id]: { ...edit(r), ...p } }));
  const autoIds = data.rows.filter((r) => !r.status && r.balance_ok !== 0 && r.category && (r.match || r.counterparty)).map((r) => r.id);

  const run = async (key: string, fn: () => Promise<void>) => {
    if (!live) return toast(T("デモでは表示のみです"));
    setBusy(key);
    try { await fn(); } catch (e) {
      toast(T("失敗しました: {a}", { a: e instanceof Error ? e.message : String(e) }));
    } finally { setBusy(null); }
  };

  const uploadPassbook = (f?: File) => f && run("pb", async () => {
    const r = await api.passbookUpload(f);
    toast(T("通帳を読み取りました: {a}件（新規 {b}件・重複 {c}件）", { a: r.read, b: r.imported, c: r.duplicates })
      + (r.balance_errors ? " ・ " + T("残高が合わない行 {a}件", { a: r.balance_errors }) : ""));
    if (pbRef.current) pbRef.current.value = "";
    await reload();
  });
  const importExcel = (f?: File) => f && run("xl", async () => {
    const r = await api.counterpartyImport(f);
    toast(T("取引先を {a}件 取り込みました", { a: r.imported }));
    if (xlRef.current) xlRef.current.value = "";
    await reload();
  });
  const confirm = (r: ApiReviewRow) => run(`c${r.id}`, async () => {
    const e = edit(r);
    await api.bankConfirm(r.id, { book: e.book && !TRANSFER.includes(e.category), category: e.category, counterparty_name: e.name, registration_no: e.reg });
    await reload();
  });
  const confirmAll = () => run("all", async () => {
    const r = await api.bankConfirmMatched(autoIds);
    toast(T("{a}件を確定しました（{b}件は要確認）", { a: r.confirmed, b: r.skipped }));
    await reload();
  });
  const lookup = (r: ApiReviewRow) => run(`l${r.id}`, async () => {
    const res = (await api.counterpartyLookup(r.description)).results;
    if (!res.length) return toast(T("国税庁のデータで見つかりませんでした。正式名称を入力してください"));
    setEdit(r, { name: res[0].name, reg: res[0].registration_no_guess });
    toast(T("{a} を見つけました（登録番号は要確認）", { a: res[0].name }));
  });
  const fix = (r: ApiReviewRow, out: string, inn: string, bal: string) => run(`f${r.id}`, async () => {
    const n = (v: string) => Number(v.replace(/[,¥\s]/g, "")) || 0;
    await api.bankFix(r.id, n(inn) - n(out), bal.trim() ? n(bal) : null);
    toast(T("修正しました。残高を再チェックしました"));
    await reload();
  });
  const xlsx = () => run("dl", async () => saveBlob(await api.bankXlsx(from, to), `通帳整理表_${from}_${to}.xlsx`));

  return (
    <AppShell title="通帳の確認" en="Passbook Review"
      sub="通帳のスキャンやネットバンキングの明細に取引先・登録番号・勘定科目を付けて、確認後に記帳します"
      actions={canEdit ? (
        <>
          <input ref={pbRef} type="file" accept="application/pdf,image/*" className="hidden" onChange={(e) => uploadPassbook(e.target.files?.[0])} />
          <input ref={xlRef} type="file" accept=".xlsx" className="hidden" onChange={(e) => importExcel(e.target.files?.[0])} />
          <Btn onClick={() => xlRef.current?.click()} disabled={!!busy}>{busy === "xl" ? <LoaderCircle size={14} className="animate-spin" /> : <FileSpreadsheet size={14} />}{T("取引先をExcelから取込")}</Btn>
          <Btn kind="primary" onClick={() => pbRef.current?.click()} disabled={!!busy || (live && !data.ai_enabled)}>
            {busy === "pb" ? <LoaderCircle size={14} className="animate-spin" /> : <FileUp size={14} />}{busy === "pb" ? T("読み取り中…（1〜2分）") : T("通帳を取込（PDF・写真）")}
          </Btn>
        </>
      ) : undefined}>
      {!canEdit && <ReadOnlyNote />}
      {live && !data.ai_enabled && <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-700">{T("通帳スキャンの読み取りには AI の設定（ANTHROPIC_API_KEY）が必要です。ネットバンキングの CSV は「銀行連携」から取り込めます。")}</p>}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label={T("明細")} value={`${data.counts.total}${T("件")}`} />
        <Stat label={T("未確認")} value={`${data.counts.open}${T("件")}`} tone={data.counts.open ? "warn" : "ok"} />
        <Stat label={T("取引先が不明")} value={`${data.counts.unknown}${T("件")}`} tone={data.counts.unknown ? "warn" : undefined} />
        <Stat label={T("残高が合わない行")} value={`${data.counts.balance_errors}${T("件")}`} tone={data.counts.balance_errors ? "bad" : "ok"} />
      </div>

      <Card title="通帳整理表" en="Passbook"
        right={<div className="flex flex-wrap items-end gap-2 text-xs">
          <Field label={T("開始日")}><input type="date" className={inputCls} value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
          <Field label={T("終了日")}><input type="date" className={inputCls} value={to} onChange={(e) => setTo(e.target.value)} /></Field>
          <label className="flex items-center gap-1.5 pb-2"><input type="checkbox" checked={onlyOpen} onChange={(e) => setOnlyOpen(e.target.checked)} />{T("未確認のみ")}</label>
          <Btn onClick={xlsx} disabled={!!busy}><Download size={13} />{T("Excel 出力")}</Btn>
          {canEdit && <Btn kind="primary" onClick={confirmAll} disabled={!!busy || !autoIds.length}>
            {busy === "all" ? <LoaderCircle size={13} className="animate-spin" /> : <BookOpenCheck size={13} />}{T("自動照合した {a}件 をまとめて確定", { a: autoIds.length })}
          </Btn>}
        </div>}>
        {loading ? <p className="flex items-center gap-2 text-xs text-slate-400"><LoaderCircle size={14} className="animate-spin" />{T("読み込み中…")}</p>
          : rows.length === 0 ? <Empty>{T("明細はありません。LINE で「通帳」と送ってから通帳の写真を送るか、「通帳を取込」から PDF を選んでください。")}</Empty>
          : <div className="overflow-x-auto">
            <table className="w-full min-w-[1120px] text-xs">
              <thead><tr className="border-b border-slate-200 text-left text-[11px] text-slate-500">
                <th className="py-2 font-bold">{T("日付")}</th><th className="text-right font-bold">{T("支出")}</th><th className="text-right font-bold">{T("入金")}</th>
                <th className="pl-3 font-bold">{T("摘要（通帳）")}</th><th className="font-bold">{T("取引先（正式名称）")}</th><th className="font-bold">{T("登録番号")}</th>
                <th className="font-bold">{T("勘定科目")}</th><th className="text-center font-bold">{T("記帳")}</th><th className="text-right font-bold">{T("残高")}</th><th />
              </tr></thead>
              <tbody>
                {rows.map((r) => {
                  const e = edit(r);
                  const done = !!r.status;
                  const ok = !done && canEdit;
                  return (
                    <tr key={r.id} className={"border-b border-slate-100 align-middle " + (r.balance_ok === 0 ? "bg-red-50" : done ? "opacity-60" : "")}>
                      <td className="whitespace-nowrap py-1.5 tabular-nums">{r.d}</td>
                      {r.balance_ok === 0 && ok ? (
                        <FixCells r={r} busy={busy === `f${r.id}`} onFix={fix} />
                      ) : (<>
                        <td className="text-right tabular-nums">{r.amount < 0 ? yen(-r.amount) : ""}</td>
                        <td className="text-right tabular-nums text-mint-700">{r.amount > 0 ? yen(r.amount) : ""}</td>
                      </>)}
                      <td className="max-w-[150px] truncate pl-3 text-slate-600" title={r.description}>{r.description}</td>
                      <td className="pr-1">
                        <div className="flex items-center gap-1">
                          <input disabled={!ok} className={inputCls + " min-w-[150px]"} value={e.name} placeholder={r.match === "rule" ? "—" : T("正式名称")}
                            onChange={(ev) => setEdit(r, { name: ev.target.value })} />
                          {ok && !e.name && r.match !== "rule" && data.nta_enabled &&
                            <button title={T("国税庁で検索")} onClick={() => lookup(r)} className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-navy">
                              {busy === `l${r.id}` ? <LoaderCircle size={13} className="animate-spin" /> : <Search size={13} />}</button>}
                        </div>
                      </td>
                      <td className="pr-1"><input disabled={!ok} className={inputCls + " w-[132px] tabular-nums"} value={e.reg} placeholder="T…" onChange={(ev) => setEdit(r, { reg: ev.target.value.trim() })} /></td>
                      <td className="pr-1">
                        <select disabled={!ok} className={selectCls + " w-[140px]"} value={e.category} onChange={(ev) => setEdit(r, { category: ev.target.value, book: !TRANSFER.includes(ev.target.value) })}>
                          <option value="">{T("選択")}</option>
                          {[...new Set([e.category, ...CATS].filter(Boolean))].map((c) => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </td>
                      <td className="text-center"><input type="checkbox" disabled={!ok || TRANSFER.includes(e.category)} checked={e.book && !TRANSFER.includes(e.category)} onChange={(ev) => setEdit(r, { book: ev.target.checked })} /></td>
                      <td className="whitespace-nowrap text-right tabular-nums">
                        {r.balance_ok === 0 && ok ? null : r.balance != null ? yen(r.balance) : ""}
                        {r.balance_ok === 0 && <TriangleAlert size={12} className="ml-1 inline text-red-500" aria-label={T("残高が合いません")} />}
                      </td>
                      <td className="w-28 text-right">
                        {done ? <Badge tone={r.status === "confirmed" ? "ok" : "muted"}>{T(r.status === "confirmed" ? "記帳済" : "記帳しない")}</Badge>
                          : ok && <Btn onClick={() => confirm(r)} disabled={!!busy || !e.category}>
                            {busy === `c${r.id}` ? <LoaderCircle size={12} className="animate-spin" /> : <CircleCheck size={12} />}{T("確定")}</Btn>}
                      </td>
                    </tr>);
                })}
              </tbody>
            </table>
          </div>}
        <p className="text-[11px] text-slate-400">
          {T("赤い行は残高が合いません（読み取りの誤りの可能性）。通帳と見比べて金額を確認してください。確定した取引先は次回から自動で照合されます。")}
        </p>
      </Card>
    </AppShell>
  );
}

/** 残高が合わない行: 支出・入金・残高をその場で直す（通帳と見比べて）。 */
function FixCells({ r, busy, onFix }: { r: ApiReviewRow; busy: boolean; onFix: (r: ApiReviewRow, out: string, inn: string, bal: string) => void }) {
  const [out, setOut] = useState(r.amount < 0 ? String(-r.amount) : "");
  const [inn, setInn] = useState(r.amount > 0 ? String(r.amount) : "");
  const [bal, setBal] = useState(r.balance != null ? String(r.balance) : "");
  return (
    <>
      <td className="pr-1"><input inputMode="numeric" className={inputCls + " w-24 border-red-300 text-right tabular-nums"} value={out} onChange={(e) => setOut(e.target.value)} /></td>
      <td className="pr-1"><input inputMode="numeric" className={inputCls + " w-24 border-red-300 text-right tabular-nums"} value={inn} onChange={(e) => setInn(e.target.value)} />
        <div className="mt-1 flex items-center justify-end gap-1">
          <input inputMode="numeric" title={T("残高")} className={inputCls + " w-24 border-red-300 text-right tabular-nums"} value={bal} onChange={(e) => setBal(e.target.value)} />
          <button onClick={() => onFix(r, out, inn, bal)} className="rounded bg-red-600 px-2 py-1 text-[11px] font-bold text-white hover:bg-red-700">
            {busy ? <LoaderCircle size={11} className="animate-spin" /> : T("修正")}</button>
        </div>
      </td>
    </>
  );
}
