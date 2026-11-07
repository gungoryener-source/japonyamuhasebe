/**
 * /welcome kurulum sihirbazının saf yardımcıları (T-044b). `npm run check:welcome` ile denetlenir.
 * Adımlar: 1 事業者情報 → 2 LINE 連携 → 3 最初の領収書. Her adım atlanabilir; bitince ホーム.
 */
export const WELCOME_STEPS = [
  { ja: "事業者情報", en: "Business" },
  { ja: "LINE 連携", en: "LINE" },
  { ja: "最初の領収書", en: "First receipt" },
] as const;

export type Step = 1 | 2 | 3;

/** `?step=` değeri → 1..3 (bozuk/eksik → 1). Sayfa yenilenince aynı adımda kalınsın diye URL'de tutulur. */
export function parseStep(v: string | null | undefined): Step {
  const n = Number((v ?? "").trim());
  return n === 2 || n === 3 ? n : 1;
}

/** Bir sonraki adım; son adımdan sonra null (→ ホーム). */
export function nextStep(s: Step): Step | null {
  return s === 3 ? null : ((s + 1) as Step);
}

/**
 * Sihirbaz kime gösterilir: demo (token yok) → statik önizleme; canlı owner → sihirbaz;
 * ekip üyesi (accountant / viewer — davetle katılan) → gösterilmez, ホーム.
 */
export function wizardMode(mode: "loading" | "live" | "demo", role: string): "loading" | "demo" | "wizard" | "home" {
  if (mode === "loading") return "loading";
  if (mode === "demo") return "demo";
  return role === "owner" ? "wizard" : "home";
}

/** Kayıt sonrası yönlendirme: davet kodu bekliyorsa katılıma (sihirbaz yok), değilse /welcome. */
export function signupRedirect(hasPendingInvite: boolean): string {
  return hasPendingInvite ? "/join/" : "/welcome/";
}

/** 登録番号 girişi: büyük harf, T ve rakam dışı karakterler atılır (設定 ile aynı). */
export function normalizeReg(v: string): string {
  return v.toUpperCase().replace(/[^T\d]/g, "");
}

export const BUSINESS_NAME_MAX = 100; // bot/api.py ProfileIn

/** Adım 1 doğrulaması: Japonca hata metni (i18n anahtarı) veya null. Boş alanlar serbest (sonra 設定'ten). */
export function profileError(name: string, reg: string): string | null {
  if (name.trim().length > BUSINESS_NAME_MAX) return "事業者名は100文字以内で入力してください";
  if (reg && !/^T\d{13}$/.test(reg)) return "登録番号は T + 13桁 で入力してください";
  return null;
}

export type ProfileDraft = { business_name: string; registration_no: string; individual: boolean };
export type LinkedProfile = { business_name: string; registration_no: string; individual: number };

/**
 * LINE defteri bağlandıktan sonra (adım 2) oturum LINE defterine geçer; adım 1'de web defterine kaydedilen
 * 事業者情報 orada yoktur. LINE defterinde 事業者名 boşsa adım 1 taslağı oraya yazılır (PUT /profile);
 * doluysa LINE defterindeki bilgi korunur (null = yazma). 登録番号 boşsa taslaktan tamamlanır.
 */
export function profileAfterLink(draft: ProfileDraft | null, linked: LinkedProfile): ProfileDraft | null {
  if (!draft || !draft.business_name.trim()) return null;
  if (linked.business_name.trim()) return null;
  return {
    business_name: draft.business_name.trim(),
    registration_no: linked.registration_no || draft.registration_no,
    individual: draft.individual,
  };
}
