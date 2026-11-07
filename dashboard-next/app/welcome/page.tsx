"use client";

/**
 * /welcome — kayıt sonrası 3 adımlı kurulum sihirbazı (T-044b).
 * 1 事業者情報 (PUT /profile) → 2 LINE 連携 (POST /auth/link-line, 「あとで」) → 3 最初の領収書 (経費精算 veya LINE) → ホーム.
 * Her adım atlanabilir; adım `?step=` ile URL'de tutulur. Demo (token yok): statik önizleme, API çağrısı yok.
 * Ekip üyesi (accountant / viewer) bu sayfaya gelirse ホーム'a yönlendirilir.
 */
import { useEffect, useState } from "react";
import { Check, ChevronRight, KeyRound, LoaderCircle, MessageCircle, Receipt, ShieldCheck, Sparkles } from "lucide-react";
import { api, ApiError, setToken } from "../lib/api";
import { useConnection } from "../components/shell";
import { cx, Field, inputCls, registrationOk } from "../components/ui";
import { Notice } from "../components/auth";
import { LangSwitcher, useT } from "../components/lang";
import { LegalLinks } from "../components/legal";
import { LINE_ADD_URL } from "../lib/lp";
import {
  BUSINESS_NAME_MAX, nextStep, normalizeReg, parseStep, profileAfterLink, profileError, WELCOME_STEPS, wizardMode,
  type ProfileDraft, type Step,
} from "../lib/welcome";

const HOME = "/";

export default function WelcomePage() {
  const t = useT();
  const { mode, role } = useConnection();
  const view = wizardMode(mode, role);
  const demo = view === "demo";
  const [step, setStep] = useState<Step>(1);
  const [draft, setDraft] = useState<ProfileDraft | null>(null);

  useEffect(() => { setStep(parseStep(new URLSearchParams(location.search).get("step"))); }, []);
  useEffect(() => { if (view === "home") location.replace(HOME); }, [view]);

  const go = (s: Step | null) => {
    if (s === null) { location.href = HOME; return; }
    setStep(s);
    history.replaceState(null, "", `/welcome/?step=${s}`);
  };
  const next = () => go(nextStep(step));

  if (view === "loading" || view === "home")
    return (
      <main className="grid min-h-screen place-items-center bg-[#F9FAFB]">
        <LoaderCircle size={20} className="animate-spin text-slate-400" />
      </main>
    );

  return (
    <main className="min-h-screen bg-[#F9FAFB] px-4 py-8">
      <div className="mx-auto w-full max-w-lg space-y-4">
        <div className="flex items-center gap-2 text-navy">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-mint text-xs font-black text-navy-900">J</span>
          <span className="text-sm font-bold">{t("J-SaaS 会計")}</span>
          <span className="ml-auto"><LangSwitcher compact /></span>
        </div>

        <div>
          <h1 className="flex items-center gap-2 text-lg font-bold text-navy"><Sparkles size={18} className="text-mint" />{t("ようこそ！かんたん初期設定")}</h1>
          <p className="text-xs text-slate-500">{t("3つのステップで使い始められます。どのステップも「あとで」でスキップできます。")}</p>
        </div>

        {demo && (
          <Notice tone="warn">
            {t("デモ表示です。入力内容は保存されません。")}{" "}
            <a href="/signup/" className="font-bold underline">{t("アカウント登録")}</a>
          </Notice>
        )}

        <Stepper step={step} onPick={demo ? go : undefined} />

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          {step === 1 && <ProfileStep demo={demo} onDone={(d) => { setDraft(d); next(); }} onSkip={next} />}
          {step === 2 && <LineStep demo={demo} draft={draft} onDone={next} onSkip={next} />}
          {step === 3 && <ReceiptStep onDone={() => go(null)} />}
        </section>

        <div className="flex items-center justify-between text-[11px] text-slate-400">
          {step > 1 ? <button onClick={() => go((step - 1) as Step)} className="hover:text-navy">← {t("戻る")}</button> : <span />}
          <a href={HOME} className="hover:text-navy">{t("初期設定をスキップしてホームへ")}</a>
        </div>
        <LegalLinks className="text-[10px] text-slate-400" />
      </div>
    </main>
  );
}

