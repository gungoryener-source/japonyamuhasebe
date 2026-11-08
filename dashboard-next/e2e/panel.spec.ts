/**
 * T-035: panel e2e. Demo modu (token yok) ve canlı mod (token + sahte API, e2e/fixtures/api.json).
 * Her sayfa açılır, menü bağlantıları gezilir; konsol hatası / yakalanmamış istisna olmamalı.
 * Fixture'ı yenilemek: `python dashboard-next/e2e/make_fixtures.py` (depo kökünden).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test, type Page } from "@playwright/test";

const FIXTURES: Record<string, unknown> = JSON.parse(readFileSync(join(__dirname, "fixtures", "api.json"), "utf-8"));
const TOKEN = "tk_e2e_dummy";

/** Kenar çubuğu menüsü (app/components/shell.tsx NAV) — başlık metniyle. */
const MENU: { href: string; label: string }[] = [
  { href: "/", label: "ホーム" },
  { href: "/invoices/", label: "請求書管理" },
  { href: "/expenses/", label: "経費精算" },
  { href: "/slips/", label: "仕切書の確認" },
  { href: "/passbook/", label: "通帳の確認" },
  { href: "/bank/", label: "銀行連携" },
  { href: "/assets/", label: "固定資産" },
  { href: "/tax/", label: "確定申告 / 税務" },
  { href: "/billing/", label: "料金プラン" },
  { href: "/settings/", label: "設定" },
];
/** Menü dışı sayfalar (oturum, yasal, tanıtım). */
const OTHER = ["/login/", "/signup/", "/reset/", "/join/", "/connect/", "/welcome/", "/lp/", "/legal/terms/", "/legal/privacy/", "/legal/tokushoho/"];

type Watch = { errors: string[]; api: { method: string; path: string; auth: string | null }[]; unmocked: string[] };

/** Konsol hatalarını, istisnaları ve API çağrılarını topla; API'yi fixture ile yanıtla. */
async function watch(page: Page, live: boolean): Promise<Watch> {
  const w: Watch = { errors: [], api: [], unmocked: [] };
  page.on("pageerror", (e) => w.errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error") w.errors.push(`console: ${m.text()}`); });
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace(/^.*\/api\/v1/, "");
    w.api.push({ method: req.method(), path, auth: req.headers()["authorization"] ?? null });
    const body = req.method() === "GET" ? FIXTURES[path] : undefined;
    if (body === undefined) {
      w.unmocked.push(`${req.method()} ${path}`);
      return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "e2e: not mocked" }) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  if (live) await page.addInitScript((tk) => { try { localStorage.setItem("jsaas.token", tk); } catch { /* yok */ } }, TOKEN);
  return w;
}

test.describe("demo modu", () => {
  for (const { href, label } of MENU) {
    test(`menü ${label} (${href})`, async ({ page }) => {
      const w = await watch(page, false);
      await page.goto(href);
      await expect(page.getByText("デモデータ").first()).toBeVisible();
      await expect(page.locator("main")).toBeVisible();
      await expect(page.locator(`a[href="${href}"]`).first()).toBeVisible();
      expect(w.api, "demo modunda token'lı API çağrısı olmamalı").toEqual([]);
      expect(w.errors).toEqual([]);
    });
  }

  test("kenar çubuğundan tüm menüler sırayla açılır", async ({ page }) => {
    const w = await watch(page, false);
    await page.goto("/");
    for (const { href } of MENU) {
      await page.locator(`nav a[href="${href}"], aside a[href="${href}"]`).first().click();
      await expect(page).toHaveURL(new RegExp(`${href.replace(/\//g, "\\/")}$`));
      await expect(page.locator("main")).toBeVisible();
    }
    expect(w.errors).toEqual([]);
  });

  for (const href of OTHER) {
    test(`sayfa ${href}`, async ({ page }) => {
      const w = await watch(page, false);
      const res = await page.goto(href);
      expect(res?.status()).toBe(200);
      await expect(page.locator("body")).not.toBeEmpty();
      await page.waitForLoadState("networkidle");
      expect(w.errors).toEqual([]);
    });
  }
});

test.describe("canlı mod (sahte API)", () => {
  for (const { href, label } of MENU) {
    test(`menü ${label} (${href})`, async ({ page }) => {
      const w = await watch(page, true);
      await page.goto(href);
      await expect(page.getByText("ライブ").first()).toBeVisible();
      await page.waitForLoadState("networkidle");
      await expect(page.locator("main")).toBeVisible();
      await expect(page.getByText("サーバーに接続できなかった")).toHaveCount(0);
      expect(w.api.length).toBeGreaterThan(0);
      expect(w.api.every((c) => c.auth === `Bearer ${TOKEN}`)).toBe(true);
      expect(w.unmocked, "fixture'da olmayan API çağrısı — make_fixtures.py PATHS'e ekleyin").toEqual([]);
      expect(w.errors).toEqual([]);
    });
  }
});
