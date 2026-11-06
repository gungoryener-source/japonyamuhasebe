"use client";

/** 設定 — 事業者情報（インボイス登録番号）・連携チャネルの状態・接続管理 */
import { useEffect, useState } from "react";
import { Copy, CreditCard, KeyRound, LogOut, MessageCircle, ScanText, ShieldCheck } from "lucide-react";
import { API_BASE, api, setToken, type ApiChannels } from "../lib/api";
import { AppShell, useShell } from "../components/shell";
import { Badge, Btn, Card, Field, inputCls, registrationOk } from "../components/ui";

export default function SettingsPage() {
  return (
    <AppShell title="設定" en="Settings" sub="事業者情報・LINE / WhatsApp 連携・接続">
      <Settings />
    </AppShell>
  );
}

const DEMO_CH: ApiChannels = {
  line: { configured: false, webhook: "/callback", linked: false },
  whatsapp: { configured: false, webhook: "/whatsapp" },
  ocr: { engine: "auto", tesseract: true, ai_fallback: false },
  categories: [],
};

function Settings() {
  const { live, mode, company, toast } = useShell();
  const [name, setName] = useState("");
  const [reg, setReg] = useState("");
  const [individual, setIndividual] = useState(true);
  const [busy, setBusy] = useState(false);
  const [ch, setCh] = useState<ApiChannels>(DEMO_CH);

  useEffect(() => {
    if (mode === "loading") return;
    if (!live) { setName(company.name); setReg(company.reg); return; }
    api.profile().then((p) => { setName(p.business_name); setReg(p.registration_no); setIndividual(!!p.individual); }).catch(() => {});
    api.channels().then(setCh).catch(() => {});
  }, [mode, live, company.name, company.reg]);

  const regValid = !reg || registrationOk(reg);
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reg && !/^T\d{13}$/.test(reg)) return toast("登録番号は T + 13桁 で入力してください");
    if (!live) return toast("保存しました（デモ）");
    setBusy(true);
    try {
      await api.putProfile({ business_name: name.trim(), registration_no: reg, individual });
      toast("事業者情報を保存しました");
    } catch (err) {
      toast(`保存に失敗しました: ${err instanceof Error ? err.message : err}`);
    } finally {
      setBusy(false);
    }
  };

  const copy = async (text: string) => {
    try { await navigator.clipboard.writeText(text); toast("コピーしました"); } catch { toast(text); }
  };

  const disconnect = async () => {
    try { if (live) await api.revoke(); } catch { /* token zaten geçersiz olabilir */ }
    setToken(null);
    location.href = "/connect/";
  };

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Card title="事業者情報" en="Business Profile" right={<ShieldCheck size={16} className="text-mint" />}>
        <form onSubmit={save} className="space-y-3">
          <Field label="事業者名（屋号・会社名）">
            <input id="st-name" value={name} onChange={(e) => setName(e.target.value)} className={inputCls} placeholder="合同会社〇〇 / 〇〇デザイン事務所" />
          </Field>
          <Field label="適格請求書発行事業者 登録番号">
            <input id="st-reg" value={reg} onChange={(e) => setReg(e.target.value.toUpperCase().replace(/[^T\d]/g, ""))} className={inputCls + " font-mono"} placeholder="T1234567890123" />
            {reg && (regValid ? <span className="text-[10px] text-mint-700">形式・チェックデジット OK</span>
              : <span className="text-[10px] text-amber-600">形式またはチェックデジットが正しくありません（個人事業者の番号は国税庁の公表サイトで確認してください）</span>)}
          </Field>
          <fieldset className="space-y-1 text-xs">
            <legend className="font-bold text-slate-600">事業形態</legend>
            <div className="flex gap-2">
              {[{ v: true, l: "個人事業主" }, { v: false, l: "法人" }].map((o) => (
                <button key={o.l} type="button" onClick={() => setIndividual(o.v)} aria-pressed={individual === o.v}
                  className={"flex-1 rounded-lg border px-3 py-2 text-left " + (individual === o.v ? "border-navy bg-slate-50 font-bold text-navy" : "border-slate-200 text-slate-500")}>
                  {o.l}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-slate-400">3割特例（2027・2028年分）は個人事業主のみ利用できます。</p>
          </fieldset>
          <Btn type="submit" kind="primary" disabled={busy}>{busy ? "保存中…" : "保存する"}</Btn>
        </form>
      </Card>

      <Card title="連携チャネル" en="Channels" right={<MessageCircle size={16} className="text-mint" />}>
        <ul className="divide-y divide-slate-100 text-xs">
          <li className="space-y-1 py-2 first:pt-0">
            <div className="flex items-center gap-2"><span className="font-bold text-navy">LINE 公式アカウント</span>
              {ch.line.configured ? <Badge tone="ok">接続済</Badge> : <Badge tone="warn">未設定</Badge>}</div>
            <p className="text-slate-500">レシートの写真や「タクシー 2300」を送るだけで記帳。「パネル」と送るとこの画面への接続コードが届きます。</p>
            <WebhookRow url={`${API_BASE}${ch.line.webhook}`} onCopy={copy} />
          </li>
          <li className="space-y-1 py-2">
            <div className="flex items-center gap-2"><span className="font-bold text-navy">WhatsApp Business</span>
              {ch.whatsapp.configured ? <Badge tone="ok">接続済</Badge> : <Badge tone="muted">未設定</Badge>}</div>
            <p className="text-slate-500">海外のお客様向け。LINE と同じ操作で記帳できます。</p>
            <WebhookRow url={`${API_BASE}${ch.whatsapp.webhook}`} onCopy={copy} />
          </li>
          <li className="space-y-1 py-2 last:pb-0">
            <div className="flex items-center gap-2"><ScanText size={14} className="text-slate-400" /><span className="font-bold text-navy">領収書の読み取り</span>
              {ch.ocr.tesseract ? <Badge tone="ok">OCR 稼働中</Badge> : <Badge tone="warn">OCR 未導入</Badge>}</div>
            <p className="text-slate-500">
              方式: {ch.ocr.engine === "claude" ? "AI" : "OCR＋ルール（AI不使用）"}
              {ch.ocr.engine === "auto" && (ch.ocr.ai_fallback ? "・読み取れない場合のみAIで補完" : "・AI補完なし")}
            </p>
          </li>
        </ul>
      </Card>

      <Card title="料金プラン" en="Billing" right={<CreditCard size={16} className="text-mint" />} className="lg:col-span-2">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <span className="text-slate-500">現在のプラン・今月の利用状況の確認、アップグレードや解約はこちらから。</span>
          <a href="/billing/" className="ml-auto"><Btn kind="ghost">料金プランを見る</Btn></a>
        </div>
      </Card>

      <Card title="接続" en="Connection" right={<KeyRound size={16} className="text-slate-400" />} className="lg:col-span-2">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {live ? (
            <>
              <Badge tone="ok">帳簿に接続中</Badge>
              <span className="text-slate-500">{company.name}</span>
              <Btn kind="danger" onClick={disconnect} className="ml-auto"><LogOut size={13} />この端末の接続を解除</Btn>
            </>
          ) : (
            <>
              <Badge tone="warn">デモ表示中</Badge>
              <span className="text-slate-500">LINE で「パネル」と送ると、あなたの帳簿に接続するリンクが届きます。</span>
              <a href="/connect/" className="ml-auto"><Btn kind="primary">接続コードを入力</Btn></a>
            </>
          )}
        </div>
      </Card>
    </div>
  );
}

function WebhookRow({ url, onCopy }: { url: string; onCopy: (t: string) => void }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-2 py-1">
      <span className="text-[10px] text-slate-400">Webhook</span>
      <code className="min-w-0 flex-1 truncate font-mono text-[11px] text-slate-600">{url}</code>
      <button onClick={() => onCopy(url)} className="text-slate-400 hover:text-navy" aria-label="コピー"><Copy size={13} /></button>
    </div>
  );
}