function Stepper({ step, onPick }: { step: Step; onPick?: (s: Step) => void }) {
  const t = useT();
  return (
    <ol className="grid grid-cols-3 gap-2" aria-label={t("進行状況")}>
      {WELCOME_STEPS.map((s, i) => {
        const n = (i + 1) as Step;
        const state = n < step ? "done" : n === step ? "now" : "todo";
        const inner = (
          <>
            <span className={cx("grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-bold tabular-nums",
              state === "done" ? "bg-mint text-white" : state === "now" ? "bg-navy text-white" : "bg-slate-100 text-slate-400")}>
              {state === "done" ? <Check size={13} /> : n}
            </span>
            <span className="min-w-0 text-left leading-tight">
              <span className={cx("block truncate text-[11px] font-bold", state === "todo" ? "text-slate-400" : "text-navy")}>{t(s.ja)}</span>
              <span className="block text-[9px] text-slate-400">{s.en}</span>
            </span>
          </>
        );
        const cls = cx("flex items-center gap-2 rounded-lg border px-2 py-1.5",
          state === "now" ? "border-navy bg-white" : "border-slate-200 bg-white/60");
        return (
          <li key={s.ja} aria-current={state === "now" ? "step" : undefined}>
            {onPick ? <button type="button" onClick={() => onPick(n)} className={cls + " w-full"}>{inner}</button> : <div className={cls}>{inner}</div>}
          </li>
        );
      })}
    </ol>
  );
}

function StepHead({ icon, title, sub }: { icon: React.ReactNode; title: string; sub: string }) {
  return (
    <div className="mb-4 flex items-center gap-2.5">
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-navy text-mint">{icon}</div>
      <div className="min-w-0">
        <h2 className="text-sm font-bold text-navy">{title}</h2>
        <p className="text-[11px] text-slate-400">{sub}</p>
      </div>
    </div>
  );
}

function Actions({ busy, primary, onSkip, skipLabel }: { busy?: boolean; primary: React.ReactNode; onSkip?: () => void; skipLabel?: string }) {
  const t = useT();
  return (
    <div className="flex items-center gap-3 pt-1">
      {onSkip && <button type="button" onClick={onSkip} className="text-xs text-slate-500 hover:text-navy">{skipLabel ?? t("あとで")}</button>}
      <button type="submit" disabled={busy}
        className="ml-auto flex h-10 items-center gap-1.5 rounded-lg bg-navy px-4 text-sm font-bold text-white hover:bg-navy-700 disabled:opacity-60">
        {busy && <LoaderCircle size={15} className="animate-spin" />}{primary}<ChevronRight size={15} />
      </button>
    </div>
  );
}

/* ---------- 1. 事業者情報 ---------- */
function ProfileStep({ demo, onDone, onSkip }: { demo: boolean; onDone: (d: ProfileDraft) => void; onSkip: () => void }) {
  const t = useT();
  const [name, setName] = useState("");
  const [reg, setReg] = useState("");
  const [individual, setIndividual] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (demo) return;
    api.profile().then((p) => { setName(p.business_name); setReg(p.registration_no); setIndividual(p.individual !== 0); }).catch(() => {});
  }, [demo]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = profileError(name, reg);
    if (err) { setError(t(err)); return; }
    const d = { business_name: name.trim(), registration_no: reg, individual };
    if (demo) { onDone(d); return; }
    setBusy(true);
    setError(null);
    try {
      await api.putProfile(d);
      onDone(d);
    } catch (e2) {
      setError(t("保存に失敗しました: {e}", { e: e2 instanceof Error ? e2.message : String(e2) }));
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-3">
      <StepHead icon={<ShieldCheck size={18} />} title={t("事業者情報")} sub={t("請求書や帳簿に表示されます。あとから「設定」で変更できます。")} />
      <Field label={t("事業者名（屋号・会社名）")}>
        <input id="wz-name" value={name} maxLength={BUSINESS_NAME_MAX} onChange={(e) => setName(e.target.value)} className={inputCls} placeholder="合同会社〇〇 / 〇〇デザイン事務所" />
      </Field>
      <Field label={t("適格請求書発行事業者 登録番号（任意）")}>
        <input id="wz-reg" value={reg} onChange={(e) => setReg(normalizeReg(e.target.value))} className={inputCls + " font-mono"} placeholder="T1234567890123" />
        {reg && (registrationOk(reg) ? <span className="text-[10px] text-mint-700">{t("形式・チェックデジット OK")}</span>
          : <span className="text-[10px] text-amber-600">{t("形式またはチェックデジットが正しくありません（個人事業者の番号は国税庁の公表サイトで確認してください）")}</span>)}
      </Field>
      <fieldset className="space-y-1 text-xs">
        <legend className="font-bold text-slate-600">{t("事業形態")}</legend>
        <div className="flex gap-2">
          {[{ v: true, l: "個人事業主" }, { v: false, l: "法人" }].map((o) => (
            <button key={o.l} type="button" onClick={() => setIndividual(o.v)} aria-pressed={individual === o.v}
              className={"flex-1 rounded-lg border px-3 py-2 text-left " + (individual === o.v ? "border-navy bg-slate-50 font-bold text-navy" : "border-slate-200 text-slate-500")}>
              {t(o.l)}
            </button>
          ))}
        </div>
      </fieldset>
      {error && <Notice tone="error">{error}</Notice>}
      <Actions busy={busy} primary={t("保存して次へ")} onSkip={onSkip} />
    </form>
  );
}

