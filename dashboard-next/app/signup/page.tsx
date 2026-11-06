"use client";

/** /signup — hesap açma (POST /auth/signup). Boş web帳簿 açılır; LINE帳簿は /connect で連携. */
import { useState } from "react";
import { UserPlus } from "lucide-react";
import { auth, PASSWORD_MAX, PASSWORD_MIN, setToken } from "../lib/api";
import { AuthCard, AuthInput, EMAIL_RE, errorText, Notice, SubmitBtn } from "../components/auth";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!EMAIL_RE.test(email.trim())) { setError("メールアドレスを正しく入力してください。"); return; }
    if (password.length < PASSWORD_MIN) { setError(`パスワードは${PASSWORD_MIN}文字以上にしてください。`); return; }
    if (password.length > PASSWORD_MAX) { setError(`パスワードは${PASSWORD_MAX}文字以内にしてください。`); return; }
    if (password !== confirm) { setError("確認用パスワードが一致しません。"); return; }
    setBusy(true);
    setError(null);
    try {
      const r = await auth.signup(email.trim(), password);
      setToken(r.token);
      location.href = "/connect/?welcome=1";
    } catch (e) {
      setError(errorText(e));
      setBusy(false);
    }
  };

  return (
    <AuthCard
      icon={<UserPlus size={18} />}
      title="アカウント登録"
      sub="Sign up ・ 無料で始める"
      onSubmit={submit}
      footer={<span>登録済みの方は <a href="/login/" className="font-bold text-navy hover:underline">ログイン</a></span>}
    >
      <AuthInput label="メールアドレス" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.jp" />
      <AuthInput label="パスワード" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)}
        hint={`${PASSWORD_MIN}文字以上`} />
      <AuthInput label="パスワード（確認）" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
      {error && <Notice tone="error">{error}</Notice>}
      <SubmitBtn busy={busy}>登録する</SubmitBtn>
      <p className="text-[10px] leading-relaxed text-slate-400">
        登録後、LINE で「パネル」と送って届く接続コードを入力すると、LINE で記録した帳簿をこのアカウントで使えます。
      </p>
    </AuthCard>
  );
}
