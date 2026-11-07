"use client";

/** Uygulama kabuğu: sayfa yönlendirmeli kenar menü, üst çubuk (arama, banka durumu, bildirim, şirket seçici), toast. */
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  Bell, Building2, Calculator, CreditCard, Check, ChevronDown, ChevronRight, CircleCheck, FileText, Home, Landmark,
  Eye, LoaderCircle, LogOut, Menu, Receipt, RefreshCw, Search, Settings, TriangleAlert, UserPlus, X,
} from "lucide-react";
import { api, ApiError, getToken, replaceSession, setToken } from "../lib/api";
import { canWrite, ledgerOptions, parseRole, ROLE_LABEL, type Ledger, type Role } from "../lib/team";
import { MOCK, type Company } from "../lib/demo";
import { Badge, cx, useClickOutside, useToast } from "./ui";
import { LegalLinks } from "./legal";
import { LangSwitcher, useLang, useT } from "./lang";

/* ============================================================
 * SIDEBAR
 * ============================================================ */

export const NAV = [
  { ja: "ホーム", en: "Home", icon: Home, href: "/" },
  { ja: "請求書管理", en: "Invoices", icon: FileText, href: "/invoices/" },
  { ja: "経費精算", en: "Expenses", icon: Receipt, href: "/expenses/" },
  { ja: "銀行連携", en: "Bank Sync", icon: Landmark, href: "/bank/" },
  { ja: "確定申告 / 税務", en: "Tax Reporting", icon: Calculator, href: "/tax/" },
  { ja: "料金プラン", en: "Billing", icon: CreditCard, href: "/billing/" },
  { ja: "設定", en: "Settings", icon: Settings, href: "/settings/" },
];

function Sidebar({ open, onClose, company }: { open: boolean; onClose: () => void; company: Company }) {
  const { t, lang } = useLang();
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
        aria-label={t("メインメニュー")}
      >
        <div className="flex h-14 items-center gap-2.5 border-b border-white/10 px-4">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-mint text-sm font-black text-navy-900">J</div>
          <div className="leading-tight">
            <p className="text-sm font-bold text-white">J-SaaS 会計</p>
            <p className="text-[10px] text-slate-400">Cloud Accounting</p>
          </div>
          <button className="ml-auto rounded p-1 text-slate-400 hover:text-white lg:hidden" onClick={onClose} aria-label={t("メニューを閉じる")}>
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
                  <span className="block text-[13px] font-bold leading-tight">{t(n.ja)}</span>
                  <span className="block text-[10px] leading-tight text-slate-500">{lang === "ja" ? n.en : n.ja}</span>
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="space-y-1 border-t border-white/10 p-4 text-[11px]">
          <p className="text-slate-400">{t("適格請求書発行事業者")}</p>
          <p className="font-mono text-slate-200 tabular">{company.reg}</p>
          <p className="pt-1 text-slate-500">{company.fiscal}</p>
          <LegalLinks className="!justify-start pt-2 text-[10px] text-slate-500 [&_a:hover]:!text-slate-200" />
        </div>
      </aside>
    </>
  );
}

/* ============================================================
 * TOPBAR (command search, bank sync, notifications, company switcher)
 * ============================================================ */