/* ---------- 2. LINE 連携 ---------- */
function LineStep({ demo, draft, onDone, onSkip }: { demo: boolean; draft: ProfileDraft | null; onDone: () => void; onSkip: () => void }) {
  const t = useT();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linked, setLinked] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (linked) { onDone(); return; }
    const c = code.trim();
    if (!c.startsWith("tk_")) { setError(t("接続コードは「tk_」で始まります。LINE で「パネル」と送って取得してください。")); return; }
    if (demo) { setLinked(true); return; }
    setBusy(true);
    setError(null);
    try {
      const r = await api.linkLine(c);
      setToken(r.token); // eski web defteri token'ları sunucuda iptal edildi
      // Adım 1'de girilen 事業者情報 LINE defterinde yoksa oraya taşı (LINE defterindeki bilgi varsa korunur).
      try {
        const fix = profileAfterLink(draft, await api.profile());
        if (fix) await api.putProfile(fix);
      } catch { /* bağlantı tamam; 事業者情報 設定'ten girilebilir */ }
      setLinked(true);
    } catch (e2) {
      setError(e2 instanceof ApiError || e2 instanceof Error ? e2.message : String(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-3">
      <StepHead icon={<MessageCircle size={18} />} title={t("LINE 連携")} sub={t("LINE で記録した帳簿を、このアカウントで使えるようにします。")} />
      <ol className="space-y-1.5 text-xs text-slate-600">
        <li className="flex gap-2"><span className="font-bold text-mint-700 tabular-nums">1</span>
          <span>{t("J-SaaS 会計の LINE 公式アカウントを友だち追加します。")}
            {LINE_ADD_URL && <> <a href={LINE_ADD_URL} rel="noopener" target="_blank" className="font-bold text-navy underline-offset-2 hover:underline">{t("LINEで友だち追加")}</a></>}
          </span></li>
        <li className="flex gap-2"><span className="font-bold text-mint-700 tabular-nums">2</span><span>{t("トークで「パネル」と送ると、接続コード（tk_…）が届きます。")}</span></li>
        <li className="flex gap-2"><span className="font-bold text-mint-700 tabular-nums">3</span><span>{t("届いたコードを下に貼り付けて「連携する」を押します。")}</span></li>
      </ol>
      {linked ? (
        <Notice tone="ok">{t("LINE の帳簿をアカウントに連携しました。")}</Notice>
      ) : (
        <label className="block space-y-1 text-xs">
          <span className="flex items-center gap-1 font-bold text-slate-600"><KeyRound size={12} />{t("接続コード")}</span>
          <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="tk_..." autoComplete="off" spellCheck={false}
            className={inputCls + " font-mono"} />
        </label>
      )}
      {error && <Notice tone="error">{error}</Notice>}
      <p className="text-[10px] leading-relaxed text-slate-400">{t("LINE を使わない場合はスキップできます。あとから「設定」→「接続」で連携できます。")}</p>
      <Actions busy={busy} primary={linked ? t("次へ") : t("連携する")} onSkip={linked ? undefined : onSkip} />
    </form>
  );
}

/* ---------- 3. 最初の領収書 ---------- */
function ReceiptStep({ onDone }: { onDone: () => void }) {
  const t = useT();
  return (
    <form onSubmit={(e) => { e.preventDefault(); onDone(); }} className="space-y-3">
      <StepHead icon={<Receipt size={18} />} title={t("最初の領収書")} sub={t("レシートを1枚登録して、記帳の流れを試してみましょう。")} />
      <div className="grid gap-2 sm:grid-cols-2">
        <a href="/expenses/" className="block rounded-lg border border-slate-200 p-3 hover:border-navy">
          <span className="flex items-center gap-1.5 text-xs font-bold text-navy"><Receipt size={14} className="text-mint" />{t("画面から登録")}</span>
          <span className="mt-1 block text-[11px] text-slate-500">{t("「経費精算」→「領収書を読み取る」で写真をアップロードします。")}</span>
        </a>
        <div className="rounded-lg border border-slate-200 p-3">
          <span className="flex items-center gap-1.5 text-xs font-bold text-navy"><MessageCircle size={14} className="text-mint" />{t("LINE で送る")}</span>
          <span className="mt-1 block text-[11px] text-slate-500">{t("レシートの写真や「タクシー 2300」を送るだけで記帳されます。")}</span>
        </div>
      </div>
      <Actions primary={t("ホームへ")} />
    </form>
  );
}
