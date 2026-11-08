"use client";

/**
 * Q-16: şirket (事業所) fiyatlandırma ayarları — yönetici ekranı. ADMIN_KEY ile açılır (bu sekmede saklanır).
 * Varsayılan: kapalı = ek şirket ücretsiz ve sınırsız. Kural kodda sabit değil; buradan değişir.
 */
import { useEffect, useState } from "react";
import { KeyRound, LoaderCircle, Save, ShieldCheck } from "lucide-react";
import { API_BASE } from "../../lib/api";
import { Btn, Card, Field, inputCls } from "../../components/ui";
import { T } from "../../lib/i18n";

type Cfg = { enabled: boolean; included: Record<"free" | "personal" | "business", number>; extra_price_jpy: number };
const KEY = "jsaas.adminKey";
const PLAN_LABEL = { free: "フリー", personal: "個人", business: "法人" } as const;

async function adminFetch(key: string, method: "GET" | "PUT", body?: Cfg) {
  const r = await fetch(`${API_BASE}/api/v1/admin/pricing`, {
    method, headers: { "X-Admin-Key": key, "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(r.status === 401 ? T("管理キーが正しくありません") : (await r.json().catch(() => ({}))).detail ?? r.statusText);
  return (await r.json()).companies as Cfg;
}

export default function AdminPricing() {
  const [key, setKey] = useState("");
  const [cfg, setCfg] = useState<Cfg | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = async (k: string) => {
    setBusy(true); setMsg(null);
    try {
      setCfg(await adminFetch(k, "GET"));
      try { sessionStorage.setItem(KEY, k); } catch { /* yok say */ }
    } catch (e) { setCfg(null); setMsg({ ok: false, text: e instanceof Error ? e.message : String(e) }); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    try { const k = sessionStorage.getItem(KEY); if (k) { setKey(k); load(k); } } catch { /* yok say */ }
  }, []);

  const save = async () => {
    if (!cfg) return;
    setBusy(true); setMsg(null);
    try { setCfg(await adminFetch(key, "PUT", cfg)); setMsg({ ok: true, text: T("保存しました") }); }
    catch (e) { setMsg({ ok: false, text: e instanceof Error ? e.message : String(e) }); }
    finally { setBusy(false); }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-4 bg-[#F9FAFB] px-4 py-10">
      <h1 className="flex items-center gap-2 text-lg font-bold text-navy"><ShieldCheck size={20} className="text-mint" />{T("料金設定（管理者）")}</h1>
      <p className="text-xs text-slate-500">{T("複数の事業所の料金ルールです。オフの間は、事業所の追加は無料・上限なしです。")}</p>

      {!cfg && (
        <Card title="管理キー" en="Admin key">
          <form onSubmit={(e) => { e.preventDefault(); load(key); }} className="flex items-end gap-2">
            <Field label={T("ADMIN_KEY（Render の環境変数）")} className="flex-1">
              <input type="password" autoComplete="off" className={inputCls} value={key} onChange={(e) => setKey(e.target.value)} />
            </Field>
            <Btn kind="primary" type="submit" disabled={!key || busy}>{busy ? <LoaderCircle size={14} className="animate-spin" /> : <KeyRound size={14} />}{T("開く")}</Btn>
          </form>
        </Card>
      )}

      {cfg && (
        <Card title="事業所の料金" en="Company pricing">
          <label className="flex items-center gap-2 text-sm font-bold text-navy">
            <input type="checkbox" checked={cfg.enabled} onChange={(e) => setCfg({ ...cfg, enabled: e.target.checked })} />
            {T("料金ルールを有効にする")}
          </label>
          <p className={"rounded-lg p-2 text-xs " + (cfg.enabled ? "bg-amber-50 text-amber-700" : "bg-mint/10 text-mint-700")}>
            {cfg.enabled ? T("有効: プランに含まれる数を超える事業所には追加料金がかかります（追加料金が0円なら、それ以上は追加できません）。")
              : T("無効: 事業所の追加は無料・上限なし（現在の設定）。")}
          </p>
          <fieldset disabled={!cfg.enabled} className="grid grid-cols-3 gap-2 disabled:opacity-50">
            {(["free", "personal", "business"] as const).map((p) => (
              <Field key={p} label={T("{a}プランに含む事業所数", { a: T(PLAN_LABEL[p]) })}>
                <input type="number" min={1} max={1000} className={inputCls + " text-right"} value={cfg.included[p]}
                  onChange={(e) => setCfg({ ...cfg, included: { ...cfg.included, [p]: Math.max(1, Number(e.target.value) || 1) } })} />
              </Field>))}
            <Field label={T("追加1事業所あたりの月額（円・税抜）")} className="col-span-3">
              <input type="number" min={0} max={1000000} className={inputCls + " text-right"} value={cfg.extra_price_jpy}
                onChange={(e) => setCfg({ ...cfg, extra_price_jpy: Math.max(0, Number(e.target.value) || 0) })} />
            </Field>
          </fieldset>
          <p className="text-[11px] text-slate-400">{T("注: 追加料金の Stripe での自動請求はまだありません。画面と利用者への表示のみです。")}</p>
          <div className="flex items-center justify-between gap-2">
            {msg ? <span className={"text-xs " + (msg.ok ? "text-mint-700" : "text-red-600")}>{msg.text}</span> : <span />}
            <Btn kind="primary" onClick={save} disabled={busy}>{busy ? <LoaderCircle size={14} className="animate-spin" /> : <Save size={14} />}{T("保存")}</Btn>
          </div>
        </Card>
      )}
      {!cfg && msg && <p className="text-xs text-red-600">{msg.text}</p>}
    </main>
  );
}
