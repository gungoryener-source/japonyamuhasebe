"use client";

/** 料金プラン (T-042b) — プラン一覧・今月の利用状況・アップグレード（Stripe Checkout）・期間末解約。 */
import { useEffect, useState } from "react";
import { Check, CircleCheck, CreditCard, Info, LoaderCircle, TriangleAlert, X } from "lucide-react";
import { api, ApiError, type ApiBillingStatus, type ApiPlan } from "../lib/api";
import { AppShell, useShell } from "../components/shell";
import { Badge, Btn, Card, cx, yen } from "../components/ui";
import { currentLang, T } from "../lib/i18n";

export default function BillingPage() {
  return (
    <AppShell title="料金プラン" en="Billing" sub="プラン・今月の利用状況・お支払い">
      <Billing />
    </AppShell>
  );
}

/** bot/billing.py PLANS の写し（デモ表示・サーバー未接続時）。価格は確定（Q-11 / T-055、月額・税抜）。 */
const DEMO_PLANS: ApiPlan[] = [
  { id: "free", name: "フリー", price_jpy: 0, receipts_per_month: 30, invoices_per_month: 3, placeholder: false, available: true },
  { id: "personal", name: "個人", price_jpy: 980, receipts_per_month: null, invoices_per_month: null, placeholder: false, available: false },
  { id: "business", name: "法人", price_jpy: 2980, receipts_per_month: null, invoices_per_month: null, placeholder: false, available: false },
];
const DEMO_STATUS: ApiBillingStatus = {
  plan: "free", plan_name: "フリー", limits: { receipts_per_month: 30, invoices_per_month: 3 },
  usage: { month: "", receipts: 18, invoices: 2 }, payments_enabled: false, limits_enforced: false, subscription: null,
};

const PLAN_NOTES: Record<ApiPlan["id"], string[]> = {
  free: ["LINE・WhatsApp で記帳", "インボイス対応の請求書", "消費税・確定申告のプレビュー"],
  personal: ["個人事業主向け", "確定申告の準備に"],
  business: ["小規模法人向け", "法人の決算準備に"],
};

const STATUS_LABEL: Record<string, string> = {
  active: "有効", trialing: "試用中", past_due: "お支払い確認中", canceled: "解約済み",
  incomplete: "手続き未完了", incomplete_expired: "手続き期限切れ", unpaid: "未払い",
};

const fmtDate = (iso: string) => (iso ? new Date(iso).toLocaleDateString("ja-JP", { timeZone: "Asia/Tokyo", year: "numeric", month: "long", day: "numeric" }) : "");

