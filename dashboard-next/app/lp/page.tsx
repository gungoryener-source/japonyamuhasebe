/** Tanıtım sayfası (T-044). Sunucu bileşeni: tüm metin statik HTML'e girer (JS olmadan okunur). İçerik: app/lib/lp.ts */
import type { Metadata } from "next";
import { ArrowRight, Calculator, Check, ChevronDown, FileText, MessageCircle, ShieldCheck } from "lucide-react";
import { SERVICE_NAME, LEGAL_PAGES } from "../lib/legal";
import {
  FAQ, FEATURES, HERO, LINE_ADD_URL, LOGIN_HREF, LP_PLANS, PRICE_NOTE, SIGNUP_HREF, STEPS, limitLabel, yenLabel,
} from "../lib/lp";

export const metadata: Metadata = {
  title: `${SERVICE_NAME} | LINEで記帳するクラウド会計`,
  description: HERO.lead,
};

const ICONS = { message: MessageCircle, invoice: FileText, tax: Calculator } as const;

function Logo() {
  return (
    <a href="/lp/" className="inline-flex items-center gap-2 text-navy">
      <span className="grid h-7 w-7 place-items-center rounded-lg bg-mint text-xs font-black text-navy-900">J</span>
      <span className="text-sm font-bold">{SERVICE_NAME}</span>
    </a>
  );
}

function Cta({ className = "" }: { className?: string }) {
  return (
    <div className={`flex flex-wrap items-center gap-3 ${className}`}>
      <a href={SIGNUP_HREF}
        className="inline-flex items-center gap-1.5 rounded-lg bg-mint px-5 py-2.5 text-sm font-bold text-navy-900 shadow-sm hover:bg-mint-600 hover:text-white">
        無料で始める <ArrowRight size={16} />
      </a>
      {LINE_ADD_URL && (
        <a href={LINE_ADD_URL} rel="noopener"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-bold text-navy hover:border-mint">
          <MessageCircle size={16} className="text-mint" /> LINEで友だち追加
        </a>
      )}
    </div>
  );
}

