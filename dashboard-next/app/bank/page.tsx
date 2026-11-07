"use client";

/** 銀行連携 — 入出金明細CSVの取込・請求書との自動消込・口座振替の経費登録 */
import { useRef, useState } from "react";
import { ArrowRightLeft, CircleCheck, FileUp, LoaderCircle } from "lucide-react";
import { api, EXPENSE_CATEGORIES, type ApiBankTx, type ApiSuggestion } from "../lib/api";
import { AppShell, useShell } from "../components/shell";
import { Badge, Btn, Card, Empty, Field, inputCls, ReadOnlyNote, selectCls, Stat, yen } from "../components/ui";
import { useLoad } from "../components/useLoad";

type BankData = { transactions: ApiBankTx[]; suggestions: ApiSuggestion[] };

const DEMO: BankData = {
  transactions: [
    { id: 6, d: "2026-11-05", description: "口座振替 ﾗｸﾃﾝﾓﾊﾞｲﾙ", amount: -3_278, balance: 4_196_722, account: "三菱UFJ 普通", invoice_no: "", entry_id: null },
    { id: 5, d: "2026-11-02", description: "振込 ｶ)ｻｸﾗｾｲｻｸｼﾖ", amount: 1_320_000, balance: 4_200_000, account: "三菱UFJ 普通", invoice_no: "", entry_id: null },
    { id: 4, d: "2026-10-31", description: "口座振替 ﾄｳｷﾖｳｼｴｱｵﾌｲｽ", amount: -66_000, balance: 2_880_000, account: "三菱UFJ 普通", invoice_no: "", entry_id: 12 },
    { id: 3, d: "2026-10-30", description: "振込 ﾄﾞ)ﾋｶﾘﾃﾞｻﾞｲﾝ", amount: 550_000, balance: 2_946_000, account: "三菱UFJ 普通", invoice_no: "INV-2026-0409", entry_id: null },
  ],
  suggestions: [{ tx_id: 5, invoice_no: "INV-2026-0418", client: "株式会社サクラ製作所", amount: 1_320_000, date: "2026-11-02" }],
};

const BANKS = ["三菱UFJ銀行", "三井住友銀行", "みずほ銀行", "ゆうちょ銀行", "楽天銀行", "PayPay銀行", "住信SBIネット銀行", "GMOあおぞらネット銀行"];

export default function BankPage() {
  return (
    <AppShell title="銀行連携" en="Bank Sync" sub="ネットバンキングの入出金明細（CSV）を取り込み、請求書の消込と経費登録を自動化">
      <Bank />
    </AppShell>
  );
}

