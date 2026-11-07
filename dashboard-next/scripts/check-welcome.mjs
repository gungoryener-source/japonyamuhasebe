// /welcome 初期設定ウィザードの純粋ヘルパー（app/lib/welcome.ts）を検査する（T-044b）。
// 実行: npm run check:welcome（Node 22.6+ の --experimental-strip-types）。
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  BUSINESS_NAME_MAX, nextStep, normalizeReg, parseStep, profileAfterLink, profileError, signupRedirect, WELCOME_STEPS, wizardMode,
} from "../app/lib/welcome.ts";

// 1) 3 ステップ、順序は 事業者情報 → LINE → 領収書
assert.deepEqual(WELCOME_STEPS.map((s) => s.ja), ["事業者情報", "LINE 連携", "最初の領収書"]);
assert.equal(parseStep(null), 1);
assert.equal(parseStep(""), 1);
assert.equal(parseStep("2"), 2);
assert.equal(parseStep(" 3 "), 3);
for (const bad of ["0", "4", "-1", "2.5", "abc", "1e1"]) assert.equal(parseStep(bad), 1, bad);
assert.deepEqual([nextStep(1), nextStep(2), nextStep(3)], [2, 3, null]);

// 2) 表示対象: デモは静的、オーナーのみウィザード、招待メンバーはホームへ
assert.equal(wizardMode("loading", "owner"), "loading");
assert.equal(wizardMode("demo", "owner"), "demo");
assert.equal(wizardMode("live", "owner"), "wizard");
assert.equal(wizardMode("live", "accountant"), "home");
assert.equal(wizardMode("live", "viewer"), "home");
assert.equal(signupRedirect(false), "/welcome/");
assert.equal(signupRedirect(true), "/join/");

// 3) 事業者情報の検証（サーバー ProfileIn: business_name ≤ 100）
assert.equal(BUSINESS_NAME_MAX, 100);
assert.equal(profileError("", ""), null, "空欄はスキップ可");
assert.equal(profileError("あ".repeat(100), "T1234567890123"), null);
assert.ok(profileError("あ".repeat(101), ""));
assert.ok(profileError("屋号", "T123"));
assert.ok(profileError("屋号", "1234567890123"));
assert.equal(normalizeReg(" t1234-5678-90123 "), "T1234567890123");
const api = readFileSync(new URL("../../bot/api.py", import.meta.url), "utf8");
assert.match(api, /class ProfileIn[\s\S]{0,200}business_name: str = Field\(default="", max_length=100\)/, "ProfileIn 上限が変わったら BUSINESS_NAME_MAX も更新");

// 4) LINE 連携後の事業者情報: LINE 帳簿が空なら下書きを移す、既存なら守る
const draft = { business_name: " 〇〇デザイン ", registration_no: "T1234567890123", individual: false };
assert.deepEqual(profileAfterLink(draft, { business_name: "", registration_no: "", individual: 1 }),
  { business_name: "〇〇デザイン", registration_no: "T1234567890123", individual: false });
assert.deepEqual(profileAfterLink(draft, { business_name: "  ", registration_no: "T9999999999999", individual: 1 }),
  { business_name: "〇〇デザイン", registration_no: "T9999999999999", individual: false }, "LINE 側の登録番号を優先");
assert.equal(profileAfterLink(draft, { business_name: "既存屋号", registration_no: "", individual: 1 }), null);
assert.equal(profileAfterLink(null, { business_name: "", registration_no: "", individual: 1 }), null, "ステップ1をスキップ");
assert.equal(profileAfterLink({ ...draft, business_name: "" }, { business_name: "", registration_no: "", individual: 1 }), null);

// 5) 登録画面はウィザードへ（招待経由は除く）
const signup = readFileSync(new URL("../app/signup/page.tsx", import.meta.url), "utf8");
assert.match(signup, /signupRedirect\(!!pendingInvite\(\)\)/);

console.log("check:welcome OK");
