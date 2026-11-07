// チーム機能の純粋ヘルパー（app/lib/team.ts）を検査する（T-041b）。
// 実行: npm run check:team（Node 22.6+ の --experimental-strip-types）。
import assert from "node:assert/strict";
import {
  canWrite, extractInviteCode, INVITE_RE, isOwner, joinLink, ledgerOptions, MEMBER_ROLES, parseRole, ROLE_LABEL, shortJST,
} from "../app/lib/team.ts";

// 1) 役割: 不明・欠落 → owner（T-041 以前のサーバー）。サーバーの writer_user / owner_user と一致
assert.equal(parseRole(undefined), "owner");
assert.equal(parseRole("admin"), "owner");
assert.equal(parseRole("viewer"), "viewer");
assert.equal(parseRole("accountant"), "accountant");
assert.deepEqual(["owner", "accountant", "viewer"].map((r) => canWrite(r)), [true, true, false]);
assert.deepEqual(["owner", "accountant", "viewer"].map((r) => isOwner(r)), [true, false, false]);
assert.deepEqual(MEMBER_ROLES, ["accountant", "viewer"]);
for (const r of ["owner", "accountant", "viewer"]) assert.ok(ROLE_LABEL[r]);

// 2) 招待コード: secrets.token_urlsafe(18) = 24 文字
const code = "iv_" + "Ab3-_x".repeat(4);
assert.ok(INVITE_RE.test(code));
assert.equal(extractInviteCode(code), code);
assert.equal(extractInviteCode(`  ${code}\n`), code);
assert.equal(extractInviteCode(`https://panel.example.jp/join/#${code}`), code);
assert.equal(extractInviteCode(`iv_${"Ab3-_x".repeat(2)}\n${"Ab3-_x".repeat(2)}`), code, "改行で割れたコード");
assert.equal(extractInviteCode("tk_abcdefghijklmnopqrstuvwx"), "", "接続コードは招待コードではない");
assert.equal(extractInviteCode("iv_short"), "");
assert.equal(extractInviteCode(""), "");
assert.equal(extractInviteCode(undefined), "");

// 3) 共有リンク: コードはハッシュ（#）に入り、末尾スラッシュは二重にならない
assert.equal(joinLink("https://p.example.jp/", code), `https://p.example.jp/join/#${code}`);
assert.equal(joinLink("https://p.example.jp", code), `https://p.example.jp/join/#${code}`);
assert.equal(extractInviteCode(joinLink("https://p.example.jp", code)), code);

// 4) 日時表示は JST
assert.equal(shortJST("2026-11-14T03:05:00+00:00"), "11/14 12:05");
assert.equal(shortJST("2026-12-31T23:30:00+09:00"), "12/31 23:30");
assert.equal(shortJST("not-a-date"), "not-a-date");

// 5) 帳簿セレクター: オーナー帳簿が先頭、重複なし、空の事業者名はプレースホルダー
const ls = ledgerOptions([
  { user_id: "U2", role: "viewer", business_name: "" },
  { user_id: "U1", role: "owner", business_name: "自分の屋号" },
  { user_id: "U2", role: "viewer", business_name: "dup" },
  { user_id: "", role: "viewer" },
  { user_id: "U3", role: "accountant", business_name: null },
]);
assert.deepEqual(ls.map((l) => l.user_id), ["U1", "U2", "U3"]);
assert.equal(ls[1].business_name, "事業者名未設定");
assert.equal(ls[2].role, "accountant");
assert.deepEqual(ledgerOptions(undefined), []);

console.log("check:team OK");
