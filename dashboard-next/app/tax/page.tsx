"use client";

/** 確定申告 / 税務 — 青色申告決算書（損益）・所得税の概算・消費税（課税方式別）・会計ソフト用CSV・税務カレンダー */
import { useEffect, useState } from "react";
import { CalendarClock, Download, FileText, TriangleAlert } from "lucide-react";
import { api, ApiError, openBlob, saveBlob, type ApiIncomeTax, type ApiPL, type ApiTax } from "../lib/api";
import { compute, KANI_LABEL, METHOD_LABEL, methodUnavailable, type Method, type Purchase, type Sale } from "../lib/tax";
import TAX_EXAMPLE from "../lib/tax-example.json";
import { estimateIncomeTax } from "../lib/income";
import { AppShell, useShell } from "../components/shell";
import { Badge, Btn, Card, cx, Field, inputCls, selectCls, Stat, yen } from "../components/ui";
import { T } from "../lib/i18n";

const DEMO_PL: ApiPL = {
  year: 2025, revenue: 8_000_000,
  expenses: [
    { category: "外注工賃", amount: 1_400_000 }, { category: "地代家賃", amount: 792_000 }, { category: "旅費交通費", amount: 286_000 },
    { category: "通信費", amount: 156_000 }, { category: "消耗品費", amount: 214_000 }, { category: "接待交際費", amount: 98_000 }, { category: "会議費", amount: 54_000 },
  ],
  expenses_total: 3_000_000, income_before_blue: 5_000_000, note: "税込経理（消費税込みの金額）で集計しています。",
};
const EX = TAX_EXAMPLE as unknown as { sales: Sale[]; purchases: Purchase[] };

const CALENDAR = [
  { d: "2026-11-10", t: "源泉所得税の納付（10月分）" },
  { d: "2026-11-30", t: "消費税 中間申告（該当者）" },
  { d: "2026-12-10", t: "源泉所得税の納付（11月分）" },
  { d: "2027-01-20", t: "源泉所得税 納期の特例（7〜12月分）" },
  { d: "2027-01-31", t: "法定調書合計表・償却資産申告" },
  { d: "2027-03-15", t: "所得税の確定申告（2026年分）期限" },
  { d: "2027-03-31", t: "個人事業者の消費税 確定申告 期限" },
];

export default function TaxPage() {
  return (
    <AppShell title="確定申告 / 税務" en="Tax Reporting" sub="青色申告決算書・所得税・消費税の概算と会計ソフト連携">
      <Tax />
    </AppShell>
  );
}

