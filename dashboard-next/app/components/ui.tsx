"use client";

/** Ortak UI parçaları ve biçimlendirme yardımcıları. */
import { useEffect, useRef, useState } from "react";

/* ============================================================
 * HELPERS
 * ============================================================ */

export const yen = (n: number) => `${n < 0 ? "−" : ""}¥${Math.abs(Math.round(n)).toLocaleString("ja-JP")}`;
export const pct = (cur: number, prev: number) => ((cur - prev) / Math.abs(prev)) * 100;
export const taxIn = (gross: number, rate: number) => Math.floor((gross * rate) / (100 + rate));
export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");
export const daysUntil = (iso: string) => Math.ceil((new Date(iso + "T00:00:00+09:00").getTime() - new Date(new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" }) + "T00:00:00+09:00").getTime()) / 86_400_000);

/* ============================================================
 * SMALL UI PRIMITIVES
 * ============================================================ */

export function Card({ title, en, right, className, children }: { title: string; en?: string; right?: React.ReactNode; className?: string; children: React.ReactNode }) {
  return (
    <section className={cx("flex min-w-0 flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]", className)}>
      <header className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <h2 className="text-[13px] font-bold text-navy">{title}</h2>
        {en && <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">{en}</span>}
        {right && <div className="ml-auto">{right}</div>}
      </header>
      {children}
    </section>
  );
}

export function Badge({ tone, children, icon = true }: { tone: "ok" | "warn" | "bad" | "info" | "muted"; children: React.ReactNode; icon?: boolean }) {
  const tones = {
    ok: "bg-mint-50 text-mint-700 ring-mint-100",
    warn: "bg-amber-50 text-amber-700 ring-amber-100",
    bad: "bg-rose-50 text-rose-700 ring-rose-100",
    info: "bg-slate-100 text-navy ring-slate-200",
    muted: "bg-slate-50 text-slate-500 ring-slate-200",
  };
  return (
    <span className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-bold ring-1 ring-inset", tones[tone])}>
      {icon && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export function useToast() {
  const [msg, setMsg] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const show = (m: string) => {
    setMsg(m);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(null), 2600);
  };
  const node = msg ? (
    <div role="status" className="fixed bottom-5 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-navy px-4 py-2 text-xs text-white shadow-lg">
      {msg}
    </div>
  ) : null;
  return { show, node };
}

export function useClickOutside(ref: React.RefObject<HTMLElement | null>, onOut: () => void) {
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && onOut();
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [ref, onOut]);
}
/* ---------- form parçaları (menü sayfaları) ---------- */
export const inputCls =
  "h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-xs outline-none placeholder:text-slate-400 focus:border-navy";
export const selectCls = inputCls + " pr-7";

export function Field({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={cx("block space-y-1 text-xs", className)}>
      <span className="font-bold text-slate-600">{label}</span>
      {children}
    </label>
  );
}

export function Btn({ children, onClick, kind = "ghost", type = "button", disabled, className, title }: {
  children: React.ReactNode; onClick?: () => void; kind?: "primary" | "ghost" | "mint" | "danger";
  type?: "button" | "submit"; disabled?: boolean; className?: string; title?: string;
}) {
  const k = {
    primary: "bg-navy text-white hover:bg-navy-700",
    mint: "bg-mint text-navy-900 hover:bg-mint-600 hover:text-white",
    ghost: "border border-slate-200 bg-white text-slate-600 hover:border-navy hover:text-navy",
    danger: "border border-rose-200 bg-white text-rose-600 hover:bg-rose-50",
  }[kind];
  return (
    <button type={type} onClick={onClick} disabled={disabled} title={title}
      className={cx("inline-flex h-8 items-center justify-center gap-1.5 rounded-lg px-3 text-xs font-bold transition disabled:opacity-50", k, className)}>
      {children}
    </button>
  );
}

export function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: "ok" | "warn" | "bad" }) {
  const c = tone === "ok" ? "text-mint-600" : tone === "warn" ? "text-amber-600" : tone === "bad" ? "text-rose-600" : "text-navy";
  return (
    <div className="min-w-0 rounded-xl border border-slate-200 bg-white px-4 py-3">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className={cx("truncate font-mono text-lg font-semibold tabular", c)}>{value}</p>
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-xs text-slate-400">{children}</p>;
}

/** 法人番号チェックデジット（登録番号 T + 13桁 の検証） */
export function registrationOk(t: string): boolean {
  if (!/^T\d{13}$/.test(t)) return false;
  const d = t.slice(1).split("").map(Number);
  const s = d.slice(1).reverse().reduce((acc, x, i) => acc + x * (i % 2 === 0 ? 1 : 2), 0);
  return d[0] === 9 - (s % 9);
}

/** 登録番号のない仕入の控除割合（令和8年度改正, docs/TAX_RULES.md） */
export function creditRatio(date: string): number {
  if (date < "2023-10-01") return 100;
  if (date < "2026-10-01") return 80;
  if (date < "2028-10-01") return 70;
  if (date < "2030-10-01") return 50;
  if (date < "2031-10-01") return 30;
  return 0;
}
