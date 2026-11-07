// Tanıtım sayfası /lp içeriğini denetler (T-044).
// 実行: npm run check:lp（Node 22.6+ の --experimental-strip-types）。`next build` 後なら out/lp/index.html も検査する。
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { FAQ, FEATURES, HERO, LP_PLANS, PRICE_NOTE, SIGNUP_HREF, STEPS, lineAddUrl, limitLabel, yenLabel } from "../app/lib/lp.ts";

// 1) プランは bot/billing.py PLANS と一致（価格・上限・順序）
const py = readFileSync(new URL("../../bot/billing.py", import.meta.url), "utf8");
const block = py.match(/PLANS: dict\[str, dict\] = \{([\s\S]*?)\n\}/)?.[1];
assert.ok(block, "bot/billing.py PLANS が見つからない");
const pyPlans = [...block.matchAll(/"(\w+)": \{"name": "([^"]+)", "price_jpy": (\d+), "receipts_per_month": (None|\d+), "invoices_per_month": (None|\d+)/g)]
  .map(([, id, name, price, r, i]) => ({ id, name, price_jpy: +price, receipts_per_month: r === "None" ? null : +r, invoices_per_month: i === "None" ? null : +i }));
assert.equal(pyPlans.length, 3, "PLANS の解析に失敗");
assert.deepEqual(LP_PLANS.map(({ notes, ...p }) => p), pyPlans, "LP_PLANS が bot/billing.py PLANS と不一致");

// 2) 表示形式
assert.equal(yenLabel(0), "¥0");
assert.equal(yenLabel(2980), "¥2,980");
assert.equal(limitLabel(null), "無制限");
assert.equal(limitLabel(30), "月30件まで");
assert.ok(PRICE_NOTE.includes("税抜"));

// 3) 内容: 3 特長, 3 ステップ, FAQ ≥5（重複なし）, 税務相談でない旨
assert.equal(FEATURES.length, 3);
assert.equal(STEPS.length, 3);
assert.ok(FAQ.length >= 5, "FAQ は 5 問以上");
assert.equal(new Set(FAQ.map((f) => f.q)).size, FAQ.length, "FAQ の質問が重複");
for (const f of FAQ) assert.ok(f.q.trim() && f.a.trim());
const all = JSON.stringify({ FAQ, FEATURES, HERO, STEPS, LP_PLANS, PRICE_NOTE });
assert.ok(all.includes("税理士法") && all.includes("税務相談"), "税務相談でない旨がない");

// 4) 未確定・未実装の主張がない（「仮」価格、電帳法対応 → T-034、WhatsApp 本番 → Q-06、数値の誇張）
for (const ng of ["仮", "電帳法", "電子帳簿保存法", "WhatsApp", "No.1", "満足度", "導入実績"]) assert.ok(!all.includes(ng), `LP に「${ng}」`);

// 5) LINE 友だち追加 URL: https の lin.ee / line.me のみ
assert.equal(lineAddUrl(undefined), null);
assert.equal(lineAddUrl("  "), null);
assert.equal(lineAddUrl("javascript:alert(1)"), null);
assert.equal(lineAddUrl("http://lin.ee/abc"), null);
assert.equal(lineAddUrl(" https://lin.ee/abc "), "https://lin.ee/abc");
assert.equal(lineAddUrl("https://line.me/R/ti/p/@abc"), "https://line.me/R/ti/p/@abc");

// 6) ビルド済みなら静的 HTML に本文が入っている（JS なしで読める）
const out = new URL("../out/lp/index.html", import.meta.url);
if (existsSync(out)) {
  const html = readFileSync(out, "utf8");
  for (const s of [HERO.title, "¥980", "¥2,980", "税抜", ...FAQ.map((f) => f.q), `href="${SIGNUP_HREF}"`,
    'href="/legal/terms/"', 'href="/legal/privacy/"', 'href="/legal/tokushoho/"']) {
    assert.ok(html.includes(s), `out/lp: 「${s}」がない`);
  }
  console.log("check:lp OK (内容 + out/lp HTML)");
} else {
  console.log("check:lp OK (内容のみ; out/ なし)");
}