function CommandPalette({ open, onClose, onPick }: { open: boolean; onClose: () => void; onPick: (item: { label: string; href: string }) => void }) {
  const t = useT();
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
      <div className="w-full max-w-xl overflow-hidden rounded-xl bg-white shadow-2xl ring-1 ring-slate-200" onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label={t("検索")}>
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
            placeholder={t("請求書・取引先・領収書・書類を検索…")}
            className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
          />
          <kbd className="rounded border border-slate-200 px-1.5 text-[10px] text-slate-400">ESC</kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto p-1.5">
          {results.length === 0 && <li className="px-3 py-6 text-center text-xs text-slate-400">{t("該当する結果がありません")}</li>}
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

export function Topbar({ onMenu, onSearch, company, setCompany, toast, live = false, role = "owner", account = false }: {
  onMenu: () => void; onSearch: () => void; company: Company; setCompany: (c: Company) => void; toast: (m: string) => void; live?: boolean;
  role?: Role; account?: boolean;
}) {
  const t = useT();
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

  // Canlı: hesabın erişebildiği defterler (T-041 GET /team/ledgers). Menü ilk açıldığında yüklenir.
  const [ledgers, setLedgers] = useState<Ledger[] | null>(null);
  const [switching, setSwitching] = useState<string | null>(null);
  const openCo = () => {
    setCoOpen((o) => !o);
    if (live && account && ledgers === null) {
      api.teamLedgers().then((r) => setLedgers(ledgerOptions(r.ledgers))).catch(() => setLedgers([]));
    }
  };
  const switchTo = async (l: Ledger) => {
    if (l.user_id === company.id || switching) { setCoOpen(false); return; }
    setSwitching(l.user_id);
    try {
      const r = await api.teamSwitch(l.user_id);
      await replaceSession(r.token);
      location.href = "/";
    } catch (e) {
      setSwitching(null);
      toast(t("切り替えに失敗しました: {e}", { e: e instanceof Error ? e.message : String(e) }));
    }
  };

  const router = useRouter();
  const sync = () => {
    if (live) { router.push("/bank/"); return; }   // canlıda: banka sayfası (CSV取込)
    if (syncing) return;
    setSyncing(true);
    setTimeout(() => {
      setSyncing(false);
      setLastSync(new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Tokyo" }));
      toast(t("銀行明細を同期しました ・ 新規 18件"));
    }, 1400);
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-slate-200 bg-white/90 px-3 backdrop-blur sm:gap-3 sm:px-5">
      <button onClick={onMenu} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden" aria-label={t("メニューを開く")}>
        <Menu size={18} />
      </button>

      <button
        onClick={onSearch}
        className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-left text-[13px] text-slate-400 hover:border-slate-300 sm:max-w-md"
      >
        <Search size={15} className="shrink-0" />
        <span className="truncate">{t("書類・請求書・取引先を検索")}</span>
        <kbd className="ml-auto hidden rounded border border-slate-200 bg-white px-1.5 text-[10px] text-slate-400 sm:block">⌘K</kbd>
      </button>

      <div className="ml-auto flex items-center gap-1 sm:gap-2">
        <LangSwitcher compact />
        {/* Bank sync status */}
        <button
          onClick={sync}
          title={t(live ? "銀行明細の取込" : "今すぐ同期")}
          className="hidden items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] hover:bg-slate-50 md:flex"
        >
          <Landmark size={14} className="text-slate-500" />
          <span className="text-slate-500">{t(live ? "銀行明細" : "銀行API")}</span>
          {live ? (
            <Badge tone="info" icon={false}>{t("CSV取込")}</Badge>
          ) : syncing ? (
            <Badge tone="info" icon={false}><LoaderCircle size={11} className="animate-spin" />{t("同期中")}</Badge>
          ) : (
            <Badge tone="ok">{t("接続済")}</Badge>
          )}
          {!live && <span className="font-mono text-slate-400 tabular">{lastSync}</span>}
          <RefreshCw size={12} className={cx("text-slate-400", syncing && "animate-spin")} />
        </button>
        <button onClick={sync} className="rounded-lg p-2 md:hidden" aria-label={t("銀行API 接続済・同期")}>
          <span className="relative block">
            <Landmark size={18} className="text-slate-500" />
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-mint ring-2 ring-white" />
          </span>
        </button>

        {/* Notifications */}
        <div ref={bellRef} className="relative">
          <button onClick={() => { setBellOpen((o) => !o); setUnread(0); }} className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label={t("通知")}>
            <Bell size={18} />
            {unread > 0 && <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[9px] font-bold text-white">{unread}</span>}
          </button>
          {bellOpen && (
            <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-24px)] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
              <p className="border-b border-slate-100 px-4 py-2.5 text-xs font-bold text-navy">{t("お知らせ")}</p>
              <ul>
                {notifications.length === 0 && <li className="px-4 py-4 text-center text-xs text-slate-400">{t("新しいお知らせはありません")}</li>}
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
          <button onClick={openCo} className="flex items-center gap-2 rounded-lg p-1 pr-2 hover:bg-slate-100" aria-haspopup="menu" aria-expanded={coOpen}>
            <span className="grid h-8 w-8 place-items-center rounded-full bg-navy text-xs font-bold text-white">{live ? (company.name.trim()[0] ?? "帳") : "佐"}</span>
            <span className="hidden text-left leading-tight sm:block">
              <span className="block max-w-[140px] truncate text-xs font-bold text-navy">{company.name}</span>
              <span className="block text-[10px] text-slate-400">{t(live ? ROLE_LABEL[role] : "経理担当 佐藤")}</span>
            </span>
            <ChevronDown size={14} className="text-slate-400" />
          </button>
          {coOpen && (
            <div className="absolute right-0 mt-2 w-64 overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-xl">
              <p className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">{t("事業所を切り替え")}</p>
              {live ? (
                <>
                  {!account && (
                    <p className="px-3 pb-2 text-[11px] text-slate-500">
                      {t("複数の帳簿を切り替えるには")}<a href="/login/" className="font-bold text-navy hover:underline">{t("メールアドレスでログイン")}</a>{t("してください。")}
                    </p>
                  )}
                  {(account ? ledgers : [{ user_id: company.id, role, business_name: company.name }])?.map((l) => (
                    <button
                      key={l.user_id}
                      onClick={() => switchTo(l)}
                      disabled={!!switching}
                      className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left hover:bg-slate-50 disabled:opacity-60"
                    >
                      {switching === l.user_id ? <LoaderCircle size={15} className="animate-spin text-slate-400" /> : <Building2 size={15} className="text-slate-400" />}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-xs font-bold text-navy">{l.business_name}</span>
                        <span className="block text-[10px] text-slate-400">{t(ROLE_LABEL[l.role])}</span>
                      </span>
                      {l.user_id === company.id && <Check size={14} className="text-mint" />}
                    </button>
                  ))}
                  {account && ledgers === null && (
                    <p className="flex items-center gap-2 px-3 py-2 text-[11px] text-slate-400"><LoaderCircle size={12} className="animate-spin" />{t("読み込み中…")}</p>
                  )}
                  {account && (
                    <a href="/join/" className="mt-1 flex items-center gap-2 border-t border-slate-100 px-3 py-2 text-[11px] text-slate-500 hover:text-navy">
                      <UserPlus size={13} />{t("招待コードで帳簿に参加")}
                    </a>
                  )}
                </>
              ) : MOCK.companies.map((c) => (
                <button
                  key={c.id}
                  onClick={() => { setCompany(c); setCoOpen(false); toast(t("{name} に切り替えました", { name: c.name })); }}
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
  const [email, setEmail] = useState<string | null>(null);
  const [role, setRole] = useState<Role>("owner");
  useEffect(() => {
    if (!getToken()) { setMode("demo"); return; }
    // Hesap e-postası (T-040b) + rol (T-041). Eski sunucuda /auth/me yoksa kod oturumu ve owner sayılır.
    // Rol, düzenleme düğmeleri bir an bile yanlış görünmesin diye "live"dan önce çözülür.
    const me = api.me().catch(() => null);
    Promise.all([api.profile(), me])
      .then(([p, m]) => {
        setEmail(m?.account?.email ?? null);
        setRole(parseRole(m?.role));
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
  return { mode, company, setCompany, error, email, role };
}

/**
 * `role`: canlı oturumun rolü (demo/yükleniyor → owner). `canEdit`: muhasebe verisi yazılabilir mi (viewer → false).
 * Sayfalar düzenleme düğmelerini `canEdit` ile gizler; sunucu yine 403 ile korur.
 */
type ShellCtx = { toast: (m: string) => void; mode: Mode; live: boolean; company: Company; role: Role; canEdit: boolean };
const Ctx = createContext<ShellCtx>({ toast: () => {}, mode: "demo", live: false, company: MOCK.companies[0], role: "owner", canEdit: true });
export const useShell = () => useContext(Ctx);

/**
 * Hesap oturumu: sunucuda token iptal (DELETE /tokens/current) + /login.
 * Yalnızca LINE koduyla açılmış oturum: eskisi gibi yalnızca tarayıcıdan silinir (kod LINE'da tekrar kullanılabilir).
 */
async function logout(account: boolean) {
  if (account) {
    try { await api.revoke(); } catch { /* sunucuya ulaşılamasa da yerelden çık */ }
  }
  setToken(null);
  if (account) location.href = "/login/";
  else location.reload();
}

export function ModeBadge({ mode, email, role = "owner" }: { mode: Mode; email?: string | null; role?: Role }) {
  const t = useT();
  if (mode === "loading") return <Badge tone="info" icon={false}><LoaderCircle size={11} className="animate-spin" />{t("読み込み中")}</Badge>;
  if (mode === "demo")
    return (
      <span className="flex items-center gap-2">
        <Badge tone="warn">{t("デモデータ")}</Badge>
        <a href="/login/" className="text-[11px] font-bold text-navy underline-offset-2 hover:underline">{t("ログイン")}</a>
        <a href="/signup/" className="text-[11px] text-slate-500 underline-offset-2 hover:text-navy hover:underline">{t("新規登録")}</a>
        <a href="/connect/" className="text-[11px] text-slate-500 underline-offset-2 hover:text-navy hover:underline">{t("LINEで接続")}</a>
      </span>
    );
  return (
    <span className="flex items-center gap-2">
      <Badge tone="ok">{t("ライブ")}</Badge>
      {role === "viewer" && <Badge tone="muted" icon={false}><Eye size={11} />{t("閲覧専用")}</Badge>}
      {email ? (
        <>
          <span className="max-w-[180px] truncate text-[11px] text-slate-500" title={email}>{email}</span>
          <button onClick={() => logout(true)} className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-navy">
            <LogOut size={12} />{t("ログアウト")}
          </button>
        </>
      ) : (
        <>
          <a href="/login/?next=/connect/" className="text-[11px] text-slate-400 hover:text-navy" title={t("ログイン後、LINEの帳簿をアカウントに連携できます")}>{t("アカウント連携")}</a>
          <button onClick={() => logout(false)} className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-navy">
            <LogOut size={12} />{t("切断")}
          </button>
        </>
      )}
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
  const { t, lang } = useLang();
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
    <Ctx.Provider value={{ toast, mode: c.mode, live: c.mode === "live", company: c.company, role: c.role, canEdit: canWrite(c.role) }}>
      <div className="flex min-h-screen">
        <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} company={c.company} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar key={c.mode} live={c.mode === "live"} onMenu={() => setMenuOpen(true)} onSearch={() => setSearchOpen(true)} company={c.company} setCompany={c.setCompany} toast={toast} role={c.role} account={!!c.email} />
          <main className="mx-auto w-full max-w-[1400px] flex-1 p-3 sm:p-5">
            <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1">
              <h1 className="text-lg font-bold text-navy">{t(title)}{(lang === "ja" ? en : title) && <span className="ml-2 text-[11px] font-medium uppercase tracking-wider text-slate-400">{lang === "ja" ? en : title}</span>}</h1>
              {sub && <p className="text-xs text-slate-400">{typeof sub === "string" ? t(sub) : sub}</p>}
              <div className="ml-auto flex flex-wrap items-center gap-2">
                {actions}
                <ModeBadge mode={c.mode} email={c.email} role={c.role} />
              </div>
            </div>
            {c.error && c.mode === "demo" && (
              <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">{t("サーバーに接続できなかったため、デモデータを表示しています（{e}）。", { e: c.error })}</p>
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
