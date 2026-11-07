/**
 * Ekip (T-041 API'si → T-041b paneli) için saf yardımcılar. Tarayıcı/React bağımlılığı yok;
 * `npm run check:team` (scripts/check-team.mjs) ile doğrulanır.
 */

export type Role = "owner" | "accountant" | "viewer";
export type MemberRole = Exclude<Role, "owner">;

export const ROLE_LABEL: Record<Role, string> = { owner: "オーナー", accountant: "編集者", viewer: "閲覧者" };
export const ROLE_HINT: Record<Role, string> = {
  owner: "すべての操作（メンバー管理・料金プラン・LINE連携を含む）",
  accountant: "記帳・請求書・銀行明細・事業者情報の閲覧と編集",
  viewer: "閲覧とPDF・CSVのダウンロードのみ（編集不可）",
};
export const MEMBER_ROLES: MemberRole[] = ["accountant", "viewer"];

/** Sunucunun rolünü güvenle okur. `role` alanı olmayan eski sunucu → owner (T-041 öncesi tüm token'lar sahibin). */
export function parseRole(v: unknown): Role {
  return v === "accountant" || v === "viewer" ? v : "owner";
}

/** Muhasebe verisi yazma (kayıt, fatura, banka, 事業者情報): owner + accountant. Sunucuda `writer_user` ile aynı. */
export const canWrite = (role: Role) => role !== "viewer";
/** Üye yönetimi, abonelik, LINE 連携: yalnızca owner. Sunucuda `owner_user` ile aynı. */
export const isOwner = (role: Role) => role === "owner";

/** Davet kodu biçimi: `iv_` + token_urlsafe(18) (bot/team.py). Uzunluk payı geniş tutuldu. */
export const INVITE_RE = /^iv_[A-Za-z0-9_-]{16,64}$/;

/**
 * Kullanıcının yapıştırdığı metinden davet kodunu çıkarır: çıplak kod, `…/join/#iv_…` bağlantısı veya
 * boşluk/satır sonu karışmış kopya. Bulunamazsa "".
 */
export function extractInviteCode(input: string): string {
  const m = (input ?? "").replace(/\s+/g, "").match(/iv_[A-Za-z0-9_-]+/);
  return m && INVITE_RE.test(m[0]) ? m[0] : "";
}

/** Paylaşım bağlantısı: kod `#` sonrasında → sunucu loglarına ve Referer'a gitmez. */
export function joinLink(origin: string, code: string): string {
  return `${origin.replace(/\/$/, "")}/join/#${code}`;
}

/** "2026-11-14T12:00:00+09:00" → "11/14 12:00"（JST）. Geçersizse olduğu gibi. */
export function shortJST(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const p = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(d);
  const g = (t: string) => p.find((x) => x.type === t)?.value ?? "";
  return `${g("month")}/${g("day")} ${g("hour")}:${g("minute")}`;
}

export type Ledger = { user_id: string; role: Role; business_name: string };

/** Defter seçici listesi: sahibi olunan defter önce, sonra üyelikler; aynı defter tekrar etmez; ad boşsa yer tutucu. */
export function ledgerOptions(raw: { user_id: string; role: unknown; business_name?: string | null }[]): Ledger[] {
  const seen = new Set<string>();
  const out: Ledger[] = [];
  for (const r of raw ?? []) {
    if (!r?.user_id || seen.has(r.user_id)) continue;
    seen.add(r.user_id);
    out.push({ user_id: r.user_id, role: parseRole(r.role), business_name: (r.business_name ?? "").trim() || "事業者名未設定" });
  }
  return out.sort((a, b) => Number(b.role === "owner") - Number(a.role === "owner"));
}