function Bank() {
  const { mode, live, toast, canEdit } = useShell();
  const { data, setData, loading, reload } = useLoad<BankData>(mode, api.bank, DEMO);
  const fileRef = useRef<HTMLInputElement>(null);
  const [account, setAccount] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const tx = data.transactions;
  const pending = tx.filter((t) => !t.invoice_no && !t.entry_id);
  const deposits = tx.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0);
  const withdrawals = tx.filter((t) => t.amount < 0).reduce((s, t) => s - t.amount, 0);

  const onFile = async (file?: File | null) => {
    if (!file) return;
    if (!live) return toast("CSV取込は帳簿に接続すると使えます（デモでは表示のみ）");
    setBusy(true); setResult(null);
    try {
      const r = await api.bankImport(file, account);
      setResult(`${r.parsed}件を読み込み、${r.imported}件を追加しました${r.duplicates ? `（重複 ${r.duplicates}件はスキップ）` : ""}。消込候補 ${r.suggestions.length}件`);
      reload();
    } catch (e) {
      setResult(`取り込めませんでした: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(false);
    }
  };

  const match = async (s: ApiSuggestion) => {
    if (!live) {
      setData((d) => ({
        transactions: d.transactions.map((t) => (t.id === s.tx_id ? { ...t, invoice_no: s.invoice_no } : t)),
        suggestions: d.suggestions.filter((x) => x.tx_id !== s.tx_id),
      }));
      return toast(`${s.invoice_no} を消込しました（デモ）`);
    }
    try {
      await api.bankMatch(s.tx_id, s.invoice_no);
      toast(`${s.invoice_no} を消込しました（入金日 ${s.date}）`);
      reload();
    } catch (e) {
      toast(`消込に失敗しました: ${e instanceof Error ? e.message : e}`);
    }
  };

  const toEntry = async (t: ApiBankTx, category: string, rate: number) => {
    if (!live) {
      setData((d) => ({ ...d, transactions: d.transactions.map((x) => (x.id === t.id ? { ...x, entry_id: 1 } : x)) }));
      return toast(`経費（${category}）に登録しました（デモ）`);
    }
    try {
      await api.bankToEntry(t.id, category, rate);
      toast(`経費に登録しました: ${category} ${yen(-t.amount)}`);
      reload();
    } catch (e) {
      toast(`登録に失敗しました: ${e instanceof Error ? e.message : e}`);
    }
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="入金合計" value={yen(deposits)} tone="ok" />
        <Stat label="出金合計" value={yen(withdrawals)} />
        <Stat label="未処理の明細" value={`${pending.length} 件`} tone={pending.length ? "warn" : "ok"} />
        <Stat label="消込候補" value={`${data.suggestions.length} 件`} tone={data.suggestions.length ? "warn" : undefined} />
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Card title="明細CSVを取り込む" en="Import" className="lg:col-span-1">
          {canEdit ? <>
          <Field label="口座名（任意）">
            <input id="bank-account" value={account} onChange={(e) => setAccount(e.target.value)} placeholder="三菱UFJ 普通" className={inputCls} />
          </Field>
          <button onClick={() => fileRef.current?.click()} disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 py-5 text-xs text-slate-500 hover:border-mint hover:text-mint-700 disabled:opacity-60">
            {busy ? <><LoaderCircle size={15} className="animate-spin" />取込中…</> : <><FileUp size={15} />CSVファイルを選ぶ</>}
          </button>
          <input ref={fileRef} type="file" accept=".csv,text/csv" hidden onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }} />
          {result && <p className="rounded-lg bg-slate-50 px-3 py-2 text-[11px] text-slate-600">{result}</p>}
          </> : <ReadOnlyNote>閲覧者のため、明細の取込・消込・経費登録はできません。</ReadOnlyNote>}
          <p className="text-[11px] leading-relaxed text-slate-400">
            ネットバンキングの「入出金明細」画面からCSVをダウンロードしてください。Shift_JIS / UTF-8 どちらも対応。同じ明細を何度取り込んでも重複しません。
          </p>
          <div className="flex flex-wrap gap-1">{BANKS.map((b) => <span key={b} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">{b}</span>)}</div>
        </Card>

        <Card title="消込候補" en="Auto Matching" className="lg:col-span-2"
          right={<span className="text-[11px] text-slate-400">入金額 = 未入金請求書の合計</span>}>
          {data.suggestions.length === 0 ? (
            <Empty>消込候補はありません。入金明細を取り込むと、金額が一致する請求書を自動で探します。</Empty>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.suggestions.map((s) => (
                <li key={s.tx_id} className="flex flex-wrap items-center gap-3 py-2">
                  <ArrowRightLeft size={15} className="text-mint" />
                  <div className="min-w-0 flex-1 text-xs">
                    <p className="font-bold text-navy">{s.client} <span className="font-mono font-normal text-slate-400">{s.invoice_no}</span></p>
                    <p className="text-[11px] text-slate-400">{s.date.replaceAll("-", "/")} 入金</p>
                  </div>
                  <span className="font-mono text-sm font-semibold text-mint-600 tabular">{yen(s.amount)}</span>
                  {canEdit && <Btn kind="mint" onClick={() => match(s)}><CircleCheck size={13} />消込する</Btn>}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="入出金明細" en="Transactions">
        {loading && <p className="text-xs text-slate-400">読み込み中…</p>}
        {tx.length === 0 ? (
          <Empty>まだ明細がありません。上の「CSVファイルを選ぶ」から取り込んでください。</Empty>
        ) : (
          <div className="-mx-4 overflow-x-auto">
            <table className="w-full min-w-[820px] text-xs">
              <thead>
                <tr className="border-y border-slate-100 bg-slate-50 text-left text-[10px] uppercase tracking-wider text-slate-400">
                  <th className="px-4 py-2 font-medium">日付</th>
                  <th className="px-2 py-2 font-medium">摘要</th>
                  <th className="px-2 py-2 text-right font-medium">入金</th>
                  <th className="px-2 py-2 text-right font-medium">出金</th>
                  <th className="px-2 py-2 text-right font-medium">残高</th>
                  <th className="px-4 py-2 font-medium">処理</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tx.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50/70">
                    <td className="whitespace-nowrap px-4 py-1.5 font-mono text-slate-500 tabular">{t.d.replaceAll("-", "/")}</td>
                    <td className="max-w-[260px] truncate px-2 py-1.5 text-slate-700">{t.description}{t.account && <span className="ml-1 text-[10px] text-slate-400">{t.account}</span>}</td>
                    <td className="whitespace-nowrap px-2 py-1.5 text-right font-mono text-mint-600 tabular">{t.amount > 0 ? yen(t.amount) : ""}</td>
                    <td className="whitespace-nowrap px-2 py-1.5 text-right font-mono text-navy tabular">{t.amount < 0 ? yen(-t.amount) : ""}</td>
                    <td className="whitespace-nowrap px-2 py-1.5 text-right font-mono text-slate-400 tabular">{t.balance != null ? yen(t.balance) : ""}</td>
                    <td className="px-4 py-1.5">
                      {t.invoice_no ? <Badge tone="ok">消込済 {t.invoice_no}</Badge>
                        : t.entry_id ? <Badge tone="ok">経費登録済</Badge>
                          : t.amount < 0 && canEdit ? <ExpenseAction desc={t.description} onSave={(c, r) => toEntry(t, c, r)} />
                            : <Badge tone="muted">未消込</Badge>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function guess(desc: string) {
  if (/ﾓﾊﾞｲﾙ|ﾄﾞｺﾓ|ｿﾌﾄﾊﾞﾝｸ|NTT|ｴｰﾕｰ/.test(desc)) return "通信費";
  if (/ﾃﾞﾝｷ|ｶﾞｽ|ｽｲﾄﾞｳ|電力|ガス/.test(desc)) return "水道光熱費";
  if (/ｵﾌｲｽ|ﾔﾁﾝ|家賃|ｼｴｱ/.test(desc)) return "地代家賃";
  if (/ﾃｽｳﾘﾖｳ|手数料/.test(desc)) return "支払手数料";
  return "雑費";
}

function ExpenseAction({ desc, onSave }: { desc: string; onSave: (category: string, rate: number) => void }) {
  const [open, setOpen] = useState(false);
  const [cat, setCat] = useState(guess(desc));
  const [rate, setRate] = useState(10);
  if (!open) return <Btn onClick={() => setOpen(true)}>経費に登録</Btn>;
  return (
    <span className="flex items-center gap-1">
      <select value={cat} onChange={(e) => setCat(e.target.value)} className={selectCls + " h-7 w-28"} aria-label="勘定科目">
        <option value="">科目を選択</option>
        {EXPENSE_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
      </select>
      <select value={rate} onChange={(e) => setRate(Number(e.target.value))} className={selectCls + " h-7 w-20"} aria-label="税率">
        <option value={10}>10%</option><option value={8}>8%</option><option value={0}>対象外</option>
      </select>
      <Btn kind="primary" disabled={!cat} onClick={() => onSave(cat, rate)} className="h-7">登録</Btn>
    </span>
  );
}

