"use client";

/** 固定資産 — 固定資産台帳と減価償却費の計算（定額法・一括償却・少額減価償却資産の特例） */
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api, type ApiAsset, type ApiAssetSchedule, type AssetDraft } from "../lib/api";
import { AppShell, useShell } from "../components/shell";
import { Badge, Btn, Card, Empty, Field, inputCls, ReadOnlyNote, selectCls, Stat, yen } from "../components/ui";
import { useLoad } from "../components/useLoad";
import { T } from "../lib/i18n";

type Data = { assets: ApiAsset[]; schedule: ApiAssetSchedule };
const YEAR = 2026;

const DEMO: Data = {
  assets: [{ id: 1, name: "ノートPC", acquired: "2026-07-10", in_service: "2026-07-10", cost: 500_000, life: 4, method: "straight", business_pct: 100 }],
  schedule: {
    year: YEAR, total_ordinary: 62_500, total_expense: 62_500, unverified: ["depreciation.rate_rule"],
    rows: [{ asset_id: 1, name: "ノートPC", method: "straight", cost: 500_000, life: 4, rate_permille: 250, months: 6, ordinary: 62_500, business_pct: 100, expense: 62_500, book_end: 437_500 }],
    warnings: ["これは帳簿データからの計算結果です。申告前に税理士・税務署に確認してください。"],
  },
};

const METHOD: Record<string, string> = { straight: "定額法", lump: "一括償却資産", small: "少額減価償却資産の特例" };
const EMPTY: AssetDraft = { name: "", acquired: "", in_service: "", cost: 0, life: 4, method: "straight", business_pct: 100 };

export default function AssetsPage() {
  return (
    <AppShell title="固定資産" en="Fixed Assets" sub="固定資産台帳と減価償却費の計算（青色申告決算書の「減価償却費」へ自動反映）">
      <Assets />
    </AppShell>
  );
}

