"use client";

/** Hesap sayfaları (/signup, /login, /reset, /connect) için ortak kart ve form parçaları (T-040b). */
import { LoaderCircle } from "lucide-react";
import { ApiError, NETWORK_ERROR } from "../lib/api";
import { LegalLinks } from "./legal";

export function AuthCard({ icon, title, sub, children, onSubmit, footer }: {
  icon: React.ReactNode; title: string; sub?: React.ReactNode; children: React.ReactNode;
  onSubmit?: () => void; footer?: React.ReactNode;
}) {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F9FAFB] p-4">
      <div className="w-full max-w-sm space-y-3">
        <a href="/" className="flex items-center justify-center gap-2 text-navy">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-mint text-xs font-black text-navy-900">J</span>
          <span className="text-sm font-bold">J-SaaS 会計</span>
        </a>
        <form
          noValidate
          onSubmit={(e) => { e.preventDefault(); onSubmit?.(); }}
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div className="flex items-center gap-2.5">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-navy text-mint">{icon}</div>
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-navy">{title}</h1>
              {sub && <p className="text-[11px] text-slate-400">{sub}</p>}
            </div>
          </div>
          {children}
        </form>
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-[11px] text-slate-400">
          {footer}
          <a href="/" className="hover:text-navy">デモデータで見る</a>
        </div>
        <LegalLinks className="text-[10px] text-slate-400" />
      </div>
    </main>
  );
}

export function AuthInput({ label, hint, className, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <label className="block space-y-1 text-xs">
      <span className="font-bold text-slate-600">{label}</span>
      <input
        {...props}
        className={`h-10 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none placeholder:text-slate-300 focus:border-navy ${className ?? ""}`}
      />
      {hint && <span className="block text-[10px] text-slate-400">{hint}</span>}
    </label>
  );
}

export function SubmitBtn({ busy, children }: { busy: boolean; children: React.ReactNode }) {
  return (
    <button disabled={busy} className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-navy text-sm font-bold text-white hover:bg-navy-700 disabled:opacity-60">
      {busy && <LoaderCircle size={15} className="animate-spin" />}{children}
    </button>
  );
}

export function Notice({ tone, children }: { tone: "error" | "ok" | "warn"; children: React.ReactNode }) {
  const c = { error: "bg-rose-50 text-rose-700", ok: "bg-mint-50 text-mint-700", warn: "bg-amber-50 text-amber-800" }[tone];
  return <p role={tone === "error" ? "alert" : "status"} className={`rounded-lg px-3 py-2 text-xs ${c}`}>{children}</p>;
}

/** API hatasını kullanıcı metnine çevirir: sunucunun Japonca `detail`'i olduğu gibi, ağ hatasında demo yönlendirmesi. */
export function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.status === 0 ? `${NETWORK_ERROR}（デモデータは下のリンクから見られます）` : e.message;
  return NETWORK_ERROR;
}

export const EMAIL_RE = /^[^@\s]{1,64}@[^@\s]+\.[^@\s]+$/;

/** Giriş sonrası dönülecek yol: yalnızca site içi göreli yol (açık yönlendirme yok). */
export function nextPath(): string {
  try {
    const n = new URLSearchParams(location.search).get("next") ?? "";
    return /^\/[a-z0-9/_-]*$/i.test(n) && !n.startsWith("//") ? n : "/";
  } catch {
    return "/";
  }
}

/**
 * Bekleyen davet kodu (T-041b): /join'e giriş yapmadan gelen kullanıcı giriş/kayıt sonrası kodu yeniden yazmasın diye
 * yalnızca bu sekmede (sessionStorage) tutulur. Başarılı katılımda silinir.
 */
const INVITE_KEY = "jsaas.invite";
export function pendingInvite(): string {
  try { return sessionStorage.getItem(INVITE_KEY) ?? ""; } catch { return ""; }
}
export function setPendingInvite(code: string | null) {
  try { if (code) sessionStorage.setItem(INVITE_KEY, code); else sessionStorage.removeItem(INVITE_KEY); } catch { /* storage yok */ }
}
