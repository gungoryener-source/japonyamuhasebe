"use client";

/** レシートの読み取り方法（OCR / AI / 自動）と AI の概算料金・今月の利用額。 */
import { useEffect, useState } from "react";
import { Bot, LoaderCircle } from "lucide-react";
import { api, type ApiAiSettings } from "../lib/api";
import { useShell } from "../components/shell";
import { Badge, Card } from "../components/ui";
import { T } from "../lib/i18n";

const DEMO: ApiAiSettings = {
  receipt_reader: "", server_default: "tesseract", ai_available: true,
  per_unit: { receipt: { jpy: 1.3, basis: "estimate", samples: 0 }, slip: { jpy: 2.6, basis: "estimate", samples: 0 }, passbook: { jpy: 2.8, basis: "estimate", samples: 0 } },
  month: { by_kind: { slip: { count: 12, jpy: 31.2 } }, total_jpy: 31.2 },
  prices: { input_usd_per_mtok: 2, output_usd_per_mtok: 10, usd_jpy: 155, model: "claude-sonnet-5-5" },
};

const OPTIONS: { v: "ocr" | "ai" | "auto"; title: string; desc: string }[] = [
  { v: "ocr", title: "OCR（無料）", desc: "印字のレシート向け。料金はかかりません。かすれ・手書きは読めないことがあります。" },
  { v: "auto", title: "自動（おすすめ）", desc: "まず OCR で読み、読めなかったときだけ AI を使います。料金は読めなかった分だけ。" },
  { v: "ai", title: "すべて AI", desc: "すべてのレシートを AI で読みます。精度が高く、手書き・かすれにも強い。" },
];

export function AiReadingCard() {
  const { live, toast, canEdit } = useShell();
  const [s, setS] = useState<ApiAiSettings>(DEMO);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!live) { setS(DEMO); return; }
    api.aiSettings().then(setS).catch(() => undefined);
  }, [live]);

  const current = s.receipt_reader || (s.server_default === "claude" ? "ai" : s.server_default === "auto" ? "auto" : "ocr");
  const per = s.per_unit.receipt.jpy;
  const yen = (n: number) => `¥${n.toLocaleString("ja-JP", { maximumFractionDigits: 1 })}`;

  const choose = async (v: "ocr" | "ai" | "auto") => {
    if (!canEdit) return;
    if (!live) { setS({ ...s, receipt_reader: v }); return toast(T("保存しました（デモ）")); }
    setBusy(true);
    try {
      setS(await api.aiSettingsPut(v));
      toast(T("読み取り方法を変更しました"));
    } catch (e) {
      toast(T("失敗しました: {a}", { a: e instanceof Error ? e.message : String(e) }));
    } finally { setBusy(false); }
  };

  const estimate = (v: string) => v === "ocr" ? T("無料") : v === "ai" ? T("約 {a} / 枚", { a: yen(per) }) : T("読めなかった分だけ 約 {a} / 枚", { a: yen(per) });

  return (
    <Card title="レシートの読み取り方法" en="Receipt Reading" right={<Bot size={16} className="text-mint" />}>
      <div className="grid gap-2 md:grid-cols-3">
        {OPTIONS.map((o) => {
          const disabled = !canEdit || busy || (o.v !== "ocr" && live && !s.ai_available);
          return (
            <button key={o.v} disabled={disabled} onClick={() => choose(o.v)}
              className={"flex flex-col gap-1 rounded-xl border p-3 text-left text-xs transition " +
                (current === o.v ? "border-mint bg-mint/10" : "border-slate-200 hover:border-slate-300") + (disabled ? " cursor-not-allowed opacity-60" : "")}>
              <span className="flex items-center justify-between gap-2 font-bold text-navy">{T(o.title)}
                {current === o.v && (busy ? <LoaderCircle size={13} className="animate-spin" /> : <Badge tone="ok">{T("選択中")}</Badge>)}</span>
              <span className="text-slate-500">{T(o.desc)}</span>
              <span className="mt-1 font-bold tabular-nums text-navy">{estimate(o.v)}</span>
            </button>);
        })}
      </div>
      {live && !s.ai_available && <p className="text-[11px] text-amber-600">{T("AI はサーバーに ANTHROPIC_API_KEY が設定されると選べます。")}</p>}

      <div className="grid gap-3 rounded-lg bg-slate-50 p-3 text-xs sm:grid-cols-2">
        <div>
          <p className="mb-1 font-bold text-navy">{T("AI の概算料金（1枚・1ページあたり）")}</p>
          <ul className="flex flex-col gap-0.5 tabular-nums text-slate-600">
            <li>{T("レシート")}: {yen(s.per_unit.receipt.jpy)}</li>
            <li>{T("仕切書（手書き）")}: {yen(s.per_unit.slip.jpy)}</li>
            <li>{T("通帳（1ページ）")}: {yen(s.per_unit.passbook.jpy)}</li>
          </ul>
          <p className="mt-1 text-[10px] text-slate-400">
            {s.per_unit.receipt.basis === "measured" ? T("直近の実績の平均です。") : T("想定値です（実績が5件たまると実績平均に切り替わります）。")}
            {" "}{T("{m}・入力 ${a} / 出力 ${b}（100万トークン）・1ドル {c}円", { m: s.prices.model, a: s.prices.input_usd_per_mtok, b: s.prices.output_usd_per_mtok, c: s.prices.usd_jpy })}
          </p>
        </div>
        <div>
          <p className="mb-1 font-bold text-navy">{T("今月の AI 利用")}</p>
          <p className="text-lg font-bold tabular-nums text-navy">{yen(s.month.total_jpy)}</p>
          <ul className="text-slate-500 tabular-nums">
            {Object.entries(s.month.by_kind).map(([k, v]) => (
              <li key={k}>{T(k === "receipt" ? "レシート" : k === "slip" ? "仕切書（手書き）" : "通帳（1ページ）")}: {v.count}{T("件")} · {yen(v.jpy)}</li>))}
            {!Object.keys(s.month.by_kind).length && <li>{T("まだ利用はありません")}</li>}
          </ul>
          <p className="mt-1 text-[10px] text-slate-400">{T("概算です。実際の請求は Anthropic のコンソールで確認してください。")}</p>
        </div>
      </div>
    </Card>
  );
}