function Billing() {
  const { live, mode, toast, role } = useShell();
  const owner = role === "owner";
  const [plans, setPlans] = useState<ApiPlan[]>(DEMO_PLANS);
  const [st, setSt] = useState<ApiBillingStatus>(DEMO_STATUS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<"success" | "cancel" | null>(null);

  useEffect(() => {
    const r = new URLSearchParams(location.search).get("billing");
    if (r === "success" || r === "cancel") setResult(r);
  }, []);

  useEffect(() => {
    if (mode === "loading") return;
    if (!live) { setLoading(false); return; }
    Promise.all([api.billingPlans(), api.billingStatus()])
      .then(([p, s]) => { setPlans(p.plans); setSt(s); setError(null); })
      .catch((e) => setError(e instanceof ApiError && e.status === 404 ? T("サーバーが料金プランに未対応です（更新待ち）") : e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [mode, live]);

  const upgrade = async (plan: "personal" | "business") => {
    if (!live) return toast(T("デモ表示中です。ログインするとプランを変更できます"));
    setBusy(plan);
    try {
      const { url } = await api.checkout(plan);
      location.href = url;   // Stripe Checkout（決済後 /billing/?billing=success に戻る）
    } catch (e) {
      toast(e instanceof Error ? e.message : String(e));
      setBusy(null);
    }
  };

  const cancel = async () => {
    if (!live) return toast(T("デモ表示中です"));
    if (!confirm(T("有料プランを解約しますか？\n現在の請求期間の終了まではそのままご利用いただけます。データは削除されません。"))) return;
    setBusy("cancel");
    try {
      setSt(await api.cancelPlan());
      toast(T("解約を受け付けました（期間末に終了）"));
    } catch (e) {
      toast(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const sub = st.subscription;
  const paid = st.plan !== "free";
  const cancelScheduled = !!sub?.cancel_at_period_end && paid;

  return (
    <div className="space-y-3">
      {result === "success" && (
        <Banner tone="ok" onClose={() => setResult(null)}>
          {T("お申し込みありがとうございます。決済の確認後、数分以内にプランが切り替わります。")}
        </Banner>
      )}
      {result === "cancel" && (
        <Banner tone="warn" onClose={() => setResult(null)}>{T("お手続きはキャンセルされました。料金は発生していません。")}</Banner>
      )}
      {!st.payments_enabled && (
        <Banner tone="info">
          {T("オンライン決済は")}<strong className="mx-0.5">{T("準備中")}</strong>{T("です。現在はすべての機能を上限なしでご利用いただけます。")}
        </Banner>
      )}
      {error && <Banner tone="warn">{T("料金プランを読み込めませんでした（")}{error}）。</Banner>}

      <div className="grid gap-3 lg:grid-cols-3">
        <Card title="現在のプラン" en="Current Plan" right={<CreditCard size={16} className="text-mint" />}>
          {loading ? (
            <p className="flex items-center gap-2 text-xs text-slate-400"><LoaderCircle size={14} className="animate-spin" />{T("読み込み中…")}</p>
          ) : (
            <div className="space-y-2 text-xs">
              <p className="flex items-center gap-2">
                <span className="text-xl font-bold text-navy">{T(st.plan_name)}</span>
                {sub && paid && <Badge tone={sub.status === "active" || sub.status === "trialing" ? "ok" : "warn"}>{T(STATUS_LABEL[sub.status] ?? sub.status)}</Badge>}
                {!live && <Badge tone="muted" icon={false}>{T("デモ")}</Badge>}
              </p>
              {sub?.current_period_end && paid && (
                <p className="text-slate-500">
                  {cancelScheduled ? T("ご利用終了日") : T("次回更新日")}: <span className="font-mono tabular text-navy">{fmtDate(sub.current_period_end)}</span>
                </p>
              )}
              {cancelScheduled && (
                <p className="rounded-lg bg-amber-50 px-2 py-1.5 text-amber-800">{T("期間末に解約予定です。終了後はフリープランに戻り、データはそのまま残ります。")}</p>
              )}
              {paid && !cancelScheduled && owner && (
                <Btn kind="danger" onClick={cancel} disabled={busy !== null || !st.payments_enabled}>
                  {busy === "cancel" ? <LoaderCircle size={13} className="animate-spin" /> : null}{T("解約（期間末）")}
                </Btn>
              )}
            </div>
          )}
        </Card>

        <Card title="今月の利用状況" en="Usage" className="lg:col-span-2"
          right={<span className="font-mono text-[11px] text-slate-400 tabular">{st.usage.month || T("今月")}</span>}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Meter label={T("経費（レシート・手入力）")} used={st.usage.receipts} limit={st.limits.receipts_per_month} />
            <Meter label={T("請求書の発行")} used={st.usage.invoices} limit={st.limits.invoices_per_month} />
          </div>
          <p className="flex items-start gap-1.5 text-[11px] text-slate-400">
            <Info size={12} className="mt-0.5 shrink-0" />
            {st.limits_enforced
              ? T("毎月1日（日本時間）にリセットされます。銀行明細の取込と入金の記録は上限に含まれません。")
              : T("上限は決済開始後に適用されます。現在は上限なしでご利用いただけます。")}
          </p>
        </Card>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {plans.map((p) => {
          const current = p.id === st.plan;
          return (
            <section key={p.id}
              className={cx("flex flex-col gap-3 rounded-xl border bg-white p-4", current ? "border-mint ring-1 ring-mint" : "border-slate-200")}>
              <header className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-navy">{currentLang() === "ja" ? `${p.name}プラン` : `${T(p.name)} plan`}</h2>
                {current && <Badge tone="ok">{T("ご利用中")}</Badge>}
              </header>
              <p className="font-mono text-2xl font-semibold text-navy tabular">
                {p.price_jpy === 0 ? "¥0" : yen(p.price_jpy)}
                <span className="ml-1 font-sans text-[11px] font-normal text-slate-400">{T("/ 月（税抜）")}</span>
              </p>
              <ul className="flex-1 space-y-1 text-xs text-slate-600">
                <li className="flex gap-1.5"><Check size={13} className="mt-0.5 shrink-0 text-mint" />{T("経費")} {p.receipts_per_month == null ? T("無制限") : T("月{a}件まで", { a: p.receipts_per_month })}</li>
                <li className="flex gap-1.5"><Check size={13} className="mt-0.5 shrink-0 text-mint" />{T("請求書")} {p.invoices_per_month == null ? T("無制限") : T("月{a}件まで", { a: p.invoices_per_month })}</li>
                {PLAN_NOTES[p.id]?.map((n) => (
                  <li key={n} className="flex gap-1.5"><Check size={13} className="mt-0.5 shrink-0 text-mint" />{T(n)}</li>
                ))}
              </ul>
              {p.id === "free" ? (
                <p className="text-center text-[11px] text-slate-400">{current ? T("現在のプランです") : T("有料プランの解約後はこのプランになります")}</p>
              ) : current ? (
                <Btn kind="ghost" disabled>{T("ご利用中")}</Btn>
              ) : !owner ? (
                <Btn kind="ghost" disabled title={T("プランの変更は帳簿のオーナーのみ行えます")}>{T("オーナーのみ変更可")}</Btn>
              ) : !st.payments_enabled || !p.available ? (
                <Btn kind="ghost" disabled title={T("オンライン決済の開始までお待ちください")}>{T("準備中")}</Btn>
              ) : (
                <Btn kind="mint" onClick={() => upgrade(p.id as "personal" | "business")} disabled={busy !== null}>
                  {busy === p.id ? <LoaderCircle size={13} className="animate-spin" /> : null}
                  {paid ? T("このプランに変更") : T("アップグレード")}
                </Btn>
              )}
            </section>
          );
        })}
      </div>
      <p className="text-[11px] text-slate-400">
        {T("価格はすべて月額・税抜です。お支払いは Stripe（クレジットカード）で安全に処理され、カード情報は当サービスに保存されません。")}
        {" "}<a href="/legal/tokushoho/" className="underline-offset-2 hover:text-navy hover:underline">{T("特定商取引法に基づく表記")}</a>
        {" "}<a href="/legal/terms/" className="underline-offset-2 hover:text-navy hover:underline">{T("利用規約")}</a>
        {" "}<a href="/settings/" className="underline-offset-2 hover:text-navy hover:underline">{T("設定に戻る")}</a>
      </p>
    </div>
  );
}

function Meter({ label, used, limit }: { label: string; used: number; limit: number | null }) {
  const ratio = limit ? Math.min(used / limit, 1) : 0;
  const tone = limit == null ? "bg-mint" : ratio >= 1 ? "bg-rose-500" : ratio >= 0.8 ? "bg-amber-500" : "bg-mint";
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-slate-600">{label}</span>
        <span className="font-mono tabular text-navy">
          <strong className="text-base">{used.toLocaleString("ja-JP")}</strong>
          <span className="text-slate-400"> / {limit == null ? T("無制限") : T("{a}件", { a: limit })}</span>
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label={label}
        aria-valuenow={used} aria-valuemin={0} aria-valuemax={limit ?? undefined}>
        <div className={cx("h-full rounded-full transition-all", tone)} style={{ width: limit == null ? "100%" : `${ratio * 100}%`, opacity: limit == null ? 0.25 : 1 }} />
      </div>
      {limit != null && used >= limit && <p className="text-[11px] text-rose-600">{T("今月の上限に達しました。アップグレードすると引き続き記録できます。")}</p>}
    </div>
  );
}

function Banner({ tone, children, onClose }: { tone: "ok" | "warn" | "info"; children: React.ReactNode; onClose?: () => void }) {
  const cls = { ok: "bg-mint-50 text-mint-700", warn: "bg-amber-50 text-amber-800", info: "bg-slate-100 text-navy" }[tone];
  const Icon = tone === "ok" ? CircleCheck : tone === "warn" ? TriangleAlert : Info;
  return (
    <div className={cx("flex items-start gap-2 rounded-lg px-3 py-2 text-xs", cls)} role="status">
      <Icon size={14} className="mt-0.5 shrink-0" />
      <p className="flex-1">{children}</p>
      {onClose && <button onClick={onClose} aria-label={T("閉じる")} className="opacity-60 hover:opacity-100"><X size={14} /></button>}
    </div>
  );
}