function Assets() {
  const { mode, live, toast, canEdit } = useShell();
  const { data, setData, loading, reload } = useLoad<Data>(
    mode, async () => { const [assets, schedule] = await Promise.all([api.assets(), api.assetSchedule(YEAR)]); return { assets, schedule }; }, DEMO);
  const [f, setF] = useState<AssetDraft>(EMPTY);
  const [err, setErr] = useState("");
  const s = data.schedule;

  const add = async () => {
    setErr("");
    const body: AssetDraft = { ...f, in_service: f.in_service || f.acquired, life: f.method === "straight" ? f.life : 0 };
    if (!live) {
      setData((d) => ({ ...d, assets: [...d.assets, { ...body, id: Date.now() }] }));
      setF(EMPTY);
      return toast(T("登録しました（デモ）"));
    }
    try {
      await api.createAsset(body);
      setF(EMPTY); toast(T("登録しました")); reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  const del = async (a: ApiAsset) => {
    if (!live) { setData((d) => ({ ...d, assets: d.assets.filter((x) => x.id !== a.id) })); return toast(T("削除しました（デモ）")); }
    try { await api.deleteAsset(a.id); toast(T("削除しました")); reload(); }
    catch (e) { toast(T("削除に失敗しました: {a}", { a: e instanceof Error ? e.message : e })); }
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label={T("登録資産")} value={T("{a} 件", { a: data.assets.length })} />
        <Stat label={T("{a}年 普通償却費", { a: YEAR })} value={yen(s.total_ordinary)} />
        <Stat label={T("必要経費算入額")} value={yen(s.total_expense)} tone="ok" />
        <Stat label={T("未償却残高")} value={yen(s.rows.reduce((t, r) => t + r.book_end, 0))} />
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Card title="資産を登録" en="Add Asset" className="lg:col-span-1">
          {canEdit ? <>
            <Field label={T("資産名")}><input id="asset-name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={inputCls} /></Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label={T("取得日")}><input id="asset-acq" type="date" value={f.acquired} onChange={(e) => setF({ ...f, acquired: e.target.value })} className={inputCls} /></Field>
              <Field label={T("事業供用日")}><input id="asset-svc" type="date" value={f.in_service} onChange={(e) => setF({ ...f, in_service: e.target.value })} className={inputCls} /></Field>
              <Field label={T("取得価額（円）")}><input id="asset-cost" type="number" min={0} value={f.cost || ""} onChange={(e) => setF({ ...f, cost: Number(e.target.value) })} className={inputCls} /></Field>
              <Field label={T("事業専用割合 %")}><input id="asset-pct" type="number" min={1} max={100} value={f.business_pct} onChange={(e) => setF({ ...f, business_pct: Number(e.target.value) })} className={inputCls} /></Field>
            </div>
            <Field label={T("償却方法")}>
              <select id="asset-method" value={f.method} onChange={(e) => setF({ ...f, method: e.target.value as AssetDraft["method"] })} className={selectCls}>
                {Object.entries(METHOD).map(([k, v]) => <option key={k} value={k}>{T(v)}</option>)}
              </select>
            </Field>
            {f.method === "straight" && (
              <Field label={T("耐用年数（年）")}><input id="asset-life" type="number" min={2} max={100} value={f.life} onChange={(e) => setF({ ...f, life: Number(e.target.value) })} className={inputCls} /></Field>
            )}
            {err && <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-[11px] text-rose-600">{err}</p>}
            <Btn kind="primary" onClick={add} disabled={!f.name || !f.acquired || !f.cost}><Plus size={13} />{T("登録")}</Btn>
          </> : <ReadOnlyNote>{T("閲覧者のため、資産の登録・削除はできません。")}</ReadOnlyNote>}
          <p className="text-[11px] leading-relaxed text-slate-400">
            {T("10万円未満の資産は経費として直接計上します。償却率は耐用年数から算出した暫定値です。")}
          </p>
        </Card>

        <Card title="減価償却費の計算" en="Depreciation Schedule" className="lg:col-span-2"
          right={<span className="text-[11px] text-slate-400">{T("{a}年分", { a: YEAR })}</span>}>
          {loading && <p className="text-xs text-slate-400">{T("読み込み中…")}</p>}
          {s.rows.length === 0 ? <Empty>{T("この年に償却する資産はありません。")}</Empty> : (
            <div className="-mx-4 overflow-x-auto">
              <table className="w-full min-w-[640px] text-xs">
                <thead>
                  <tr className="border-y border-slate-100 bg-slate-50 text-left text-[10px] uppercase tracking-wider text-slate-400">
                    <th className="px-4 py-2 font-medium">{T("資産")}</th>
                    <th className="px-2 py-2 text-right font-medium">{T("取得価額")}</th>
                    <th className="px-2 py-2 text-right font-medium">{T("月数")}</th>
                    <th className="px-2 py-2 text-right font-medium">{T("普通償却費")}</th>
                    <th className="px-2 py-2 text-right font-medium">{T("事業割合")}</th>
                    <th className="px-2 py-2 text-right font-medium">{T("必要経費")}</th>
                    <th className="px-4 py-2 text-right font-medium">{T("期末残高")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {s.rows.map((r) => (
                    <tr key={r.asset_id}>
                      <td className="px-4 py-1.5 text-slate-700">{r.name} <Badge tone="muted">{T(METHOD[r.method] ?? r.method)}</Badge></td>
                      <td className="px-2 py-1.5 text-right font-mono tabular">{yen(r.cost)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular">{r.months}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular">{yen(r.ordinary)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular">{r.business_pct}%</td>
                      <td className="px-2 py-1.5 text-right font-mono font-semibold text-navy tabular">{yen(r.expense)}</td>
                      <td className="px-4 py-1.5 text-right font-mono text-slate-400 tabular">{yen(r.book_end)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {s.unverified.length > 0 && <Badge tone="warn">{T("未検証の参数あり")}</Badge>}
          <ul className="space-y-1 text-[11px] text-slate-500">{s.warnings.map((w) => <li key={w}>・{w}</li>)}</ul>
        </Card>
      </div>

      <Card title="資産台帳" en="Asset Register">
        {data.assets.length === 0 ? <Empty>{T("まだ資産がありません。")}</Empty> : (
          <ul className="divide-y divide-slate-100">
            {data.assets.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-3 py-2 text-xs">
                <span className="min-w-0 flex-1 font-bold text-navy">{a.name}
                  <span className="ml-2 font-mono font-normal text-slate-400">{a.acquired.replaceAll("-", "/")} · {T(METHOD[a.method])}{a.method === "straight" ? ` · ${a.life}${T("年")}` : ""}</span></span>
                <span className="font-mono tabular">{yen(a.cost)}</span>
                {canEdit && <Btn onClick={() => del(a)} title={T("削除")}><Trash2 size={13} /></Btn>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
