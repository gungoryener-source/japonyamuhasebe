"use client";

/**
 * /join#iv_xxx — 招待コードで他の事業者の帳簿に参加する（T-041b, POST /team/join）。
 * - メールアドレスでログイン中: コードを確認して参加 → 新しいトークン（参加先の帳簿）に切り替えてホームへ。
 * - 未ログイン / LINE 接続コードのみ: コードを sessionStorage に残してログイン・新規登録へ（戻ると自動で入力済み）。
 * 元の帳簿には上部メニューの帳簿セレクターでいつでも戻れる（POST /team/switch）。
 */
import { useEffect, useState } from "react";
import { LoaderCircle, UserPlus } from "lucide-react";
import { api, getToken, replaceSession } from "../lib/api";
import { extractInviteCode, ROLE_HINT, ROLE_LABEL, parseRole } from "../lib/team";
import { AuthCard, AuthInput, errorText, Notice, pendingInvite, setPendingInvite, SubmitBtn } from "../components/auth";

type Session = { state: "loading" } | { state: "none" } | { state: "account"; email: string };

export default function JoinPage() {
  const [value, setValue] = useState("");
  const [session, setSession] = useState<Session>({ state: "loading" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState<string | null>(null);

  useEffect(() => {
    const fromHash = extractInviteCode(location.hash.slice(1));
    if (location.hash) history.replaceState(null, "", "/join/"); // kod adres çubuğunda / geçmişte kalmasın
    const code = fromHash || extractInviteCode(pendingInvite());
    if (code) { setValue(code); setPendingInvite(code); }
    const resolve = async (): Promise<Session> => {
      if (!getToken()) return { state: "none" };
      try {
        const me = await api.me();
        return me.account ? { state: "account", email: me.account.email } : { state: "none" };
      } catch {
        return { state: "none" };
      }
    };
    resolve().then(setSession);
  }, []);

  const submit = async () => {
    const code = extractInviteCode(value);
    if (!code) { setError("招待コードは「iv_」で始まります。オーナーから届いたコードまたはリンクを貼り付けてください。"); return; }
    if (session.state !== "account") { setPendingInvite(code); location.href = "/login/?next=/join/"; return; }
    setBusy(true);
    setError(null);
    try {
      const r = await api.teamJoin(code);
      setPendingInvite(null);
      await replaceSession(r.token);
      setJoined(ROLE_LABEL[parseRole(r.role)]);
      setTimeout(() => { location.href = "/"; }, 900);
    } catch (e) {
      setError(errorText(e));
      setBusy(false);
    }
  };

  if (session.state === "loading")
    return (
      <main className="grid min-h-screen place-items-center bg-[#F9FAFB]">
        <LoaderCircle size={20} className="animate-spin text-slate-400" />
      </main>
    );

  const account = session.state === "account";
  return (
    <AuthCard
      icon={<UserPlus size={18} />}
      title="招待された帳簿に参加"
      sub="Join a team ledger"
      onSubmit={submit}
      footer={account
        ? <a href="/" className="font-bold text-navy hover:underline">ホームに戻る</a>
        : <><a href="/login/?next=/join/" className="font-bold text-navy hover:underline">ログイン</a><a href="/signup/" className="hover:text-navy">新規登録</a></>}
    >
      {account ? (
        <p className="rounded-lg bg-slate-50 px-3 py-2 text-[11px] text-slate-500">
          ログイン中：<span className="font-bold text-navy">{session.email}</span><br />
          参加後は上部メニューから、ご自身の帳簿と参加した帳簿を切り替えられます。
        </p>
      ) : (
        <Notice tone="warn">招待に参加するには、メールアドレスでログイン（またはアカウント登録）してください。コードはこのタブに保存され、ログイン後に自動で入力されます。</Notice>
      )}
      <AuthInput label="招待コード" value={value} onChange={(e) => setValue(e.target.value)} placeholder="iv_..." autoComplete="off" spellCheck={false}
        className="font-mono" />
      <ul className="space-y-0.5 text-[10px] text-slate-400">
        <li><span className="font-bold text-slate-500">{ROLE_LABEL.accountant}</span>：{ROLE_HINT.accountant}</li>
        <li><span className="font-bold text-slate-500">{ROLE_LABEL.viewer}</span>：{ROLE_HINT.viewer}</li>
      </ul>
      {error && <Notice tone="error">{error}</Notice>}
      {joined && <Notice tone="ok">{joined}として参加しました。帳簿を開いています…</Notice>}
      <SubmitBtn busy={busy || !!joined}>{account ? "参加する" : "ログインして参加"}</SubmitBtn>
    </AuthCard>
  );
}
