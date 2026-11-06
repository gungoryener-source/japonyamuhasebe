/** Yasal sayfalar için ortak görünüm (T-043). Sunucu bileşeni: metin statik HTML'e girer (JS olmadan okunur). */
import { FileText, TriangleAlert } from "lucide-react";
import { DRAFT_NOTICE, LEGAL_PAGES, LEGAL_UPDATED, PENDING, SERVICE_NAME, type LegalDoc } from "../lib/legal";

function Pending() {
  return <span className="ml-1.5 inline-flex shrink-0 items-center rounded bg-amber-100 px-1.5 py-0.5 align-middle text-[10px] font-bold text-amber-700">{PENDING}</span>;
}

export function LegalPage({ doc }: { doc: LegalDoc }) {
  return (
    <main className="min-h-screen bg-[#F9FAFB] px-4 py-8">
      <div className="mx-auto w-full max-w-3xl space-y-4">
        <a href="/" className="inline-flex items-center gap-2 text-navy">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-mint text-xs font-black text-navy-900">J</span>
          <span className="text-sm font-bold">{SERVICE_NAME}</span>
        </a>

        <div role="note" className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
          <TriangleAlert size={16} className="mt-0.5 shrink-0" />
          <p>
            <strong className="font-bold">{DRAFT_NOTICE}。</strong>
            内容は専門家による確認前のもので、今後変更される可能性があります。「{PENDING}」と表示された箇所は未確定です。
          </p>
        </div>

        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <header className="mb-6 flex items-start gap-3 border-b border-slate-100 pb-4">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-navy text-mint"><FileText size={18} /></div>
            <div className="min-w-0">
              <h1 className="text-lg font-bold text-navy">{doc.title}</h1>
              <p className="text-[11px] text-slate-400">{doc.en} ・ 最終更新：{LEGAL_UPDATED}</p>
            </div>
          </header>

          <p className="mb-6 text-sm leading-7 text-slate-700">{doc.intro}</p>

          {doc.rows && (
            <dl className="divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200 text-sm">
              {doc.rows.map((r) => (
                <div key={r.label} className="grid gap-1 px-4 py-3 sm:grid-cols-[11rem_1fr] sm:gap-4">
                  <dt className="font-bold text-slate-600">{r.label}</dt>
                  <dd className="leading-6 text-slate-700">
                    {r.value === PENDING ? <Pending /> : <>{r.value}{r.todo && <Pending />}</>}
                  </dd>
                </div>
              ))}
            </dl>
          )}

          <div className="space-y-6">
            {doc.sections.map((s) => (
              <section key={s.heading} className="space-y-2">
                <h2 className="text-sm font-bold text-navy">{s.heading}</h2>
                {s.blocks.map((b, i) =>
                  b.items ? (
                    <ul key={i} className="list-disc space-y-1 pl-5 text-sm leading-7 text-slate-700">
                      {b.items.map((it) => <li key={it}>{it}</li>)}
                    </ul>
                  ) : (
                    <p key={i} className="text-sm leading-7 text-slate-700">{b.text}{b.todo && <Pending />}</p>
                  ),
                )}
              </section>
            ))}
          </div>
        </article>

        <nav aria-label="法務ページ" className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-[11px] text-slate-400">
          {LEGAL_PAGES.map((p) => (
            <a key={p.slug} href={p.href} aria-current={p.slug === doc.slug ? "page" : undefined}
              className={p.slug === doc.slug ? "font-bold text-navy" : "hover:text-navy"}>{p.title}</a>
          ))}
          <a href="/" className="hover:text-navy">ホーム</a>
        </nav>
      </div>
    </main>
  );
}

/** Formlar/menü altı için kısa yasal bağlantılar. */
export function LegalLinks({ className = "" }: { className?: string }) {
  return (
    <span className={`flex flex-wrap items-center justify-center gap-x-3 gap-y-1 ${className}`}>
      {LEGAL_PAGES.map((p) => <a key={p.slug} href={p.href} className="hover:text-navy hover:underline">{p.title}</a>)}
    </span>
  );
}
