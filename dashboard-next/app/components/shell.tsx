"use client";

/** Uygulama kabuğu: sayfa yönlendirmeli kenar menü, üst çubuk (arama, banka durumu, bildirim, şirket seçici), toast. */
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  Bell, Building2, Calculator, Check, ChevronDown, ChevronRight, CircleCheck, FileText, Home, Landmark,
  LoaderCircle, LogOut, Menu, Receipt, RefreshCw, Search, Settings, TriangleAlert, X,
} from "lucide-react";
import { api, ApiError, getToken, setToken } from "../lib/api";
import { MOCK, type Company } from "../lib/demo";
import { Badge, cx, useClickOutside, useToast } from "./ui";

/* ============================================================
 * SIDEBAR
 * ============================================================ */

export const NAV = [
  { ja: "ホーム", en: "Home", icon: Home, href: "/" },
  { ja: "請求書管理", en: "Invoices", icon: FileText, href: "/invoices/" },
  { ja: "経費精算", en: "Expenses", icon: Receipt, href: "/expenses/" },
  { ja: "銀行連携", en: "Bank Sync", icon: Landmark, href: "/bank/" },
  { ja: "確定申告 / 税務", en: "Tax Reporting", icon: Calculator, href: "/tax/" },
  { ja: "設定", en: "Settings", icon: Settings, href: "/settings/" },
];

