"use client";

/**
 * Dil seçimi (T-047): ja (varsayılan) / tr / en.
 * Sözlük Japonca kaynak metinle anahtarlanır (`app/lib/i18n.ts`); çevirisi olmayan metin Japonca kalır.
 * Seçim localStorage `jsaas.lang`'da tutulur, <html lang> güncellenir.
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Languages } from "lucide-react";
import { LANGS, setCurrentLang, translate, type Lang } from "../lib/i18n";

const KEY = "jsaas.lang";

type LangCtx = { lang: Lang; setLang: (l: Lang) => void; t: (ja: string, vars?: Record<string, unknown>) => string };
const Ctx = createContext<LangCtx>({ lang: "ja", setLang: () => {}, t: (s, v) => translate("ja", s, v) });

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("ja");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved && LANGS.some((l) => l.code === saved)) setLangState(saved as Lang);
    } catch { /* depolama kapalı olabilir */ }
  }, []);

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try { localStorage.setItem(KEY, l); } catch { /* yok say */ }
  }, []);

  const t = useCallback((ja: string, vars?: Record<string, unknown>) => translate(lang, ja, vars), [lang]);

  setCurrentLang(lang);   // T() için; render sırasında ayarlanır ki çocuklar aynı dili görsün
  // Dil değişince ağaç yeniden kurulur: hook kullanmayan T() çağrıları da güncellenir.
  return <Ctx.Provider value={{ lang, setLang, t }}><div key={lang} className="contents">{children}</div></Ctx.Provider>;
}

export const useLang = () => useContext(Ctx);
export const useT = () => useContext(Ctx).t;

/** Üst çubuk ve 設定 sayfası için dil seçici. */
export function LangSwitcher({ compact = false }: { compact?: boolean }) {
  const { lang, setLang, t } = useLang();
  return (
    <label className={"flex items-center gap-1.5 rounded-lg text-[11px] text-slate-500 " + (compact ? "p-1.5 hover:bg-slate-100" : "")}>
      <Languages size={compact ? 16 : 14} className="shrink-0 text-slate-500" aria-hidden />
      <span className="sr-only">{t("表示言語")}</span>
      <select
        value={lang}
        onChange={(e) => setLang(e.target.value as Lang)}
        className={"cursor-pointer bg-transparent font-bold text-navy outline-none " + (compact ? "max-w-[5.5rem]" : "rounded-lg border border-slate-200 px-2 py-1.5")}
        aria-label={t("表示言語")}
      >
        {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
      </select>
    </label>
  );
}