export default function Page() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-[#F9FAFB] text-slate-700">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
          <Logo />
          <nav className="flex items-center gap-3 text-xs">
            <a href="#pricing" className="hidden text-slate-500 hover:text-navy sm:inline">料金</a>
            <a href="#faq" className="hidden text-slate-500 hover:text-navy sm:inline">よくある質問</a>
            <a href={LOGIN_HREF} className="text-slate-500 hover:text-navy">ログイン</a>
            <a href={SIGNUP_HREF} className="rounded-md bg-navy px-3 py-1.5 font-bold text-white hover:bg-navy-700">無料登録</a>
          </nav>
        </div>
      </header>

      <main>
        {/* Kahraman */}
        <section className="bg-navy text-white">
          <div className="mx-auto grid max-w-5xl gap-8 px-4 py-12 sm:py-16 md:grid-cols-[1.2fr_1fr] md:items-center">
            <div className="min-w-0 space-y-5">
              <p className="text-xs font-bold tracking-wider text-mint">個人事業主・小さな会社のクラウド会計</p>
              <h1 className="text-3xl font-black leading-tight sm:text-4xl">{HERO.title}</h1>
              <p className="text-sm leading-7 text-slate-300">{HERO.lead}</p>
              <Cta />
              <p className="text-[11px] text-slate-400">フリープランはクレジットカード登録不要です。</p>
            </div>
            <ol aria-label="使い方の流れ" className="min-w-0 space-y-2">
              {HERO.flow.map((f, i) => (
                <li key={f} className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-mint font-mono text-xs font-bold text-navy-900 tabular-nums">{i + 1}</span>
                  <span className="text-sm font-bold">{f}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Özellikler */}
        <section aria-labelledby="features" className="mx-auto max-w-5xl px-4 py-12">
          <h2 id="features" className="mb-6 text-center text-xl font-bold text-navy">できること</h2>
          <div className="grid gap-3 md:grid-cols-3">
            {FEATURES.map((f) => {
              const Icon = ICONS[f.icon];
              return (
                <article key={f.title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="mb-3 grid h-9 w-9 place-items-center rounded-lg bg-navy text-mint"><Icon size={18} /></div>
                  <h3 className="mb-2 text-sm font-bold text-navy">{f.title}</h3>
                  <p className="text-xs leading-6 text-slate-600">{f.body}</p>
                </article>
              );
            })}
          </div>
        </section>

        {/* Adımlar */}
        <section aria-labelledby="steps" className="border-y border-slate-200 bg-white">
          <div className="mx-auto max-w-5xl px-4 py-12">
            <h2 id="steps" className="mb-6 text-center text-xl font-bold text-navy">LINEで始める3ステップ</h2>
            <ol className="grid gap-3 md:grid-cols-3">
              {STEPS.map((s, i) => (
                <li key={s.title} className="rounded-xl bg-[#F9FAFB] p-5">
                  <p className="mb-1 font-mono text-xs font-bold text-mint-600 tabular-nums">STEP {i + 1}</p>
                  <h3 className="mb-1 text-sm font-bold text-navy">{s.title}</h3>
                  <p className="text-xs leading-6 text-slate-600">{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Fiyatlar */}
        <section id="pricing" aria-labelledby="pricing-h" className="mx-auto max-w-5xl px-4 py-12">
          <h2 id="pricing-h" className="mb-6 text-center text-xl font-bold text-navy">料金プラン</h2>
          <div className="grid gap-3 md:grid-cols-3">
            {LP_PLANS.map((p) => (
              <section key={p.id} data-plan={p.id}
                className={`flex flex-col gap-3 rounded-xl border bg-white p-5 ${p.id === "personal" ? "border-mint ring-1 ring-mint" : "border-slate-200"}`}>
                <h3 className="text-sm font-bold text-navy">{p.name}プラン</h3>
                <p className="font-mono text-2xl font-semibold text-navy tabular-nums">
                  {yenLabel(p.price_jpy)}
                  <span className="ml-1 font-sans text-[11px] font-normal text-slate-400">/ 月（税抜）</span>
                </p>
                <ul className="flex-1 space-y-1 text-xs text-slate-600">
                  <li className="flex gap-1.5"><Check size={13} className="mt-0.5 shrink-0 text-mint" />経費 {limitLabel(p.receipts_per_month)}</li>
                  <li className="flex gap-1.5"><Check size={13} className="mt-0.5 shrink-0 text-mint" />請求書 {limitLabel(p.invoices_per_month)}</li>
                  {p.notes.map((n) => (
                    <li key={n} className="flex gap-1.5"><Check size={13} className="mt-0.5 shrink-0 text-mint" />{n}</li>
                  ))}
                </ul>
                <a href={SIGNUP_HREF}
                  className={`rounded-lg px-4 py-2 text-center text-xs font-bold ${p.id === "free" ? "bg-mint text-navy-900 hover:bg-mint-600 hover:text-white" : "border border-slate-300 text-navy hover:border-mint"}`}>
                  {p.id === "free" ? "無料で始める" : "登録してプランを選ぶ"}
                </a>
              </section>
            ))}
          </div>
          <p className="mt-3 text-center text-[11px] text-slate-400">
            {PRICE_NOTE}{" "}
            <a href="/legal/tokushoho/" className="underline-offset-2 hover:text-navy hover:underline">特定商取引法に基づく表記</a>
          </p>
        </section>

        {/* SSS */}
        <section id="faq" aria-labelledby="faq-h" className="border-t border-slate-200 bg-white">
          <div className="mx-auto max-w-3xl px-4 py-12">
            <h2 id="faq-h" className="mb-6 text-center text-xl font-bold text-navy">よくある質問</h2>
            <div className="divide-y divide-slate-100 rounded-xl border border-slate-200">
              {FAQ.map((f) => (
                <details key={f.q} className="group px-4 py-3">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-bold text-navy">
                    <span>{f.q}</span>
                    <ChevronDown size={16} className="shrink-0 text-slate-400 transition group-open:rotate-180" />
                  </summary>
                  <p className="mt-2 text-xs leading-6 text-slate-600">{f.a}</p>
                </details>
              ))}
            </div>
            <p className="mt-4 flex items-start gap-1.5 text-[11px] leading-5 text-slate-400">
              <ShieldCheck size={13} className="mt-0.5 shrink-0" />
              本サービスは税務相談・税務代理を行うものではありません。表示される税額は概算です。
            </p>
          </div>
        </section>

        <section className="bg-navy">
          <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 px-4 py-10 text-center text-white">
            <h2 className="text-lg font-bold">今日のレシートから、記帳をはじめましょう。</h2>
            <Cta className="justify-center" />
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-2 px-4 py-6 text-[11px] text-slate-400 sm:flex-row sm:justify-between">
          <span>© {SERVICE_NAME}</span>
          <nav aria-label="法務ページ" className="flex flex-wrap justify-center gap-x-4 gap-y-1">
            {LEGAL_PAGES.map((p) => <a key={p.slug} href={p.href} className="hover:text-navy">{p.title}</a>)}
            <a href={LOGIN_HREF} className="hover:text-navy">ログイン</a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
