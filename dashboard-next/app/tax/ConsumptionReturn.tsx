"use client";

/** 消費税申告書（第一表・第二表相当）— 国税／地方消費税を分け、各数値の計算式と根拠を表示する（T-071b）。 */
import { useEffect, useState } from "react";
import { TriangleAlert } from "lucide-react";
import { api, type ApiConsumptionReturn, type ApiReturnLine } from "../lib/api";
import { methodUnavailable, type Method } from "../lib/tax";
import EXAMPLE from "../lib/consumption-return-example.json";
import { Badge, Card, cx, Field, selectCls, Stat, yen } from "../components/ui";
import { T } from "../lib/i18n";

const DEMO = EXAMPLE as unknown as { year: number; results: Record<string, ApiConsumptionReturn> };

/** 行ラベル（サーバーは日本語を返す）。キーから組み立てて ja/tr/en に切り替える。 */
export function lineLabel(l: ApiReturnLine, method: string): string {
  const [head, rate, ratio] = l.key.split(".");
  const r = rate === "10" ? "7.8%" : rate === "8" ? "6.24%" : "";
  switch (head) {
    case "base": return rate ? T("課税標準額（{r}適用分）", { r }) : T("課税標準額");
    case "output": return rate ? T("消費税額（{r}適用分）", { r }) : T("消費税額");
    case "input":
      return ratio === "100" ? T("控除対象仕入税額（{r}適用分）", { r })
        : T("控除対象仕入税額（適格請求書なし・控除{p}%）（{r}適用分）", { p: ratio, r });
    case "credit": {
      if (method === "niwari") return T("特別控除税額（2割特例）");
      if (method === "sanwari") return T("特別控除税額（3割特例）");
      const m = l.label.match(/第(\d)種 みなし仕入率(\d+)%/);
      return m ? T("控除対象仕入税額（第{n}種 みなし仕入率{p}%）", { n: m[1], p: m[2] }) : T("控除対象仕入税額");
    }
    case "national_payable": return T("差引税額（国税）");
    case "national_refund": return T("控除不足還付税額（国税）");
    case "local_payable": return T("譲渡割額（地方消費税・納税額）");
    case "local_refund": return T("譲渡割額（地方消費税・還付額）");
    case "total": return T("納付（又は還付）税額の合計");
    default: return l.label;
  }
}

const EMPHASIS = new Set(["national_payable", "national_refund", "local_payable", "local_refund", "total"]);

export default function ConsumptionReturn({ year, method, kani, live }: { year: number; method: Method; kani: number; live: boolean }) {
  const [calc, setCalc] = useState<"warimodoshi" | "ledger">("warimodoshi");
  const [res, setRes] = useState<ApiConsumptionReturn | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    const unavailable = methodUnavailable(method, { individual: true, taxYear: year, kaniType: kani });
    if (unavailable) { setRes(null); setMsg(unavailable); return; }
    if (!live) {
      const r = DEMO.results[method];
      setRes(r ?? null);
      setMsg(r ? T("デモ: {a}年分の例", { a: DEMO.year }) : T("この課税方式のデモは用意していません"));
      return;
    }
    let off = false;
    api.consumptionReturn(year, method, method === "kani" ? kani : undefined, calc)
      .then((r) => { if (!off) { setRes(r); setMsg(null); } })
      .catch((e) => { if (!off) { setRes(null); setMsg(e instanceof Error ? e.message : String(e)); } });
    return () => { off = true; };
  }, [live, year, method, kani, calc]);

  const refund = res ? res.total_payable < 0 : false;
  return (
    <Card title="消費税申告書（国税・地方消費税）" en="Consumption Tax Return" className="lg:col-span-12"
      right={res && res.unverified.length > 0 ? <Badge tone="warn">{T("未検証の項目あり")}</Badge> : undefined}>
      {method === "honsoku" && live && (
        <Field label={T("仕入税額の計算方法")} className="max-w-xs">
          <select id="cr-calc" value={calc} onChange={(e) => setCalc(e.target.value as "warimodoshi" | "ledger")} className={selectCls}>
            <option value="warimodoshi">{T("割戻し計算（特例）")}</option>
            <option value="ledger">{T("帳簿積上げ計算")}</option>
          </select>
        </Field>
      )}
      {msg && <p className="text-[11px] text-slate-500">{msg}</p>}
      {res && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label={T("消費税額（国税）")} value={yen(res.output_tax)} />
            <Stat label={T("控除税額")} value={yen(res.credit)} />
            <Stat label={refund ? T("還付税額（国税＋地方）") : T("納付税額（国税＋地方）")} value={yen(Math.abs(res.total_payable))} tone={refund ? "ok" : "warn"} />
            <Stat label={T("うち地方消費税")} value={yen(res.local_payable || res.local_refund)} />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="border-b border-slate-200 text-left text-[10px] text-slate-400">
                <th className="py-1 font-normal">{T("項目")}</th><th className="py-1 font-normal">{T("計算の根拠")}</th><th className="py-1 text-right font-normal">{T("金額")}</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {res.lines.map((l) => (
                  <tr key={l.key} className={cx(EMPHASIS.has(l.key) && "bg-slate-50 font-bold text-navy")}>
                    <td className="py-1.5 pr-3">{lineLabel(l, res.method)}</td>
                    <td className="py-1.5 pr-3 font-mono text-[10px] font-normal text-slate-400">
                      {l.formula}
                      <span className="ml-2 text-slate-300">{l.rule}</span>
                      {!l.verified && <span className="ml-2 text-amber-600">{T("未検証")}</span>}
                    </td>
                    <td className="py-1.5 text-right font-mono tabular">{yen(l.value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(res.transitional_over_cap?.length ?? 0) > 0 && (
            <p className="flex items-start gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-[11px] text-amber-800">
              <TriangleAlert size={13} className="mt-0.5 shrink-0" />
              {T("一の免税事業者等からの仕入れが経過措置の上限を超えています: {a}", { a: res.transitional_over_cap!.map((o) => o.seller).join("、") })}
            </p>
          )}
          <ul className="space-y-1">
            {res.warnings.map((w) => (
              <li key={w.code} className={cx("flex items-start gap-1.5 text-[11px]", w.code === "disclaimer" ? "text-slate-400" : "text-amber-800")}>
                <TriangleAlert size={12} className="mt-0.5 shrink-0" />{T(w.message)}
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}