function Sidebar({ open, onClose, company }: { open: boolean; onClose: () => void; company: Company }) {
  const path = usePathname() || "/";
  const norm = (p: string) => (p.endsWith("/") ? p : p + "/");
  const isActive = (href: string) => (href === "/" ? norm(path) === "/" : norm(path).startsWith(href));
  return (
    <>
      <div className={cx("fixed inset-0 z-40 bg-slate-900/40 lg:hidden", open ? "block" : "hidden")} onClick={onClose} aria-hidden />
      <aside
        className={cx(
          "fixed inset-y-0 left-0 z-50 flex w-56 flex-col bg-navy text-slate-300 transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="メインメニュー"
      >
        <div className="flex h-14 items-center gap-2.5 border-b border-white/10 px-4">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-mint text-sm font-black text-navy-900">J</div>
          <div className="leading-tight">
            <p className="text-sm font-bold text-white">J-SaaS 会計</p>
            <p className="text-[10px] text-slate-400">Cloud Accounting</p>
          </div>
          <button className="ml-auto rounded p-1 text-slate-400 hover:text-white lg:hidden" onClick={onClose} aria-label="メニューを閉じる">
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
          {NAV.map((n) => {
            const active = isActive(n.href);
            return (
              <Link
                key={n.en}
                href={n.href}
                onClick={onClose}
                aria-current={active ? "page" : undefined}
                className={cx(
                  "group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors",
                  active ? "bg-white/10 text-white" : "hover:bg-white/5 hover:text-white",
                )}
              >
                <n.icon size={17} className={active ? "text-mint" : "text-slate-400 group-hover:text-slate-200"} />
                <span className="min-w-0 flex-1">
                  <span className="block text-[13px] font-bold leading-tight">{n.ja}</span>
                  <span className="block text-[10px] leading-tight text-slate-500">{n.en}</span>
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="space-y-1 border-t border-white/10 p-4 text-[11px]">
          <p className="text-slate-400">適格請求書発行事業者</p>
          <p className="font-mono text-slate-200 tabular">{company.reg}</p>
          <p className="pt-1 text-slate-500">{company.fiscal}</p>
        </div>
      </aside>
    </>
  );
}

/* ============================================================
 * TOPBAR (command search, bank sync, notifications, company switcher)
 * ============================================================ */

function CommandPalette({ open, onClose, onPick }: { open: boolean; onClose: () => void; onPick: (item: { label: string; href: string }) => void }) {
  const [q, setQ] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const results = useMemo(() => {
    const k = q.trim().toLowerCase();
    return k ? MOCK.searchIndex.filter((r) => (r.label + r.sub + r.type).toLowerCase().includes(k)) : MOCK.searchIndex;
  }, [q]);

  useEffect(() => {
    if (open) { setQ(""); setCursor(0); setTimeout(() => inputRef.current?.focus(), 0); }
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-slate-900/40 px-4 pt-[12vh]" onMouseDown={onClose}>
      <div className="w-full max-w-xl overflow-hidden rounded-xl bg-white shadow-2xl ring-1 ring-slate-200" onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label="検索">
        <div className="flex items-center gap-2 border-b border-slate-200 px-4">
          <Search size={16} className="text-slate-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => { setQ(e.target.value); setCursor(0); }}
            onKeyDown={(e) => {
              if (e.key === "Escape") onClose();
              if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, results.length - 1)); }
              if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
              if (e.key === "Enter" && results[cursor]) onPick(results[cursor]);
            }}
            placeholder="請求書・取引先・領収書・書類を検索…"
            className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
          />
          <kbd className="rounded border border-slate-200 px-1.5 text-[10px] text-slate-400">ESC</kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto p-1.5">
          {results.length === 0 && <li className="px-3 py-6 text-center text-xs text-slate-400">該当する結果がありません</li>}
          {results.map((r, i) => (
            <li key={r.label}>
              <button
                onMouseEnter={() => setCursor(i)}
                onClick={() => onPick(r)}
                className={cx("flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left", i === cursor && "bg-slate-100")}
              >
                <span className="w-12 shrink-0 rounded bg-slate-100 py-0.5 text-center text-[10px] font-bold text-slate-500">{r.type}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] text-navy">{r.label}</span>
                  <span className="block truncate text-[11px] text-slate-400">{r.sub}</span>
                </span>
                <ChevronRight size={14} className="text-slate-300" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function Topbar({ onMenu, onSearch, company, setCompany, toast, live = false }: {
  onMenu: () => void; onSearch: () => void; company: Company; setCompany: (c: Company) => void; toast: (m: string) => void; live?: boolean;
}) {
  const notifications = live ? [] : MOCK.notifications;
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState("09:12");
  const [bellOpen, setBellOpen] = useState(false);
  const [coOpen, setCoOpen] = useState(false);
  const [unread, setUnread] = useState(live ? 0 : MOCK.notifications.length);
  const bellRef = useRef<HTMLDivElement>(null);
  const coRef = useRef<HTMLDivElement>(null);
  useClickOutside(bellRef, () => setBellOpen(false));
  useClickOutside(coRef, () => setCoOpen(false));

  const router = useRouter();
  const sync = () => {
    if (live) { router.push("/bank/"); return; }   // canlıda: banka sayfası (CSV取込)
    if (syncing) return;
    setSyncing(true);
    setTimeout(() => {
      setSyncing(false);
      setLastSync(new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Tokyo" }));
      toast("銀行明細を同期しました ・ 新規 18件");
    }, 1400);
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-slate-200 bg-white/90 px-3 backdrop-blur sm:gap-3 sm:px-5">
      <button onClick={onMenu} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden" aria-label="メニューを開く">
        <Menu size={18} />
      </button>

      <button
        onClick={onSearch}
        className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-left text-[13px] text-slate-400 hover:border-slate-300 sm:max-w-md"
      >
        <Search size={15} className="shrink-0" />
        <span className="truncate">書類・請求書・取引先を検索</span>
        <kbd className="ml-auto hidden rounded border border-slate-200 bg-white px-1.5 text-[10px] text-slate-400 sm:block">⌘K</kbd>
      </button>

      <div className="ml-auto flex items-center gap-1 sm:gap-2">
        {/* Bank sync status */}
        <button
          onClick={sync}
          title={live ? "銀行明細の取込" : "今すぐ同期"}
          className="hidden items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] hover:bg-slate-50 md:flex"
        >
          <Landmark size={14} className="text-slate-500" />
          <span className="text-slate-500">{live ? "銀行明細" : "銀行API"}</span>
          {live ? (
            <Badge tone="info" icon={false}>CSV取込</Badge>
          ) : syncing ? (
            <Badge tone="info" icon={false}><LoaderCircle size={11} className="animate-spin" />同期中</Badge>
          ) : (
            <Badge tone="ok">接続済</Badge>
          )}
          {!live && <span className="font-mono text-slate-400 tabular">{lastSync}</span>}
          <RefreshCw size={12} className={cx("text-slate-400", syncing && "animate-spin")} />
        </button>
        <button onClick={sync} className="rounded-lg p-2 md:hidden" aria-label="銀行API 接続済・同期">
          <span className="relative block">
            <Landmark size={18} className="text-slate-500" />
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-mint ring-2 ring-white" />
          </span>
        </button>

        {/* Notifications */}
        <div ref={bellRef} className="relative">
          <button onClick={() => { setBellOpen((o) => !o); setUnread(0); }} className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="通知">
            <Bell size={18} />
            {unread > 0 && <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[9px] font-bold text-white">{unread}</span>}
          </button>
          {bellOpen && (
            <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-24px)] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
              <p className="border-b border-slate-100 px-4 py-2.5 text-xs font-bold text-navy">お知らせ</p>
              <ul>
                {notifications.length === 0 && <li className="px-4 py-4 text-center text-xs text-slate-400">新しいお知らせはありません</li>}
                {notifications.map((n) => (
                  <li key={n.t} className="flex gap-3 border-b border-slate-100 px-4 py-2.5 last:border-0">
                    {n.kind === "warn" ? <TriangleAlert size={15} className="mt-0.5 shrink-0 text-amber-500" /> : <CircleCheck size={15} className="mt-0.5 shrink-0 text-mint" />}
                    <div className="min-w-0">
                      <p className="text-xs text-slate-700">{n.t}</p>
                      <p className="text-[10px] text-slate-400">{n.time}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Company / profile switcher */}
        <div ref={coRef} className="relative">
          <button onClick={() => setCoOpen((o) => !o)} className="flex items-center gap-2 rounded-lg p-1 pr-2 hover:bg-slate-100">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-navy text-xs font-bold text-white">佐</span>
            <span className="hidden text-left leading-tight sm:block">
              <span className="block max-w-[140px] truncate text-xs font-bold text-navy">{company.name}</span>
              <span className="block text-[10px] text-slate-400">経理担当 佐藤</span>
            </span>
            <ChevronDown size={14} className="text-slate-400" />
          </button>
          {coOpen && (
            <div className="absolute right-0 mt-2 w-64 overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-xl">
              <p className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">事業所を切り替え</p>
              {(live ? [company] : MOCK.companies).map((c) => (
                <button
                  key={c.id}
                  onClick={() => { setCompany(c); setCoOpen(false); toast(`${c.name} に切り替えました`); }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left hover:bg-slate-50"
                >
                  <Building2 size={15} className="text-slate-400" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-bold text-navy">{c.name}</span>
                    <span className="block font-mono text-[10px] text-slate-400">{c.reg}</span>
                  </span>
                  {c.id === company.id && <Check size={14} className="text-mint" />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}


/* ============================================================
 * BAĞLANTI + KABUK
 * ============================================================ */

export type Mode = "loading" | "live" | "demo";

/** Token varsa profil yüklenir ("live"), yoksa demo. Tüm sayfalar kullanır. */
export function useConnection() {
  const [mode, setMode] = useState<Mode>("loading");
  const [company, setCompany] = useState<Company>(MOCK.companies[0]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!getToken()) { setMode("demo"); return; }
    api.profile()
      .then((p) => {
        const y = new Date().getFullYear();
        setCompany({ id: p.user_id, name: p.business_name || "事業者名未設定", reg: p.registration_no || "登録番号未設定", fiscal: `${y}年分` });
        setMode("live");
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) setToken(null);
        setError(e instanceof Error ? e.message : String(e));
        setMode("demo");
      });
  }, []);
  return { mode, company, setCompany, error };
}

type ShellCtx = { toast: (m: string) => void; mode: Mode; live: boolean; company: Company };
const Ctx = createContext<ShellCtx>({ toast: () => {}, mode: "demo", live: false, company: MOCK.companies[0] });
export const useShell = () => useContext(Ctx);

export function ModeBadge({ mode }: { mode: Mode }) {
  if (mode === "loading") return <Badge tone="info" icon={false}><LoaderCircle size={11} className="animate-spin" />読み込み中</Badge>;
  if (mode === "demo")
    return (
      <span className="flex items-center gap-2">
        <Badge tone="warn">デモデータ</Badge>
        <a href="/connect/" className="text-[11px] font-bold text-navy underline-offset-2 hover:underline">自分の帳簿に接続</a>
      </span>
    );
  return (
    <span className="flex items-center gap-2">
      <Badge tone="ok">ライブ</Badge>
      <button onClick={() => { setToken(null); location.reload(); }} className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-navy">
        <LogOut size={12} />切断
      </button>
    </span>
  );
}

/**
 * Her sayfanın dış çerçevesi. `conn` verilmezse kendi bağlantısını yükler.
 * Başlık satırında sayfa adı, alt açıklama, sağda mod rozeti + isteğe bağlı aksiyonlar.
 */
export function AppShell({ title, en, sub, actions, conn, children }: {
  title: string; en?: string; sub?: React.ReactNode; actions?: React.ReactNode;
  conn?: ReturnType<typeof useConnection>; children: React.ReactNode;
}) {
  const own = useConnection();
  const c = conn ?? own;
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const { show: toast, node: toastNode } = useToast();
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setSearchOpen(true); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <Ctx.Provider value={{ toast, mode: c.mode, live: c.mode === "live", company: c.company }}>
      <div className="flex min-h-screen">
        <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} company={c.company} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar key={c.mode} live={c.mode === "live"} onMenu={() => setMenuOpen(true)} onSearch={() => setSearchOpen(true)} company={c.company} setCompany={c.setCompany} toast={toast} />
          <main className="mx-auto w-full max-w-[1400px] flex-1 p-3 sm:p-5">
            <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1">
              <h1 className="text-lg font-bold text-navy">{title}{en && <span className="ml-2 text-[11px] font-medium uppercase tracking-wider text-slate-400">{en}</span>}</h1>
              {sub && <p className="text-xs text-slate-400">{sub}</p>}
              <div className="ml-auto flex flex-wrap items-center gap-2">
                {actions}
                <ModeBadge mode={c.mode} />
              </div>
            </div>
            {c.error && c.mode === "demo" && (
              <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">サーバーに接続できなかったため、デモデータを表示しています（{c.error}）。</p>
            )}
            {children}
          </main>
        </div>
        <CommandPalette open={searchOpen} onClose={() => setSearchOpen(false)} onPick={(it) => { setSearchOpen(false); router.push(it.href); }} />
        {toastNode}
      </div>
    </Ctx.Provider>
  );
}