function Tax() {
  const { live, toast, mode } = useShell();
  const thisYear = Number(new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" }).slice(0, 4));
  const [year, setYear] = useState(live ? thisYear : 2025);
  const [pl, setPl] = useState<ApiPL>(DEMO_PL);
  const [blue, setBlue] = useState(650_000);
  // T-049: 令和9年分（2027）以後は 75万 が選べ、55万 は廃止。年を変えて選択肢から外れたら 65万 に戻す
  useEffect(() => {
    if ((year >= 2027 && blue === 550_000) || (year < 2027 && blue === 750_000)) setBlue(650_000);
  }, [year, blue]);
  const [social, setSocial] = useState("420000");
  const [other, setOther] = useState("0");
  const [it, setIt] = useState<Omit<ApiIncomeTax, "year" | "revenue" | "expenses" | "disclaimer"> | null>(null);
  const [itMsg, setItMsg] = useState<string | null>(null);
  const [method, setMethod] = useState<Method>("honsoku");
  const [kani, setKani] = useState(5);
  const [ct, setCt] = useState<{ output: number; input: number; payable: number } | null>(null);
  const [ctMsg, setCtMsg] = useState<string | null>(null);

  useEffect(() => { if (mode === "live") setYear(thisYear); }, [mode, thisYear]);

  // 損益
  useEffect(() => {
    if (!live) { setPl({ ...DEMO_PL, year }); return; }
    api.pl(year).then(setPl).catch((e) => toast(T("損益を取得できませんでした: {a}", { a: e instanceof Error ? e.message : e })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live, year]);

  // 所得税
  useEffect(() => {
    const s = Number(social) || 0, o = Number(other) || 0;
    if (!live) {
      const r = estimateIncomeTax(pl.revenue, pl.expenses_total, year, blue, s, o);
      setIt(r);
      setItMsg(r ? null : T("{a}年分の基礎控除は税制改正の内容を確認中のため、計算できません（対応: 2025〜2027年分）。", { a: year }));
      return;
    }
    api.incomeTax(year, { blue, social_insurance: s, other_deductions: o })
      .then((r) => { setIt(r); setItMsg(null); })
      .catch((e) => { setIt(null); setItMsg(e instanceof ApiError && e.status === 409 ? T("{a}年分の基礎控除は税制改正の内容を確認中のため、計算できません（対応: 2025〜2027年分）。", { a: year }) : T("計算できませんでした: {a}", { a: e instanceof Error ? e.message : e })); });
  }, [live, year, blue, social, other, pl.revenue, pl.expenses_total]);

  // 消費税
  useEffect(() => {
    const unavailable = methodUnavailable(method, { individual: true, taxYear: year, kaniType: kani });
    if (unavailable) { setCt(null); setCtMsg(unavailable); return; }
    if (!live) {
      const r = compute(EX.sales, EX.purchases, method, { individual: true, taxYear: 2026, kaniType: kani });
      setCt(r); setCtMsg(T("デモ: 2026年分の例"));
      return;
    }
    api.consumption(year, method, method === "kani" ? kani : undefined)
      .then((r) => { setCt({ output: r.output_tax, input: r.input_tax, payable: r.payable }); setCtMsg(null); })
      .catch((e) => { setCt(null); setCtMsg(e instanceof Error ? e.message : String(e)); });
  }, [live, year, method, kani]);

  const blueReturnPdf = async () => {
    if (!live) return toast(T("PDFは帳簿に接続すると表示できます"));
    try {
      openBlob(await api.blueReturnPdf(year, blue));
    } catch (e) {
      toast(T("PDFを取得できませんでした") + `: ${e instanceof Error ? e.message : e}`);
    }
  };

  const exportCsv = async (fmt: "freee" | "mf" | "yayoi") => {
    if (!live) return toast(T("CSV出力は帳簿に接続すると使えます"));
    try {
      saveBlob(await api.exportCsv(fmt, year), `tegaru_${fmt}_${year}.csv`);
    } catch (e) {
      toast(T("出力に失敗しました: {a}", { a: e instanceof Error ? e.message : e }));
    }
  };

  const income = pl.revenue - pl.expenses_total;
  const years = Array.from({ length: 4 }, (_, i) => thisYear - i);
  const today = new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold text-slate-600">{T("対象年分")}</span>
        {years.map((y) => (
          <button key={y} onClick={() => setYear(y)} aria-pressed={year === y}
            className={cx("rounded-full px-3 py-1 text-xs ring-1 ring-inset", year === y ? "bg-navy text-white ring-navy" : "text-slate-500 ring-slate-200 hover:bg-slate-50")}>
            {y}{T("年分")}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label={T("売上（収入）金額")} value={yen(pl.revenue)} tone="ok" />
        <Stat label={T("経費合計")} value={yen(pl.expenses_total)} />
        <Stat label={T("所得金額（青色控除前）")} value={yen(income)} />
        <Stat label={T("納める所得税（概算）")} value={it ? yen(it.total) : "—"} tone="warn" />
      </div>

      <div className="grid gap-3 lg:grid-cols-12">
        <Card title="青色申告決算書（損益計算書）" en="P/L" className="lg:col-span-5" right={<Btn onClick={blueReturnPdf}><FileText size={13} />{T("決算書PDF")}</Btn>}>
          <table className="w-full text-xs">
            <tbody className="divide-y divide-slate-100">
              <tr><td className="py-1.5 font-bold">{T("① 売上（収入）金額")}</td><td className="py-1.5 text-right font-mono tabular">{yen(pl.revenue)}</td></tr>
              {pl.expenses.map((e) => (
                <tr key={e.category}><td className="py-1 pl-4 text-slate-600">{e.category}</td><td className="py-1 text-right font-mono text-slate-600 tabular">{yen(e.amount)}</td></tr>
              ))}
              <tr><td className="py-1.5 font-bold">{T("㉜ 経費計")}</td><td className="py-1.5 text-right font-mono font-bold tabular">{yen(pl.expenses_total)}</td></tr>
              <tr><td className="py-1.5 font-bold text-navy">{T("㊸ 所得金額（青色申告特別控除前）")}</td><td className="py-1.5 text-right font-mono font-bold text-navy tabular">{yen(income)}</td></tr>
            </tbody>
          </table>
          <p className="text-[10px] text-slate-400">{T(pl.note)}</p>
        </Card>

        <Card title="所得税の概算" en="Income Tax" className="lg:col-span-4">
          <div className="grid grid-cols-2 gap-2">
            <Field label={T("青色申告特別控除")} className="col-span-2">
              <select id="tx-blue" value={blue} onChange={(e) => setBlue(Number(e.target.value))} className={selectCls}>
                {year >= 2027 && <option value={750_000}>{T("75万円（e-Tax＋優良な電子帳簿・届出）")}</option>}
                <option value={650_000}>{T("65万円（e-Tax＋複式簿記）")}</option>
                {year < 2027 && <option value={550_000}>{T("55万円")}</option>}
                <option value={100_000}>{T("10万円（簡易簿記）")}</option>
                <option value={0}>{T("白色申告")}</option>
              </select>
              {year >= 2027 && <span className="mt-1 block text-[10px] text-slate-400">{T("令和9年分以後: 55万円は廃止。75万円は e-Tax に加えて優良な電子帳簿等の要件と届出が必要です。")}</span>}
            </Field>
            <Field label={T("社会保険料控除")}><input id="tx-social" value={social} onChange={(e) => setSocial(e.target.value.replace(/\D/g, ""))} inputMode="numeric" className={inputCls + " text-right font-mono"} /></Field>
            <Field label={T("その他の所得控除")}><input id="tx-other" value={other} onChange={(e) => setOther(e.target.value.replace(/\D/g, ""))} inputMode="numeric" className={inputCls + " text-right font-mono"} /></Field>
          </div>
          {it ? (
            <dl className="space-y-1 border-t border-slate-100 pt-2 text-xs">
              <Row k={T("青色申告特別控除")} v={-it.blue_deduction} />
              <Row k={T("事業所得")} v={it.business_income} />
              <Row k={T("基礎控除")} v={-it.basic_deduction} />
              <Row k={T("課税所得金額")} v={it.taxable} bold />
              <Row k={T("所得税")} v={it.base_tax} />
              <Row k={T("復興特別所得税（2.1%）")} v={it.reconstruction} />
              <div className="flex justify-between border-t border-slate-200 pt-1 text-sm font-bold text-navy"><dt>{T("納める所得税")}</dt><dd className="font-mono tabular">{yen(it.total)}</dd></div>
            </dl>
          ) : (
            <p className="flex items-start gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-[11px] text-amber-800"><TriangleAlert size={13} className="mt-0.5 shrink-0" />{itMsg}</p>
          )}
          <p className="text-[10px] text-slate-400">{T("概算です。源泉徴収税額・予定納税・医療費控除などは含みません。")}</p>
        </Card>

        <Card title="消費税" en="Consumption Tax" className="lg:col-span-3">
          <Field label={T("課税方式")}>
            <select id="tx-method" value={method} onChange={(e) => setMethod(e.target.value as Method)} className={selectCls}>
              {(Object.keys(METHOD_LABEL) as Method[]).map((m) => <option key={m} value={m}>{T(METHOD_LABEL[m])}</option>)}
            </select>
          </Field>
          {method === "kani" && (
            <Field label={T("事業区分")}>
              <select id="tx-kani" value={kani} onChange={(e) => setKani(Number(e.target.value))} className={selectCls}>
                {Object.entries(KANI_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </Field>
          )}
          {ct ? (
            <dl className="space-y-1 text-xs">
              <Row k={T("売上税額")} v={ct.output} />
              <Row k={T("控除税額")} v={-ct.input} />
              <div className="flex justify-between border-t border-slate-200 pt-1 text-sm font-bold text-navy"><dt>{T("納付税額（概算）")}</dt><dd className="font-mono tabular">{yen(ct.payable)}</dd></div>
            </dl>
          ) : null}
          {ctMsg && <p className="text-[11px] text-slate-500">{ctMsg}</p>}
          <p className="text-[10px] text-slate-400">{T("登録番号のない仕入は 2026/10〜2028/9 の間 70% 控除（令和8年度改正）。")}</p>
        </Card>

        <Card title="会計ソフト用CSV" en="Export" className="lg:col-span-6">
          <p className="text-xs text-slate-500">{year}{T("年分の取引を、各会計ソフトの取込形式（Shift_JIS）で出力します。税理士への提出にも使えます。")}</p>
          <div className="flex flex-wrap gap-2">
            <Btn onClick={() => exportCsv("freee")}><Download size={13} />freee</Btn>
            <Btn onClick={() => exportCsv("mf")}><Download size={13} />{T("マネーフォワード")}</Btn>
            <Btn onClick={() => exportCsv("yayoi")}><Download size={13} />{T("弥生会計")}</Btn>
          </div>
          <p className="text-[10px] text-slate-400">{T("e-Tax 用の申告データ（xtx）出力は今後対応予定です。")}</p>
        </Card>

        <Card title="税務カレンダー" en="Filing Schedule" className="lg:col-span-6">
          <ul className="divide-y divide-dashed divide-slate-200 text-xs">
            {CALENDAR.map((c) => {
              const days = Math.ceil((new Date(c.d).getTime() - new Date(today).getTime()) / 86_400_000);
              return (
                <li key={c.d + c.t} className={cx("flex items-center gap-3 py-1.5", days < 0 && "text-slate-300 line-through")}>
                  <CalendarClock size={13} className="shrink-0 text-slate-400" />
                  <span className="w-20 font-mono tabular">{c.d.slice(5).replace("-", "/")}</span>
                  <span className="flex-1">{T(c.t)}</span>
                  {days >= 0 && <Badge tone={days <= 7 ? "bad" : days <= 30 ? "warn" : "info"} icon={false}>{T("あと")}{days}{T("日")}</Badge>}
                </li>
              );
            })}
          </ul>
        </Card>
      </div>
    </div>
  );
}

function Row({ k, v, bold }: { k: string; v: number; bold?: boolean }) {
  return (
    <div className={cx("flex justify-between", bold && "font-bold")}>
      <dt className="text-slate-500">{k}</dt>
      <dd className="font-mono tabular">{v < 0 ? `−${yen(-v)}` : yen(v)}</dd>
    </div>
  );
}
