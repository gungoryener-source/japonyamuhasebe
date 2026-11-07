"use client";

/** /signup — hesap açma (POST /auth/signup). Boş web帳簿 açılır; LINE帳簿は /connect で連携. */
import { useState } from "react";
import { UserPlus } from "lucide-react";
import { auth, PASSWORD_MAX, PASSWORD_MIN, setToken } from "../lib/api";
import { AuthCard, AuthInput, EMAIL_RE, errorText, Notice, SubmitBtn, pendingInvite } from "../components/auth";
import { T } from "../lib/i18n";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!EMAIL_RE.test(email.trim())) { setError(T("メールアドレスを正しく入力してください。")); return; }
    if (password.length < PASSWORD_MIN) { setError(T("パスワードは{a}文字以上にしてください。", { a: PASSWORD_MIN })); return; }
    if (password.length > PASSWORD_MAX) { setError(T("パスワードは{a}文字以内にしてください。", { a: PASSWORD_MAX })); return; }
    if (password !== confirm) { setError(T("確認用パスワードが一致しません。")); return; }
    setBusy(true);
    setError(null);
    try {
      const r = await auth.signup(email.trim(), password);
      setToken(r.token);
      location.href = pendingInvite() ? "/join/" : "/connect/?welcome=1"; // davetle gelen: katılıma dön (T-041b)
    } catch (e) {
      setError(errorText(e));
      setBusy(false);
    }
  };

  return (
    <AuthCard
      icon={<UserPlus size={18} />}
      title={T("アカウント登録")}
      sub={T("Sign up ・ 無料で始める")}
      onSubmit={submit}
      footer={<span>{T("登録済みの方は")} <a href="/login/" className="font-bold text-navy hover:underline">{T("ログイン")}</a></span>}
    >
      <AuthInput label={T("メールアドレス")} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.jp" />
      <AuthInput label={T("パスワード")} type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)}
        hint={T("{a}文字以上", { a: PASSWORD_MIN })} />
      <AuthInput label={T("パスワード（確認）")} type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
      {error && <Notice tone="error">{error}</Notice>}
      <p className="text-[11px] leading-relaxed text-slate-500">
        {T("登録すると、")}<a href="/legal/terms/" target="_blank" className="font-bold text-navy underline-offset-2 hover:underline">{T("利用規約")}</a>{T("と")}
        <a href="/legal/privacy/" target="_blank" className="font-bold text-navy underline-offset-2 hover:underline">{T("プライバシーポリシー")}</a>{T("に同意したものとみなされます。")}
      </p>
      <SubmitBtn busy={busy}>{T("登録する")}</SubmitBtn>
      <p className="text-[10px] leading-relaxed text-slate-400">
        {T("登録後、LINE で「パネル」と送って届く接続コードを入力すると、LINE で記録した帳簿をこのアカウントで使えます。")}
      </p>
    </AuthCard>
  );
}
