// 法務ページのテンプレート（app/lib/legal.ts）を検査する（T-043）。
// 実行: npm run check:legal（Node 22.6+ の --experimental-strip-types）。`next build` 後なら out/legal/* の HTML も検査する。
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import {
  DRAFT_NOTICE, PENDING, LEGAL_PAGES, TOKUSHOHO_REQUIRED, sellerFrom, termsDoc, privacyDoc, tokushohoDoc,
} from "../app/lib/legal.ts";

// 1) 未設定・空白のみの値は「要確認」
const empty = sellerFrom({ NEXT_PUBLIC_LEGAL_SELLER: "  ", NEXT_PUBLIC_LEGAL_EMAIL: "" });
for (const v of Object.values(empty)) assert.equal(v, PENDING);

// 2) 設定値はそのまま（前後空白のみ除去）
const set = sellerFrom({
  NEXT_PUBLIC_LEGAL_SELLER: " テスト合同会社 ", NEXT_PUBLIC_LEGAL_MANAGER: "山田 太郎", NEXT_PUBLIC_LEGAL_ADDRESS: "東京都千代田区1-1",
  NEXT_PUBLIC_LEGAL_PHONE: "03-0000-0000", NEXT_PUBLIC_LEGAL_EMAIL: "support@example.jp",
});
assert.equal(set.name, "テスト合同会社");

// 3) 特商法: 必須項目がすべて行にある。未設定の販売業者情報は todo、設定済みは todo でない
for (const seller of [empty, set]) {
  const t = tokushohoDoc(seller);
  const labels = t.rows.map((r) => r.label);
  for (const req of TOKUSHOHO_REQUIRED) assert.ok(labels.includes(req), `特商法: ${req} がない`);
  for (const r of t.rows) assert.ok(r.value.trim(), `特商法: ${r.label} が空`);
  for (const k of ["販売業者", "運営統括責任者", "所在地", "電話番号", "メールアドレス"]) {
    const row = t.rows.find((r) => r.label === k);
    assert.equal(Boolean(row.todo), seller === empty, `特商法: ${k} の要確認フラグ`);
  }
}

// 4) 規約・ポリシー: 見出しが一意で空ブロックがない。必須の章がある。販売業者名が差し込まれる
const docs = [termsDoc(set), privacyDoc(set), tokushohoDoc(set)];
for (const d of docs) {
  const hs = d.sections.map((s) => s.heading);
  assert.equal(new Set(hs).size, hs.length, `${d.slug}: 見出しが重複`);
  for (const s of d.sections) for (const b of s.blocks) assert.ok(b.text?.trim() || b.items?.length, `${d.slug}/${s.heading}: 空ブロック`);
  assert.ok(LEGAL_PAGES.some((p) => p.slug === d.slug), `${d.slug}: LEGAL_PAGES にない`);
}
const privacyText = JSON.stringify(privacyDoc(set));
for (const kw of ["利用目的", "第三者提供", "外国にある第三者", "保存期間", "開示", "シンガポール"]) assert.ok(privacyText.includes(kw), `privacy: ${kw}`);
assert.ok(termsDoc(set).intro.includes("テスト合同会社"));
assert.ok(JSON.stringify(termsDoc(set)).includes("税理士法"), "terms: 税務相談でない旨");

// 5) ビルド済みなら、各ページの静的 HTML にドラフト表示と本文が含まれる（JS なしで読める）
const out = new URL("../out/legal/", import.meta.url);
if (existsSync(out)) {
  for (const p of LEGAL_PAGES) {
    const html = readFileSync(new URL(`${p.slug}/index.html`, out), "utf8");
    assert.ok(html.includes(DRAFT_NOTICE), `${p.slug}: ドラフト表示がない`);
    assert.ok(html.includes(p.title), `${p.slug}: タイトルがない`);
  }
  const tk = readFileSync(new URL("tokushoho/index.html", out), "utf8");
  for (const req of TOKUSHOHO_REQUIRED) assert.ok(tk.includes(req), `out/tokushoho: ${req}`);
  console.log("check:legal OK (テンプレート + out/legal HTML)");
} else {
  console.log("check:legal OK (テンプレートのみ; out/ なし)");
}
