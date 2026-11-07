"use client";

/** /login — e-posta + parola ile giriş (POST /auth/login). Token mevcut `jsaas.token` anahtarına kaydedilir. */
import { useState } from "react";
import { LogIn } from "lucide-react";
import { auth, setToken } from "../lib/api";
import { AuthCard, AuthInput, EMAIL_RE, errorText, nextPath, Notice, SubmitBtn } from "../components/auth";
import { T } from "../lib/i18n";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!EMAIL_RE.test(email.trim())) { setError(T("メールアドレスを正しく入力してください。")); return; }
    if (!password) { setError(T("パスワードを入力してください。")); return; }
    setBusy(true);
    setError(null);
    try {
      const r = await auth.login(email.trim(), password);
      setToken(r.token);
      location.href = nextPath();
    } catch (e) {
      setError(errorText(e));
      setBusy(false);
    }
  };

  return (
    <AuthCard
      icon={<LogIn size={18} />}
      title={T("ログイン")}
      sub="Log in"
      onSubmit={submit}
      footer={<><a href="/signup/" className="font-bold text-navy hover:underline">{T("新規登録")}</a><a href="/connect/" className="hover:text-navy">{T("LINEの接続コードで開く")}</a></>}
    >
      <AuthInput label={T("メールアドレス")} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.jp" />
      <AuthInput label={T("パスワード")} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <Notice tone="error">{error}</Notice>}
      <SubmitBtn busy={busy}>{T("ログイン")}</SubmitBtn>
      <a href="/reset/" className="block text-center text-[11px] text-slate-400 hover:text-navy">{T("パスワードをお忘れの方")}</a>
    </AuthCard>
  );
}
